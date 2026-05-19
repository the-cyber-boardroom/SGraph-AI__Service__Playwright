# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Warming__Page
# Asserts HTML content, cross-origin probe config, and no-cache headers.
# No mocks, no network.
#
# Refactored for v0.1.16:
#   - <meta http-equiv="refresh"> dropped; the page is JS-driven now.
#   - Probe target switched from the slug FQDN to `vp-admin.<zone>/api/v1/status`
#     (different CF distribution + single-host cert → no H2 coalescing).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json
import re

import pytest

from sg_compute_specs.vault_publish.lambdas.waker.Warming__Page import Warming__Page, NO_CACHE_HEADERS


def _config_from(html: str) -> dict:
    match = re.search(r'<script id="waker-cfg"[^>]*>(.*?)</script>', html, re.DOTALL)
    assert match, 'waker-cfg JSON block missing from warming-page HTML'
    return json.loads(match.group(1))


class TestWarmingPage:

    def setup_method(self):
        # Reset env for each test so module-level WAKER_PROBE_HOST is reproducible
        os.environ['SG_AWS__DNS__DEFAULT_ZONE'] = 'aws.sg-labs.app'
        os.environ.pop('WAKER_PROBE_HOST', None)
        os.environ.pop('WAKER_PROBE_PATH', None)
        os.environ.pop('WAKER_LAMBDA_FUNCTION_URL', None)
        import importlib
        from sg_compute_specs.vault_publish.lambdas.waker import Warming__Page as wp_mod
        importlib.reload(wp_mod)
        self.module = wp_mod
        self.page   = wp_mod.Warming__Page()

    def test_render_returns_string(self):
        html = self.page.render('sara-cv')
        assert isinstance(html, str) and len(html) > 0

    def test_html_contains_slug(self):
        html = self.page.render('sara-cv')
        assert 'sara-cv' in html

    def test_no_meta_refresh(self):
        # JS-driven flow — the old <meta http-equiv="refresh"> is gone.
        html = self.page.render('any-slug')
        assert 'http-equiv="refresh"' not in html

    def test_probe_url_defaults_to_vp_admin(self):
        cfg = _config_from(self.page.render('demo'))
        assert cfg['probe_target'] == 'admin-host'
        assert cfg['probe_url']    == 'https://vp-admin.aws.sg-labs.app/api/v1/status'

    def test_initial_wait_30s_by_default(self):
        cfg = _config_from(self.page.render('demo'))
        assert cfg['initial_wait_ms'] == 30000

    def test_poll_fast_5s_by_default(self):
        cfg = _config_from(self.page.render('demo'))
        assert cfg['poll_fast_ms'] == 5000

    def test_settle_disabled_by_default(self):
        # v0.1.16 cross-origin polling means socket-pool draining is no longer
        # needed; settle_ms=0 → JS redirects immediately on state=proxied.
        cfg = _config_from(self.page.render('demo'))
        assert cfg['settle_ms'] == 0

    def test_custom_initial_wait(self):
        page = Warming__Page(initial_wait_ms=10000)
        cfg  = _config_from(page.render('demo'))
        assert cfg['initial_wait_ms'] == 10000

    def test_custom_poll_fast(self):
        page = Warming__Page(poll_fast_ms=2000)
        cfg  = _config_from(page.render('demo'))
        assert cfg['poll_fast_ms'] == 2000

    def test_headers_no_cache(self):
        hdrs = self.page.headers()
        cc = hdrs.get('Cache-Control', '')
        assert 'no-store' in cc and 'no-cache' in cc and 'must-revalidate' in cc

    def test_headers_pragma_no_cache(self):
        assert self.page.headers().get('Pragma') == 'no-cache'

    def test_headers_content_type_html(self):
        ct = self.page.headers().get('Content-Type', '')
        assert 'text/html' in ct

    def test_headers_returns_fresh_copy(self):
        h1 = self.page.headers()
        h2 = self.page.headers()
        h1['X-Test'] = '1'
        assert 'X-Test' not in h2                                                  # Mutating one copy doesn't affect the other


class TestWarmingPageEnvOverrides:

    def test_custom_probe_host(self):
        os.environ['WAKER_PROBE_HOST'] = 'staging-admin.example.com'
        os.environ['SG_AWS__DNS__DEFAULT_ZONE'] = 'aws.sg-labs.app'
        import importlib
        from sg_compute_specs.vault_publish.lambdas.waker import Warming__Page as wp_mod
        importlib.reload(wp_mod)
        cfg = _config_from(wp_mod.Warming__Page().render('demo'))
        assert 'staging-admin.example.com' in cfg['probe_url']
        os.environ.pop('WAKER_PROBE_HOST', None)

    def test_lambda_url_fallback_when_no_admin_host(self):
        # When admin host is empty but Lambda Function URL is set, fall back
        # to polling the Lambda directly via /__waker__/probe.
        os.environ['WAKER_PROBE_HOST']         = ''
        os.environ['WAKER_LAMBDA_FUNCTION_URL'] = 'https://abc.lambda-url.eu-west-2.on.aws'
        os.environ['SG_AWS__DNS__DEFAULT_ZONE'] = 'aws.sg-labs.app'
        import importlib
        from sg_compute_specs.vault_publish.lambdas.waker import Warming__Page as wp_mod
        importlib.reload(wp_mod)
        cfg = _config_from(wp_mod.Warming__Page().render('demo'))
        assert cfg['probe_target'] == 'lambda-url'
        assert '/__waker__/probe' in cfg['probe_url']
        os.environ.pop('WAKER_LAMBDA_FUNCTION_URL', None)

    def test_slug_fqdn_fallback_when_nothing_set(self):
        # Both env vars empty → JS will poll the slug FQDN itself.
        os.environ['WAKER_PROBE_HOST']         = ''
        os.environ.pop('WAKER_LAMBDA_FUNCTION_URL', None)
        os.environ['SG_AWS__DNS__DEFAULT_ZONE'] = 'aws.sg-labs.app'
        import importlib
        from sg_compute_specs.vault_publish.lambdas.waker import Warming__Page as wp_mod
        importlib.reload(wp_mod)
        cfg = _config_from(wp_mod.Warming__Page().render('demo'))
        assert cfg['probe_target'] == 'slug-fqdn'
        assert cfg['probe_url'] == ''
