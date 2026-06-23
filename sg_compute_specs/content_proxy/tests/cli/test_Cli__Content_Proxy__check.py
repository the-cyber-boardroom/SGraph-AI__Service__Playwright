# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: `sg cp check` / `wait` table machinery
# No AWS — exercises the pure check-table builders, the check ordering, the row
# initialisation, and the `sg cp logs --source <x>` suggestion mapping (ported
# from sg va, adapted to content_proxy's LOG_SOURCES).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from rich.table                                                                     import Table

from sg_compute_specs.content_proxy.cli.Cli__Content_Proxy                          import (LOG_SOURCES, _CHECK_ORDER,
                                                                                            _DIAG_HINTS, _DIAG_ICONS,
                                                                                            _DIAG_STATE_LABEL, _initial_rows,
                                                                                            _build_check_table, _suggestions_for)


class test_check_order(TestCase):

    def test_order_matches_diagnose_stages_plus_external(self):
        assert _CHECK_ORDER == ('ec2-state', 'ssm-reachable', 'boot-failed', 'container-engine',
                                'containers-up', 'cert-init', 'vault-http', 'boot-ok', 'external-http')

    def test_cert_init_present_for_tls_debugging(self):
        assert 'cert-init' in _CHECK_ORDER

    def test_external_http_is_last(self):                                           # the CLI's own probe is appended after diagnose()
        assert _CHECK_ORDER[-1] == 'external-http'


class test_diag_icon_tables(TestCase):

    def test_every_status_has_icon_and_label(self):
        for status in ('ok', 'fail', 'warn', 'skip', 'checking', 'pending'):
            assert status in _DIAG_ICONS
            assert status in _DIAG_STATE_LABEL


class test_initial_rows(TestCase):

    def test_one_pending_row_per_check(self):
        rows = _initial_rows()
        assert [n for n, _, _ in rows] == list(_CHECK_ORDER)
        assert all(status == 'pending' for _, status, _ in rows)
        assert all(detail == '' for _, _, detail in rows)


class test_build_check_table(TestCase):

    def test_returns_table_with_one_row_per_check(self):
        rows  = [('ec2-state', 'ok', 'running'), ('vault-http', 'warn', 'HTTP 503')]
        table = _build_check_table(rows)
        assert isinstance(table, Table)
        assert table.row_count == 2

    def test_header_extra_does_not_crash(self):
        table = _build_check_table(_initial_rows(), header_extra='attempt=2 elapsed=30s')
        assert isinstance(table, Table)

    def test_detail_truncated_to_first_line(self):                                  # multi-line details (e.g. boot tail) show only line 1
        rows  = [('boot-failed', 'fail', 'boot script error:\nline2\nline3')]
        table = _build_check_table(rows)
        assert table.row_count == 1                                                 # render must not throw on multi-line detail


class test_diag_hints(TestCase):

    def test_every_hint_source_is_a_real_log_source(self):                          # suggestions must map to `sg cp logs --source` keys
        for check_name, hints in _DIAG_HINTS.items():
            for source, _reason in hints:
                assert source in LOG_SOURCES, f'{check_name} hint {source!r} is not a LOG_SOURCES key'

    def test_cert_init_failure_suggests_cert_init_logs(self):
        sources = [s for s, _r in _DIAG_HINTS['cert-init']]
        assert 'cert-init' in sources


class test_suggestions_for(TestCase):

    def test_only_warn_and_fail_rows_produce_suggestions(self):
        rows = [('ec2-state', 'ok', ''), ('cert-init', 'ok', ''), ('vault-http', 'ok', '')]
        assert _suggestions_for(rows, 'keen-darwin') == []

    def test_cert_init_failure_suggests_cert_init_source(self):
        rows = [('cert-init', 'fail', 'cert-init exited non-zero')]
        out  = _suggestions_for(rows, 'keen-darwin')
        assert out                                                                   # non-empty
        assert any(source == 'cert-init' for source, _reason, _origin in out)

    def test_deduplicated_across_checks(self):                                      # boot appears in several hints → suggested once
        rows = [('boot-failed', 'fail', 'x'), ('container-engine', 'warn', 'y')]
        out  = _suggestions_for(rows, 'keen-darwin')
        boot_sources = [s for s, _r, _o in out if s == 'boot']
        assert len(boot_sources) == 1

    def test_origin_is_the_failing_check(self):
        rows = [('vault-http', 'fail', 'no response')]
        out  = _suggestions_for(rows, 'keen-darwin')
        origins = {origin for _s, _r, origin in out}
        assert origins == {'vault-http'}
