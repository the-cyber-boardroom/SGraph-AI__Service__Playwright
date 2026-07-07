# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__Diagnose__Renderer
# Shared live boot-progress check-table. No AWS / no mocks — driven by tiny
# in-memory fake services that expose diagnose() + health(), consistent with the
# repo's in-memory composition style. Covers row building, the external probe,
# the run_checks stream merge, the dedup/suggestion seam, and run_once/run_until_ok.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                          import TestCase

from rich.console                                      import Console
from rich.table                                        import Table

from sg_compute.cli.base.Spec__Diagnose__Renderer      import (DIAG_ICONS, DIAG_STATE_LABEL, OK_STATES,
                                                               build_check_table, initial_rows, probe_external_http,
                                                               run_checks, suggestions_for, print_summary,
                                                               run_once, run_until_ok)


# ── in-memory fakes (no AWS) ──────────────────────────────────────────────────

class _FakeProbe:
    def __init__(self, healthy=True, state='running', last_error='', elapsed_ms=12):
        self.healthy    = healthy
        self.state      = state
        self.last_error = last_error
        self.elapsed_ms = elapsed_ms


class _FakeService:
    # diagnose yields a fixed stage list; health returns a fixed probe.
    def __init__(self, stages, probe=None):
        self._stages = stages
        self._probe  = probe if probe is not None else _FakeProbe()

    def diagnose(self, region, name):
        for row in self._stages:
            yield row

    def health(self, region, name, timeout_sec=0, poll_sec=10):
        return self._probe


class _Live:                                                    # stand-in for rich.Live.update() — records the last table
    def __init__(self):
        self.last = None
    def update(self, table):
        self.last = table


CHECK_ORDER = ('ec2-state', 'ssm-reachable', 'containers-up', 'external-http')


# ── tests ─────────────────────────────────────────────────────────────────────

class test_build_check_table(TestCase):

    def test_one_row_per_check(self):
        rows  = [('ec2-state', 'ok', 'running'), ('vault-http', 'warn', 'HTTP 503')]
        table = build_check_table(rows)
        assert isinstance(table, Table)
        assert table.row_count == 2

    def test_detail_truncated_to_first_line(self):                                  # multi-line detail must not throw on render
        table = build_check_table([('boot-failed', 'fail', 'err:\nline2\nline3')])
        assert table.row_count == 1

    def test_header_extra_accepted(self):
        table = build_check_table(initial_rows(CHECK_ORDER), header_extra='attempt=2')
        assert isinstance(table, Table)

    def test_ok_times_adds_ok_column(self):                                          # timed path → extra 'OK@' column
        rows  = [('ec2-state', 'ok', 'running'), ('containers-up', 'pending', '')]
        plain = build_check_table(rows)                                              # no ok_times → 3 columns
        timed = build_check_table(rows, ok_times={'ec2-state': 7})                   # ok_times → 4 columns
        assert len(timed.columns) == len(plain.columns) + 1
        assert any(c.header == 'OK@' for c in timed.columns)

    def test_ok_times_empty_dict_still_shows_column(self):                           # {} is "timed, none green yet", not "untimed"
        table = build_check_table([('ec2-state', 'pending', '')], ok_times={})
        assert any(c.header == 'OK@' for c in table.columns)


class test_icon_label_tables(TestCase):

    def test_every_status_has_icon_and_label(self):
        for status in ('ok', 'fail', 'warn', 'skip', 'checking', 'pending'):
            assert status in DIAG_ICONS
            assert status in DIAG_STATE_LABEL

    def test_ok_states_are_ok_and_skip(self):
        assert OK_STATES == ('ok', 'skip')


class test_initial_rows(TestCase):

    def test_pending_row_per_check(self):
        rows = initial_rows(CHECK_ORDER)
        assert [n for n, _, _ in rows] == list(CHECK_ORDER)
        assert all(s == 'pending' for _, s, _ in rows)

    def test_none_check_order_yields_empty(self):                                   # rows grow dynamically when no order given
        assert initial_rows(None) == []


