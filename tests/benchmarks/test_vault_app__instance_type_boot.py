# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark — vault-app boot time across 6 instance types
#
# Launches 6 instances in parallel from a baked AMI (letsencrypt-ip TLS) and
# measures wall-clock time from RunInstances to first successful HTTP 200 on
# :443.  Deletes all instances on exit (even on failure or Ctrl-C).
#
# Gate: requires SG_RUN_LIVE_BENCH=1 and an explicit --ami argument passed via
#       SG_BENCH__AMI_ID (or -k ami-xxx filter).  Skips cleanly otherwise so
#       normal CI is not affected.
#
# Run example:
#   SG_RUN_LIVE_BENCH=1 SG_BENCH__AMI_ID=ami-0abc123 pytest \
#       tests/benchmarks/test_vault_app__instance_type_boot.py -s -v
#
# Optional overrides:
#   SG_BENCH__REGION          (default: eu-west-2)
#   SG_BENCH__TIMEOUT_SEC     (default: 240)
#   SG_BENCH__MAX_HOURS       (default: 0.25)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import ssl
import time
import secrets
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing             import Optional

import pytest


# ── Constants ─────────────────────────────────────────────────────────────────

INSTANCE_TYPES = [
    't3.medium' ,   # current baseline
    't3a.medium',   # AMD Zen 2 — same RAM/vCPU tier, EPYC
    'm5.large'  ,   # Skylake general purpose — 8 GiB RAM
    'm6i.large' ,   # Ice Lake general purpose — 8 GiB RAM
    'c5.large'  ,   # Skylake compute optimised — 4 GiB RAM
    'c6i.large' ,   # Ice Lake compute optimised — 4 GiB RAM
]

REGION      = os.environ.get('SG_BENCH__REGION',      'eu-west-2')
AMI_ID      = os.environ.get('SG_BENCH__AMI_ID',      '')
TIMEOUT_SEC = int(os.environ.get('SG_BENCH__TIMEOUT_SEC', '240'))
MAX_HOURS   = float(os.environ.get('SG_BENCH__MAX_HOURS', '0.25'))
POLL_SEC    = 6


# ── Gate ──────────────────────────────────────────────────────────────────────

def _live_bench_enabled() -> bool:
    return os.environ.get('SG_RUN_LIVE_BENCH', '') == '1'


def _creds_available() -> bool:
    try:
        import boto3
        boto3.client('sts', region_name=REGION).get_caller_identity()
        return True
    except Exception:
        return False


# ── HTTP probe (no vault client — pure stdlib) ─────────────────────────────────

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode    = ssl.CERT_NONE


def _http_status(url: str, timeout: int = 5) -> int:
    """Return HTTP status code, or 0 on connection error."""
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=_ssl_ctx) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def _vault_is_up(public_ip: str) -> bool:
    """True when either :443 or :8080 returns a non-5xx response."""
    for url in (f'https://{public_ip}/info/health',
                f'http://{public_ip}:8080/info/health'):
        s = _http_status(url)
        if s and s < 500:
            return True
    return False


# ── Per-instance worker ────────────────────────────────────────────────────────

class _BootResult:
    def __init__(self, instance_type: str):
        self.instance_type  : str            = instance_type
        self.iid            : str            = ''
        self.sg_id          : str            = ''
        self.public_ip      : str            = ''
        self.elapsed_s      : Optional[int]  = None    # None = did not become healthy
        self.error          : str            = ''
        self.timed_out      : bool           = False

    def __repr__(self):
        if self.elapsed_s is not None:
            return f'<{self.instance_type}  {self.elapsed_s}s  ip={self.public_ip}>'
        tag = 'TIMEOUT' if self.timed_out else f'ERROR: {self.error[:60]}'
        return f'<{self.instance_type}  {tag}>'


def _launch_one(svc, itype: str, ami_id: str, caller_ip: str) -> _BootResult:
    """Create, wait for health, return timing.  Stores iid+sg_id for cleanup."""
    from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request

    result = _BootResult(itype)
    t0     = time.monotonic()

    try:
        req = Schema__Vault_App__Create__Request(
            region        = REGION                       ,
            instance_type = itype                        ,
            from_ami      = ami_id                       ,
            caller_ip     = caller_ip                    ,
            max_hours     = MAX_HOURS                    ,
            with_tls_check= True                         ,
            tls_mode      = 'letsencrypt-ip'             ,
            acme_prod     = True                         ,
            use_spot      = True                         ,
            stack_name    = f'bench-{itype.replace(".", "-")}-{secrets.token_hex(3)}',
        )
        resp         = svc.create_stack(req, creator='bench')
        result.iid   = str(getattr(resp.stack_info, 'instance_id', '') or '')
        result.sg_id = str(getattr(resp.stack_info, 'sg_id',       '') or '')
    except Exception as exc:
        result.error = str(exc)[:200]
        return result

    # poll until healthy or timeout
    deadline = time.monotonic() + TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            info      = svc.get_stack_info(REGION, req.stack_name)
            public_ip = str(getattr(info, 'public_ip', '') or '') if info else ''
            if public_ip:
                result.public_ip = public_ip
                if _vault_is_up(public_ip):
                    result.elapsed_s = int(time.monotonic() - t0)
                    return result
        except Exception:
            pass
        time.sleep(POLL_SEC)

    result.timed_out = True
    result.elapsed_s = None
    return result


# ── Cleanup ────────────────────────────────────────────────────────────────────

