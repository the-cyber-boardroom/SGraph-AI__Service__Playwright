# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — cert_init
# Entry point for the one-shot cert sidecar. Writes cert.pem + key.pem to the
# shared /certs volume and exits 0; the TLS apps that read those files are gated
# behind it via compose `depends_on: service_completed_successfully`.
#
#   python -m sg_compute.platforms.tls.cert_init
#
# Three modes (SG__CERT_INIT__MODE):
#   self-signed             (default)  — Cert__Generator, offline, browser will warn
#   letsencrypt-ip                     — Cert__ACME__Client, publicly-trusted IP cert
#                                        via http-01 on :80 (LE staging unless ACME_PROD)
#   letsencrypt-hostname               — Cert__ACME__Client, publicly-trusted DNS-name
#                                        cert via http-01 on :80. The caller must point
#                                        the FQDN's A record at the EC2 IP *before* boot —
#                                        cert-init does not wait for DNS propagation.
#                                        Reachable from sandbox-egress proxies (which
#                                        validate hostnames strictly) — the IP-cert path
#                                        cannot be reached that way.
#
# Common name / IP resolution: SG__CERT_INIT__COMMON_NAME env → EC2 IMDSv2
# public IPv4 → 'localhost' (self-signed only; letsencrypt-ip fails loud if it
# cannot resolve a real public IP). letsencrypt-hostname uses
# SG__CERT_INIT__TLS_HOSTNAME directly — no IMDS lookup.
#
# ── observability ───────────────────────────────────────────────────────────
# Each stage transition is appended to STAGE_FILE (default
# /var/lib/sg-compute/cert-init.stage) so `sg va check` can surface the
# current stage without tailing docker logs. Format per line:
#   {iso_ts}\t{stage}\t{detail}
# The last line is the current stage. Stages:
#   start             — main() entered, mode resolved
#   generating        — self-signed: building cert in-process
#   waiting-for-dns   — letsencrypt-hostname: polling for FQDN → my IP
#   dns-converged     — letsencrypt-hostname: FQDN resolves to my IP
#   requesting-cert   — letsencrypt-*: ACME HTTP-01 challenge in flight
#   cert-issued       — success: cert+key written to /certs
#   failed            — exception caught at top of main(); detail = error
#
# ── timing budget (letsencrypt-hostname mode, the slow path) ────────────────
#   container start              2-5s     30s worst case
#   waiting-for-dns              5-60s    180s default (was 900s)
#   ACME HTTP-01 challenge       5-20s    60s (LE retries internally)
#   write cert to /certs        <1s      n/a
#   ────────────────────────────────────────────────────────────────────────
#   total: typical               30-90s   total: worst case  ≤ 5 min
#
# `sg vp register --wait` and `sg va wait` should size their timeouts above
# the worst-case row above (~300s + a margin) — the DNS default cap is what
# the sidecar itself enforces; the CLI poll never aborts cert-init.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
import os
import socket
import sys
import time
import urllib.request
from datetime import datetime, timezone

from sg_compute.platforms.tls.Cert__Generator import Cert__Generator

ENV__MODE                  = 'SG__CERT_INIT__MODE'
ENV__COMMON_NAME           = 'SG__CERT_INIT__COMMON_NAME'
ENV__SANS                  = 'SG__CERT_INIT__SANS'
ENV__ACME_PROD             = 'SG__CERT_INIT__ACME_PROD'
ENV__ACME_EMAIL            = 'SG__CERT_INIT__ACME_EMAIL'
ENV__TLS_HOSTNAME          = 'SG__CERT_INIT__TLS_HOSTNAME'
ENV__DNS_WAIT_TIMEOUT_SEC  = 'SG__CERT_INIT__DNS_WAIT_TIMEOUT_SEC'
ENV__CERT_FILE             = 'FAST_API__TLS__CERT_FILE'
ENV__KEY_FILE              = 'FAST_API__TLS__KEY_FILE'
ENV__STAGE_FILE            = 'SG__CERT_INIT__STAGE_FILE'                       # override for tests

