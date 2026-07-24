# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: `sg cp check` / `wait` diagnose config
# No AWS — verifies the spec-specific diagnose config (check order, hints) the
# `check`/`wait` commands and `create --wait` feed into the SHARED
# Spec__Diagnose__Renderer. The renderer's own table/summary logic is tested in
# sg_compute__tests/cli/base/test_Spec__Diagnose__Renderer.py.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.cli.base.Spec__Diagnose__Renderer                                   import suggestions_for
from sg_compute_specs.content_proxy.cli.Cli__Content_Proxy                          import (LOG_SOURCES, DIAGNOSE_CHECK_ORDER,
                                                                                            DIAGNOSE_HINTS, DIAGNOSE_LOG_PREFIX,
                                                                                            _cli_spec)


class test_diagnose_check_order(TestCase):

    def test_order_matches_diagnose_stages_plus_external(self):
        assert DIAGNOSE_CHECK_ORDER == ('ec2-state', 'ssm-reachable', 'boot-failed', 'container-engine',
                                        'containers-up', 'cert-init', 'vault-http', 'browser-http',
                                        'boot-ok', 'external-http')

    def test_cert_init_present_for_tls_debugging(self):
        assert 'cert-init' in DIAGNOSE_CHECK_ORDER

    def test_external_http_is_last(self):                                           # the renderer's own probe is appended after diagnose()
        assert DIAGNOSE_CHECK_ORDER[-1] == 'external-http'


class test_diagnose_hints(TestCase):

    def test_every_hint_source_is_a_real_log_source(self):                          # suggestions must map to `sg cp logs --source` keys
        for check_name, hints in DIAGNOSE_HINTS.items():
            for source, _reason in hints:
                assert source in LOG_SOURCES, f'{check_name} hint {source!r} is not a LOG_SOURCES key'

    def test_cert_init_failure_suggests_cert_init_logs(self):
        sources = [s for s, _r in DIAGNOSE_HINTS['cert-init']]
        assert 'cert-init' in sources

    def test_log_prefix_is_sg_cp_logs(self):
        assert DIAGNOSE_LOG_PREFIX == 'sg cp logs'


class test_cli_spec_carries_diagnose_config(TestCase):

    def test_spec_exposes_check_order(self):                                        # so create --wait renders the same table
        assert _cli_spec.diagnose_check_order == DIAGNOSE_CHECK_ORDER

    def test_spec_exposes_hints_and_prefix(self):
        assert _cli_spec.diagnose_hints      == DIAGNOSE_HINTS
        assert _cli_spec.diagnose_log_prefix == DIAGNOSE_LOG_PREFIX


class test_suggestions_with_content_proxy_config(TestCase):                          # end-to-end: content_proxy hints through the shared renderer

    def test_no_warn_fail_no_suggestions(self):
        rows = [('ec2-state', 'ok', ''), ('cert-init', 'ok', ''), ('vault-http', 'ok', '')]
        assert suggestions_for(rows, DIAGNOSE_HINTS, valid_sources=set(LOG_SOURCES)) == []

    def test_cert_init_failure_suggests_cert_init_source(self):
        rows = [('cert-init', 'fail', 'cert-init exited non-zero')]
        out  = suggestions_for(rows, DIAGNOSE_HINTS, valid_sources=set(LOG_SOURCES))
        assert out
        assert any(source == 'cert-init' for source, _reason, _origin in out)

    def test_deduplicated_across_checks(self):                                      # 'boot' appears in several hints → suggested once
        rows = [('boot-failed', 'fail', 'x'), ('container-engine', 'warn', 'y')]
        out  = suggestions_for(rows, DIAGNOSE_HINTS, valid_sources=set(LOG_SOURCES))
        boot_sources = [s for s, _r, _o in out if s == 'boot']
        assert len(boot_sources) == 1

    def test_origin_is_the_failing_check(self):
        rows = [('vault-http', 'fail', 'no response')]
        out  = suggestions_for(rows, DIAGNOSE_HINTS, valid_sources=set(LOG_SOURCES))
        origins = {origin for _s, _r, origin in out}
        assert origins == {'vault-http'}