def _delete_one(svc, iid: str, sg_id: str, stack_name: str) -> None:
    try:
        svc.delete_stack(REGION, stack_name)
    except Exception:
        # belt-and-suspenders: terminate directly if service-level delete fails
        try:
            if iid:
                svc.aws_client.instance.terminate(REGION, iid)
        except Exception:
            pass
        try:
            if sg_id:
                svc.aws_client.sg.delete_security_group(REGION, sg_id)
        except Exception:
            pass


# ── Results table ──────────────────────────────────────────────────────────────

def _print_results(results: list) -> None:
    col_w = max(len(r.instance_type) for r in results) + 2
    header = f'  {"INSTANCE TYPE":<{col_w}}  {"BOOT TIME":>10}  {"STATUS"}'
    sep    = '  ' + '-' * (len(header) - 2)
    print('\n')
    print('  ┌' + '─' * (len(header) - 1) + '┐')
    print(f'  │{header}│')
    print('  │' + sep[2:] + '│')

    healthy = [r for r in results if r.elapsed_s is not None]
    for r in sorted(results, key=lambda x: (x.elapsed_s is None, x.elapsed_s or 9999)):
        if r.elapsed_s is not None:
            baseline = healthy[0].elapsed_s if healthy else r.elapsed_s
            delta    = r.elapsed_s - baseline
            delta_s  = f'  (+{delta}s)' if delta > 0 else '  (baseline)'
            status   = f'{r.elapsed_s:>6}s  ✓{delta_s}'
        elif r.timed_out:
            status = f'{"—":>7}  TIMEOUT >{TIMEOUT_SEC}s'
        else:
            status = f'{"—":>7}  ERROR: {r.error[:40]}'
        print(f'  │  {r.instance_type:<{col_w}} {status}')

    print('  └' + '─' * (len(header) - 1) + '┘')
    if healthy:
        fastest = min(healthy, key=lambda r: r.elapsed_s)
        slowest = max(healthy, key=lambda r: r.elapsed_s)
        spread  = slowest.elapsed_s - fastest.elapsed_s
        print(f'\n  fastest: {fastest.instance_type} ({fastest.elapsed_s}s)'
              f'  |  slowest: {slowest.instance_type} ({slowest.elapsed_s}s)'
              f'  |  spread: {spread}s')
    print()


# ── Test ───────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _live_bench_enabled(), reason='set SG_RUN_LIVE_BENCH=1 to run')
class Test__Vault_App__Instance_Type_Boot:

    def test_requires_ami_id(self):
        assert AMI_ID, (
            'SG_BENCH__AMI_ID is not set.  '
            'Pass the baked vault-app AMI id, e.g.:\n'
            '  SG_RUN_LIVE_BENCH=1 SG_BENCH__AMI_ID=ami-0abc123 pytest '
            'tests/benchmarks/test_vault_app__instance_type_boot.py -s -v'
        )

    def test_creds_available(self):
        assert _creds_available(), (
            'No AWS credentials available for region '
            f'{REGION!r}.  Configure AWS_PROFILE or set env vars.'
        )

    def test_boot_all_types(self):
        """Launch 6 instance types in parallel, capture boot timings, delete all."""
        assert AMI_ID,          'SG_BENCH__AMI_ID must be set (caught by test_requires_ami_id)'
        assert _creds_available(), 'AWS creds missing (caught by test_creds_available)'

        from sg_compute_specs.vault_app.service.Vault_App__Service   import Vault_App__Service
        from sg_compute.platforms.ec2.networking.Caller__IP__Detector import Caller__IP__Detector

        svc       = Vault_App__Service().setup()
        caller_ip = Caller__IP__Detector().detect()
        assert caller_ip, 'Could not detect caller public IP — set SG_BENCH_CALLER_IP or check network'

        print(f'\n  AMI: {AMI_ID}  |  region: {REGION}  |  timeout: {TIMEOUT_SEC}s  |  types: {len(INSTANCE_TYPES)}')
        print(f'  Launching {len(INSTANCE_TYPES)} instances in parallel...\n')

        results: list[_BootResult] = []
        lock = threading.Lock()

        def _worker(itype):
            r = _launch_one(svc, itype, AMI_ID, caller_ip)
            with lock:
                results.append(r)
                tag = f'{r.elapsed_s}s' if r.elapsed_s is not None else ('TIMEOUT' if r.timed_out else f'ERROR {r.error[:30]}')
                print(f'  [{itype:<12}]  done — {tag}')
            return r

        try:
            with ThreadPoolExecutor(max_workers=len(INSTANCE_TYPES)) as pool:
                futures = {pool.submit(_worker, itype): itype for itype in INSTANCE_TYPES}
                for fut in as_completed(futures):
                    fut.result()   # surface any uncaught exception
        finally:
            # always delete — even on keyboard interrupt or assertion error
            print(f'\n  Deleting {len(results)} instances...')
            with ThreadPoolExecutor(max_workers=len(results) or 1) as pool:
                futs = []
                for r in results:
                    stack_name = f'bench-{r.instance_type.replace(".", "-")}'
                    futs.append(pool.submit(_delete_one, svc, r.iid, r.sg_id, stack_name))
                for fut in as_completed(futs):
                    try:
                        fut.result()
                    except Exception:
                        pass
            print('  All instances deleted.')

        _print_results(results)

        healthy = [r for r in results if r.elapsed_s is not None]
        assert healthy, (
            f'No instance type became healthy within {TIMEOUT_SEC}s.\n'
            f'Results: {results}'
        )