class test_probe_external_http(TestCase):

    def test_healthy(self):
        status, detail = probe_external_http(_FakeService([], _FakeProbe(healthy=True, elapsed_ms=20)),
                                             'eu-west-2', 's')
        assert status == 'ok'
        assert '20ms' in detail

    def test_unhealthy_with_error_is_warn(self):
        svc = _FakeService([], _FakeProbe(healthy=False, state='starting', last_error='vault http 503'))
        status, detail = probe_external_http(svc, 'eu-west-2', 's')
        assert status == 'warn'
        assert '503' in detail

    def test_unhealthy_no_error_is_fail(self):
        svc = _FakeService([], _FakeProbe(healthy=False, state='', last_error=''))
        status, _ = probe_external_http(svc, 'eu-west-2', 's')
        assert status == 'fail'


class test_run_checks(TestCase):

    def test_merges_diagnose_stream_then_appends_external_probe(self):
        stages = [('ec2-state', 'checking', ''), ('ec2-state', 'ok', 'running'),
                  ('containers-up', 'ok', '5 up')]
        svc    = _FakeService(stages, _FakeProbe(healthy=True))
        rows   = initial_rows(CHECK_ORDER)
        out    = run_checks(svc, 'eu-west-2', 's', live=_Live(), rows=rows)
        as_dict = {n: s for n, s, _ in out}
        assert as_dict['ec2-state']     == 'ok'                                     # last yield wins over 'checking'
        assert as_dict['containers-up'] == 'ok'
        assert as_dict['external-http'] == 'ok'                                     # appended by the renderer

    def test_unknown_check_is_appended(self):                                       # a diagnose check not in the order still shows
        svc  = _FakeService([('surprise', 'warn', 'x')], _FakeProbe())
        rows = initial_rows(CHECK_ORDER)
        out  = run_checks(svc, 'eu-west-2', 's', live=_Live(), rows=rows)
        assert any(n == 'surprise' for n, _, _ in out)

    def test_ok_times_stamped_only_for_ok_states(self):                             # time-to-OK captured for green rows, not warn/fail
        import time as _t
        stages   = [('ec2-state', 'ok', ''), ('containers-up', 'warn', 'not yet'), ('cert-init', 'skip', '')]
        svc      = _FakeService(stages, _FakeProbe(healthy=True))
        rows     = initial_rows(CHECK_ORDER)
        ok_times = {}
        run_checks(svc, 'eu-west-2', 's', live=_Live(), rows=rows, ok_times=ok_times, started=_t.monotonic())
        assert 'ec2-state'     in ok_times                                          # ok  → stamped
        assert 'cert-init'     in ok_times                                          # skip → stamped (skip is an OK state)
        assert 'external-http' in ok_times                                          # healthy probe → stamped
        assert 'containers-up' not in ok_times                                      # warn → not stamped


class test_suggestions_for(TestCase):

    HINTS = {'cert-init'  : [('cert-init', 'sidecar logs')],
             'boot-failed': [('boot', 'boot log')],
             'vault-http' : [('boot', 'boot log'), ('vault', 'vault logs')]}

    def test_only_warn_fail_rows(self):
        rows = [('cert-init', 'ok', ''), ('boot-failed', 'skip', '')]
        assert suggestions_for(rows, self.HINTS) == []

    def test_fail_row_suggested(self):
        out = suggestions_for([('cert-init', 'fail', 'x')], self.HINTS)
        assert out == [('cert-init', 'sidecar logs', 'cert-init')]

    def test_dedup_across_checks(self):                                             # 'boot' appears twice → once
        rows = [('boot-failed', 'fail', ''), ('vault-http', 'warn', '')]
        out  = suggestions_for(rows, self.HINTS)
        boot = [s for s, _r, _o in out if s == 'boot']
        assert len(boot) == 1

    def test_valid_sources_filter_drops_unknown(self):
        out = suggestions_for([('cert-init', 'fail', '')], self.HINTS, valid_sources={'boot'})
        assert out == []                                                            # cert-init not a valid source → dropped

    def test_empty_hints_safe(self):
        assert suggestions_for([('x', 'fail', '')], None) == []


