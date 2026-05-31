# ═══════════════════════════════════════════════════════════════════════════════
# Live — /browser/* one-shot endpoints. Each of the JSON-returning routes
# exercised once against sgraph.ai (lightest real target).
#
# Click + fill are intentionally NOT tested here:
#   • Click against the marketing site is a probe-test (no specific
#     selector we can rely on) and triggered navigation can leak Chromium
#     subprocesses.
#   • Fill against sgraph.ai has no real form input to target — the
#     non-existent-selector path was killing the service mid-suite
#     (RemoteProtocolError on the first /browser/fill request, then
#     connection-refused for every subsequent test). Diagnosis pending;
#     the /browser/fill verb itself is unit-tested via the executor.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


class test_browser_routes(TestCase):

    def test__navigate(self):
        with _client() as c:
            r = c.post('/browser/navigate', json={'url': TARGET__SGRAPH})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['url'].startswith('https://sgraph.ai')
            assert body['final_url'].startswith('https://sgraph.ai')
            assert body['duration_ms']         > 0
            assert body['timings']['total_ms'] > 0

    def test__get_content_returns_html(self):
        with _client() as c:
            r = c.post('/browser/get-content', json={'url': TARGET__SGRAPH})
            assert r.status_code == 200, r.text
            body = r.json()
            html = body.get('html') or ''
            assert '<html' in html.lower()
            assert len(html) > 500                                                   # Real rendered page, not an error stub

    def test__get_url(self):
        with _client() as c:
            r = c.post('/browser/get-url', json={'url': TARGET__SGRAPH})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['final_url'].startswith('https://sgraph.ai')

    def test__screenshot_returns_png_bytes(self):
        with _client() as c:
            r = c.post('/browser/screenshot', json={'url': TARGET__SGRAPH})
            assert r.status_code == 200, r.text
            assert r.headers.get('content-type', '').startswith('image/png')
            assert r.content[:8] == b'\x89PNG\r\n\x1a\n'                              # PNG magic bytes
            assert int(r.headers.get('X-Total-Ms', '0')) > 0
