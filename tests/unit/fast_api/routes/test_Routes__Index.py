# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Index (GET / "Try it out" console)
#
# Phase 1 (v0.2.64 dev pack) bug-fixes + capability bootstrap. Assertions are on the
# RENDERED HTML via Routes__Index().index(_FakeRequest()) — no route registration or
# Chromium needed, so these run anywhere the package imports.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                          import TestCase

from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index                    import Routes__Index


class _FakeRequest:                                                                    # minimal stand-in — only .headers.get is used by Root_Path__Resolver
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


def _render(headers: dict = None) -> str:
    return Routes__Index().index(_FakeRequest(headers)).body.decode()


class test_Routes__Index__phase1(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    # ── bug-fix: health badge sent no API key → always "degraded" on keyed deployments ──
    def test__health_check_sends_api_key(self):
        assert 'function authHeaders'        in self.html                              # auth header helper exists
        assert "h['X-API-Key'] = k"          in self.html                              # key attached when present
        assert "apiGet('/health/status')"    in self.html                              # health check goes through the auth-aware getter
        assert "await fetch(window.API_BASE + '/health/status')" not in self.html      # old keyless call removed

    # ── capability bootstrap: /health/info + /health/capabilities fetched on load ──
    def test__bootstrap_fetches_info_and_capabilities(self):
        assert "apiGet('/health/info')"         in self.html
        assert "apiGet('/health/capabilities')" in self.html
        assert 'function bootstrap'             in self.html
        assert 'let CAPABILITIES'               in self.html                           # exposed for later capability-driven UI (P2)

    # ── bug-fix: ${url} was injected raw into innerHTML (XSS / markup break) ──
    def test__batch_grid_escapes_url(self):
        assert 'const u     = escHtml(url)' in self.html                               # url escaped before interpolation
        assert 'title="${url}"'             not in self.html                           # no raw url in an attribute
        assert '${i+1}. ${url}'             not in self.html                           # no raw url in label text

    # ── bug-fix: batch render must survive a non-array screenshots payload ──
    def test__batch_guards_non_array_screenshots(self):
        assert 'Array.isArray(data.screenshots)' in self.html
        assert 'data.screenshots || []'          not in self.html

    # ── bug-fix: /docs link was absolute (/docs) → broke behind the /pw proxy ──
    def test__docs_link_is_prefix_aware(self):
        assert 'id="docs-link"'           in self.html
        assert "a.href = window.API_BASE + '/docs'" in self.html
        assert '<a href="/docs"'          not in self.html                             # the old absolute href is gone

    def test__docs_link_prefixed_behind_proxy(self):
        html = _render({'x-forwarded-prefix': '/pw'})
        assert 'window.API_BASE="/pw";' in html                                        # resolver still wins; docs-link composes off API_BASE at runtime

    # ── "html" is a render format, not a screenshot format ──
    def test__format_toggle_relabelled(self):
        assert 'Image (PNG)' in self.html
        assert 'HTML source' in self.html
        assert 'PNG screenshot' not in self.html