class test_print_summary(TestCase):

    def _capture(self, rows, **kw):
        c = Console(highlight=False, record=True, width=120)
        print_summary(c, rows, 'my-stack', **kw)
        return c.export_text()

    def test_all_ok(self):
        out = self._capture([('ec2-state', 'ok', ''), ('vault-http', 'skip', '')])
        assert 'all checks passed' in out

    def test_failure_without_hints_omits_suggestions(self):
        out = self._capture([('cert-init', 'fail', 'x')])
        assert '1 failed' in out
        assert 'Suggested next steps' not in out                                    # no hints/prefix → no suggestions

    def test_failure_with_hints_shows_suggestions(self):
        out = self._capture([('cert-init', 'fail', 'x')],
                            hints={'cert-init': [('cert-init', 'sidecar logs')]},
                            log_command_prefix='sg cp logs', valid_sources={'cert-init'})
        assert 'Suggested next steps' in out
        assert 'sg cp logs my-stack --source cert-init' in out


class test_run_once(TestCase):

    def test_returns_rows_and_renders(self):
        stages = [('ec2-state', 'ok', 'running'), ('ssm-reachable', 'ok', 'responsive'),
                  ('containers-up', 'ok', 'up')]
        svc    = _FakeService(stages, _FakeProbe(healthy=True))
        c      = Console(highlight=False, record=True, width=120)
        rows   = run_once(svc, 'eu-west-2', 'my-stack', console=c, check_order=CHECK_ORDER)
        states = {n: s for n, s, _ in rows}
        assert states['ec2-state']     == 'ok'
        assert states['external-http'] == 'ok'
        assert 'my-stack' in c.export_text()


class test_run_until_ok(TestCase):

    def test_all_ok_first_attempt_returns_true(self):
        stages = [('ec2-state', 'ok', ''), ('ssm-reachable', 'ok', ''), ('containers-up', 'ok', '')]
        svc    = _FakeService(stages, _FakeProbe(healthy=True))
        c      = Console(highlight=False, record=True, width=120)
        _rows, all_ok = run_until_ok(svc, 'eu-west-2', 'my-stack', console=c,
                                     check_order=CHECK_ORDER, timeout=30, poll=1)
        assert all_ok is True                                                       # returns on attempt 1, no sleep

    def test_timeout_zero_with_warn_returns_false_without_looping(self):
        stages = [('ec2-state', 'ok', ''), ('ssm-reachable', 'ok', ''), ('containers-up', 'warn', 'not yet')]
        svc    = _FakeService(stages, _FakeProbe(healthy=False, state='starting', last_error='no'))
        c      = Console(highlight=False, record=True, width=120)
        _rows, all_ok = run_until_ok(svc, 'eu-west-2', 'my-stack', console=c,
                                     check_order=CHECK_ORDER, timeout=0, poll=1)     # timeout=0 → break after attempt 1
        assert all_ok is False

    def test_skip_counts_as_ok(self):                                              # a 'skip' row (e.g. cert-init on non-TLS) must not block all_ok
        stages = [('ec2-state', 'ok', ''), ('ssm-reachable', 'ok', ''),
                  ('containers-up', 'ok', ''), ('cert-init', 'skip', 'no sidecar')]
        order  = ('ec2-state', 'ssm-reachable', 'containers-up', 'cert-init', 'external-http')
        svc    = _FakeService(stages, _FakeProbe(healthy=True))
        c      = Console(highlight=False, record=True, width=120)
        _rows, all_ok = run_until_ok(svc, 'eu-west-2', 'my-stack', console=c,
                                     check_order=order, timeout=30, poll=1)
        assert all_ok is True
