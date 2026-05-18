# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Warming__Page
# Asserts HTML content, auto-refresh meta, and no-cache headers.
# No mocks, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_publish.waker.Warming__Page import Warming__Page, NO_CACHE_HEADERS


class TestWarmingPage:
    def setup_method(self):
        self.page = Warming__Page()

    def test_render_returns_string(self):
        html = self.page.render('sara-cv')
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_contains_slug(self):
        html = self.page.render('sara-cv')
        assert 'sara-cv' in html

    def test_auto_refresh_meta_present(self):
        html = self.page.render('sara-cv')
        assert 'http-equiv="refresh"' in html

    def test_default_refresh_is_10_seconds(self):
        html = self.page.render('slug-x')
        assert 'content="10"' in html

    def test_custom_refresh_seconds(self):
        page = Warming__Page(refresh_seconds=30)
        html = page.render('slug-x')
        assert 'content="30"' in html

    def test_headers_no_cache(self):
        hdrs = self.page.headers()
        cc = hdrs.get('Cache-Control', '')
        assert 'no-store' in cc
        assert 'no-cache' in cc
        assert 'must-revalidate' in cc

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