# DNS-wait default was 900s. v0.1.14 cert-init-observability brief: 180s is enough when
# --with-aws-dns runs the Route 53 INSYNC poll in parallel during the EC2 boot window;
# DNS that hasn't converged in 3 minutes is almost certainly a misconfigured A record
# (operator error), not a propagation race. Caller can still override via env.
DEFAULT__DNS_WAIT_TIMEOUT_SEC = 180
DNS_WAIT_POLL_SEC             = 5

# Stage file — bind-mounted into the cert-init container via the compose template.
# Readable from the EC2 host: sudo cat /var/lib/sg-compute/cert-init.stage
STAGE_FILE = '/var/lib/sg-compute/cert-init.stage'

# Stage labels (single source of truth — tests + diagnose() both import these)
STAGE__START            = 'start'
STAGE__GENERATING       = 'generating'
STAGE__WAITING_FOR_DNS  = 'waiting-for-dns'
STAGE__DNS_CONVERGED    = 'dns-converged'
STAGE__REQUESTING_CERT  = 'requesting-cert'
STAGE__CERT_ISSUED      = 'cert-issued'
STAGE__FAILED           = 'failed'

MODE__SELF_SIGNED          = 'self-signed'
MODE__LETSENCRYPT_IP       = 'letsencrypt-ip'
MODE__LETSENCRYPT_HOSTNAME = 'letsencrypt-hostname'

DEFAULT__CERT_FILE   = '/certs/cert.pem'
DEFAULT__KEY_FILE    = '/certs/key.pem'
DEFAULT__COMMON_NAME = 'localhost'

_TRUTHY    = {'1', 'true', 'yes', 'on'}
_IMDS_BASE = 'http://169.254.169.254/latest'


def record_stage(stage: str, detail: str = '', stage_file: str = '') -> None:
    """Append a stage line to STAGE_FILE for `sg va check` to surface.

    Format: {iso_utc_ts}\\t{stage}\\t{detail}\\n. Append-only — the file
    captures the full progression; readers take the last line. Failures
    to write are swallowed (best-effort observability — never block cert
    issuance on a stage-file write)."""
    path = stage_file or os.environ.get(ENV__STAGE_FILE, '') or STAGE_FILE
    line = f'{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}\t{stage}\t{detail}\n'
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(line)
    except Exception as exc:                                                   # /var/lib/sg-compute not mounted, permissions, disk full
        print(f'[cert-init] stage-file write failed ({path}): {exc}', file=sys.stderr)


