# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Spec__Diagnose__Renderer off-TTY rendering
# Off a TTY, rich.Live can't redraw in place, so the old per-check live.update()
# duplicated the `attempt=N` table. The fix renders one deduped snapshot per
# attempt. These tests lock that: no duplicated attempt blocks, and the loop still
# completes when every check is ok.
# ═══════════════════════════════════════════════════════════════════════════════

import io

from rich.console import Console

from sg_compute.cli.base.Spec__Diagnose__Renderer import run_until_ok, run_once


CHECK_ORDER = ('ec2-state', 'vault-http')


class _Health:
    healthy = True
    url     = 'https://x/info/health'
    http_code = 200
    latency_ms = 10
    error   = ''


class _Svc__AllOk:
    def diagnose(self, region, name):
        yield ('ec2-state',  'ok', 'running')
        yield ('vault-http', 'ok', 'HTTP 200 (:443)')
    def health(self, region, name, timeout_sec=0):
        return _Health()


def _non_tty_console():
    return Console(file=io.StringIO(), force_terminal=False, width=200)


class TestNonTtyRendering:

    def test_completes_when_all_ok(self):
        c = _non_tty_console()
        rows, all_ok = run_until_ok(_Svc__AllOk(), 'eu-west-2', 'swift-watt',
                                    console=c, check_order=CHECK_ORDER, timeout=30, poll=1)
        assert all_ok is True
        assert ('external-http', 'ok', 'serving via health probe (10ms)') in rows or \
               any(n == 'external-http' and s == 'ok' for n, s, _ in rows)

    def test_no_duplicated_attempt_blocks_off_tty(self):
        c   = _non_tty_console()
        run_until_ok(_Svc__AllOk(), 'eu-west-2', 'swift-watt',
                     console=c, check_order=CHECK_ORDER, timeout=30, poll=1)
        out = c.file.getvalue()
        # all checks are ok on attempt 1 → exactly one snapshot printed, so 'attempt=1'
        # appears at most once (the old per-check churn printed it ~3x).
        assert out.count('attempt=1') <= 1

    def test_run_once_off_tty_prints_table(self):
        c = _non_tty_console()
        run_once(_Svc__AllOk(), 'eu-west-2', 'swift-watt',
                 console=c, check_order=CHECK_ORDER)
        out = c.file.getvalue()
        assert 'ec2-state'  in out
        assert 'vault-http' in out
