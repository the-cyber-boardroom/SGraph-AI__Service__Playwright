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
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
import os
import sys
import urllib.request

from sg_compute.platforms.tls.Cert__Generator import Cert__Generator

ENV__MODE         = 'SG__CERT_INIT__MODE'
ENV__COMMON_NAME  = 'SG__CERT_INIT__COMMON_NAME'
ENV__SANS         = 'SG__CERT_INIT__SANS'
ENV__ACME_PROD    = 'SG__CERT_INIT__ACME_PROD'
ENV__ACME_EMAIL   = 'SG__CERT_INIT__ACME_EMAIL'
ENV__TLS_HOSTNAME = 'SG__CERT_INIT__TLS_HOSTNAME'
ENV__CERT_FILE    = 'FAST_API__TLS__CERT_FILE'
ENV__KEY_FILE     = 'FAST_API__TLS__KEY_FILE'

MODE__SELF_SIGNED          = 'self-signed'
MODE__LETSENCRYPT_IP       = 'letsencrypt-ip'
MODE__LETSENCRYPT_HOSTNAME = 'letsencrypt-hostname'

DEFAULT__CERT_FILE   = '/certs/cert.pem'
DEFAULT__KEY_FILE    = '/certs/key.pem'
DEFAULT__COMMON_NAME = 'localhost'

_TRUTHY    = {'1', 'true', 'yes', 'on'}
_IMDS_BASE = 'http://169.254.169.254/latest'


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
    Cert__Generator().generate_to_files(cert_path   = cert_path   ,
                                        key_path    = key_path    ,
                                        common_name = common_name ,
                                        sans        = sans        )
    print(f'[cert-init] mode=self-signed  cn={common_name!r}  cert={cert_path}  key={key_path}  sans={sans}')


def _run_letsencrypt_ip(cert_path: str, key_path: str) -> None:
    from sg_compute.platforms.tls.Cert__ACME__Client import Cert__ACME__Client

    public_ip = resolve_public_ip()
    prod      = os.environ.get(ENV__ACME_PROD, '').strip().lower() in _TRUTHY
    email     = os.environ.get(ENV__ACME_EMAIL, '').strip()
    client    = Cert__ACME__Client()
    config    = client.config(prod=prod, contact_email=email)
    print(f'[cert-init] mode=letsencrypt-ip  ip={public_ip}  '
          f'directory={"prod" if prod else "staging"}  profile={config.profile}')
    client.issue(ip=public_ip, cert_path=cert_path, key_path=key_path, config=config)
    print(f'[cert-init] letsencrypt-ip cert issued  cert={cert_path}  key={key_path}')


def _run_letsencrypt_hostname(cert_path: str, key_path: str) -> None:
    from sg_compute.platforms.tls.Cert__ACME__Client import Cert__ACME__Client

    hostname = resolve_tls_hostname()
    prod     = os.environ.get(ENV__ACME_PROD, '').strip().lower() in _TRUTHY
    email    = os.environ.get(ENV__ACME_EMAIL, '').strip()
    client   = Cert__ACME__Client()
    config   = client.config(prod=prod, contact_email=email, for_hostname=True)
    print(f'[cert-init] mode=letsencrypt-hostname  hostname={hostname}  '
          f'directory={"prod" if prod else "staging"}')
    client.issue(hostname=hostname, cert_path=cert_path, key_path=key_path, config=config)
    print(f'[cert-init] letsencrypt-hostname cert issued  cert={cert_path}  key={key_path}')


def main() -> None:
    cert_path = os.environ.get(ENV__CERT_FILE) or DEFAULT__CERT_FILE
    key_path  = os.environ.get(ENV__KEY_FILE)  or DEFAULT__KEY_FILE
    mode      = (os.environ.get(ENV__MODE, '').strip() or MODE__SELF_SIGNED).lower()

    if mode == MODE__LETSENCRYPT_IP:
        _run_letsencrypt_ip(cert_path, key_path)
    elif mode == MODE__LETSENCRYPT_HOSTNAME:
        _run_letsencrypt_hostname(cert_path, key_path)
    elif mode == MODE__SELF_SIGNED:
        _run_self_signed(cert_path, key_path)
    else:
        print(f'[cert-init] unknown {ENV__MODE}={mode!r} — expected one of '
              f'{MODE__SELF_SIGNED!r} / {MODE__LETSENCRYPT_IP!r} / {MODE__LETSENCRYPT_HOSTNAME!r}',
              file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