def _imds_public_ipv4() -> str:                                              # best-effort IMDSv2 lookup; '' on any failure
    try:
        token_req = urllib.request.Request(f'{_IMDS_BASE}/api/token', method='PUT',
                                           headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'})
        token     = urllib.request.urlopen(token_req, timeout=2).read().decode()
        ip_req    = urllib.request.Request(f'{_IMDS_BASE}/meta-data/public-ipv4',
                                           headers={'X-aws-ec2-metadata-token': token})
        return urllib.request.urlopen(ip_req, timeout=2).read().decode().strip()
    except Exception:
        return ''


def resolve_common_name() -> str:
    return (os.environ.get(ENV__COMMON_NAME, '').strip()
            or _imds_public_ipv4()
            or DEFAULT__COMMON_NAME)


def resolve_public_ip() -> str:                                              # ACME needs a real routable IP — no localhost fallback
    candidate = os.environ.get(ENV__COMMON_NAME, '').strip() or _imds_public_ipv4()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        raise RuntimeError(f'letsencrypt-ip mode needs a public IP — resolved {candidate!r} '
                           f'(set {ENV__COMMON_NAME} or run on EC2 with IMDS reachable)')
    return candidate


def _resolve_hostname(hostname: str) -> str:                                 # one DNS lookup attempt; returns IP string or an error sentinel
    # Catch broadly — gethostbyname can raise gaierror on NXDOMAIN, OSError on transient
    # network failure, and UnicodeError on malformed labels. The polling loop must never
    # raise on a single bad lookup; it just retries until timeout.
    try:
        return socket.gethostbyname(hostname)
    except (socket.gaierror, OSError, UnicodeError) as e:
        return f'<resolution failed: {e}>'


def wait_for_dns_to_match(hostname        : str ,
                          my_ip           : str ,
                          timeout_sec     : int  = DEFAULT__DNS_WAIT_TIMEOUT_SEC,
                          poll_sec        : int  = DNS_WAIT_POLL_SEC,
                          now_fn               = time.time,
                          sleep_fn             = time.sleep,
                          resolve_fn           = _resolve_hostname,
                          raise_on_timeout: bool = True) -> bool:
    # Poll DNS until `hostname` resolves to `my_ip`. Backstop for the race between EC2 boot
    # speed and Route 53 propagation — typically returns on the first poll when the CLI's
    # --with-aws-dns ran the upsert + INSYNC wait in parallel during the EC2 boot window.
    # Returns True on convergence. On timeout: raise RuntimeError if raise_on_timeout (the
    # default, kept for callers that hard-gate on box-side DNS), else return False so the
    # caller can decide — the hostname flow proceeds to ACME anyway, because Let's Encrypt
    # validates from ITS OWN resolvers, not this box (whose stub resolver may still be
    # serving a cached NXDOMAIN from a lookup made before the record existed).
    deadline  = now_fn() + timeout_sec
    last_seen = ''
    print(f'[cert-init] waiting for DNS: {hostname} → {my_ip}  (timeout {timeout_sec}s, poll {poll_sec}s)')
    while now_fn() < deadline:
        resolved = resolve_fn(hostname)
        if resolved == my_ip:
            print(f'[cert-init] DNS converged: {hostname} → {my_ip}')
            return True
        if resolved != last_seen:                                            # only print on change to keep the log readable
            print(f'[cert-init] waiting … {hostname} currently → {resolved}')
            last_seen = resolved
        sleep_fn(poll_sec)
    msg = (f'DNS for {hostname!r} did not converge to {my_ip} within {timeout_sec}s '
           f'(last seen: {last_seen!r})')
    if raise_on_timeout:
        raise RuntimeError(msg)
    print(f'[cert-init] {msg}')
    return False


def resolve_tls_hostname() -> str:                                           # FQDN must already point at this box's IP
    hostname = os.environ.get(ENV__TLS_HOSTNAME, '').strip()
    if not hostname:
        raise RuntimeError(f'letsencrypt-hostname mode needs {ENV__TLS_HOSTNAME} set to the FQDN to issue for')
    if any(c in hostname for c in ('/', ':', ' ')) or '://' in hostname:
        raise RuntimeError(f'{ENV__TLS_HOSTNAME} must be a bare FQDN (no scheme, port, or path) — got {hostname!r}')
    try:
        ipaddress.ip_address(hostname)                                       # if this succeeds, it's an IP, not a hostname
        raise RuntimeError(f'{ENV__TLS_HOSTNAME}={hostname!r} is an IP — use letsencrypt-ip mode instead')
    except ValueError:
        pass                                                                 # not an IP — good, it's a hostname
    return hostname


def _run_self_signed(cert_path: str, key_path: str) -> None:
    common_name = resolve_common_name()
    sans        = [s.strip() for s in os.environ.get(ENV__SANS, '').split(',') if s.strip()]
    record_stage(STAGE__GENERATING, f'cn={common_name} sans={sans}')
    Cert__Generator().generate_to_files(cert_path   = cert_path   ,
                                        key_path    = key_path    ,
                                        common_name = common_name ,
                                        sans        = sans        )
    print(f'[cert-init] mode=self-signed  cn={common_name!r}  cert={cert_path}  key={key_path}  sans={sans}')
    record_stage(STAGE__CERT_ISSUED, f'cert={cert_path}')


def _run_letsencrypt_ip(cert_path: str, key_path: str) -> None:
    from sg_compute.platforms.tls.Cert__ACME__Client import Cert__ACME__Client

    public_ip = resolve_public_ip()
    prod      = os.environ.get(ENV__ACME_PROD, '').strip().lower() in _TRUTHY
    email     = os.environ.get(ENV__ACME_EMAIL, '').strip()
    client    = Cert__ACME__Client()
    config    = client.config(prod=prod, contact_email=email)
    print(f'[cert-init] mode=letsencrypt-ip  ip={public_ip}  '
          f'directory={"prod" if prod else "staging"}  profile={config.profile}')
    record_stage(STAGE__REQUESTING_CERT, f'ip={public_ip} prod={prod}')
    client.issue(ip=public_ip, cert_path=cert_path, key_path=key_path, config=config)
    print(f'[cert-init] letsencrypt-ip cert issued  cert={cert_path}  key={key_path}')
    record_stage(STAGE__CERT_ISSUED, f'cert={cert_path} ip={public_ip}')


def _run_letsencrypt_hostname(cert_path: str, key_path: str) -> None:
    from sg_compute.platforms.tls.Cert__ACME__Client import Cert__ACME__Client

    hostname = resolve_tls_hostname()
    my_ip    = resolve_public_ip()                                           # ACME validates from the IP this box answers on — fail loud if no public IP
    timeout  = int(os.environ.get(ENV__DNS_WAIT_TIMEOUT_SEC, '').strip() or DEFAULT__DNS_WAIT_TIMEOUT_SEC)
    record_stage(STAGE__WAITING_FOR_DNS, f'fqdn={hostname} target={my_ip} timeout={timeout}s')
    converged = wait_for_dns_to_match(hostname=hostname, my_ip=my_ip, timeout_sec=timeout,
                                      raise_on_timeout=False)
    if converged:
        record_stage(STAGE__DNS_CONVERGED, f'{hostname} -> {my_ip}')
    else:
        # The box couldn't confirm the record (commonly a cached NXDOMAIN from the
        # --with-aws-dns race — Route 53's negative TTL is ~900s, far longer than our
        # poll window). Proceed to ACME anyway: Let's Encrypt validates from its own
        # resolvers, so it succeeds when the record is actually live and fails loud
        # below if it isn't — no worse than aborting here, and it rescues the race.
        print(f"[cert-init] WARNING: could not confirm {hostname} -> {my_ip} on this box "
              f"within {timeout}s; proceeding to ACME (Let's Encrypt validates externally).")
        record_stage(STAGE__DNS_CONVERGED, 'unconfirmed-on-box — proceeding (LE validates externally)')
    prod     = os.environ.get(ENV__ACME_PROD, '').strip().lower() in _TRUTHY
    email    = os.environ.get(ENV__ACME_EMAIL, '').strip()
    client   = Cert__ACME__Client()
    config   = client.config(prod=prod, contact_email=email, for_hostname=True)
    print(f'[cert-init] mode=letsencrypt-hostname  hostname={hostname}  '
          f'directory={"prod" if prod else "staging"}')
    record_stage(STAGE__REQUESTING_CERT, f'hostname={hostname} prod={prod}')
    client.issue(hostname=hostname, cert_path=cert_path, key_path=key_path, config=config)
    print(f'[cert-init] letsencrypt-hostname cert issued  cert={cert_path}  key={key_path}')
    record_stage(STAGE__CERT_ISSUED, f'cert={cert_path} hostname={hostname}')


def main() -> None:
    cert_path = os.environ.get(ENV__CERT_FILE) or DEFAULT__CERT_FILE
    key_path  = os.environ.get(ENV__KEY_FILE)  or DEFAULT__KEY_FILE
    mode      = (os.environ.get(ENV__MODE, '').strip() or MODE__SELF_SIGNED).lower()
    record_stage(STAGE__START, f'mode={mode}')

    try:
        if mode == MODE__LETSENCRYPT_IP:
            _run_letsencrypt_ip(cert_path, key_path)
        elif mode == MODE__LETSENCRYPT_HOSTNAME:
            _run_letsencrypt_hostname(cert_path, key_path)
        elif mode == MODE__SELF_SIGNED:
            _run_self_signed(cert_path, key_path)
        else:
            err = (f'unknown {ENV__MODE}={mode!r} — expected one of '
                   f'{MODE__SELF_SIGNED!r} / {MODE__LETSENCRYPT_IP!r} / {MODE__LETSENCRYPT_HOSTNAME!r}')
            print(f'[cert-init] {err}', file=sys.stderr)
            record_stage(STAGE__FAILED, err)
            sys.exit(2)
    except SystemExit:
        raise
    except BaseException as exc:                                               # also catches KeyboardInterrupt / timeouts so `failed` is recorded
        record_stage(STAGE__FAILED, f'{type(exc).__name__}: {exc}'[:240])
        raise


if __name__ == '__main__':
    main()
