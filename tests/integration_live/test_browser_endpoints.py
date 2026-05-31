# ═══════════════════════════════════════════════════════════════════════════════
# Live — /browser/* one-shot endpoints. Each of the JSON-returning routes
# exercised once against sgraph.ai (lightest real target). Click + fill
# probe-style tests against sgraph.ai assert clean failure surfaces (the
# selectors may or may not exist) — the value is verifying the route
# round-trips, not asserting on the marketing site's exact DOM.
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

    def test__click_route_round_trips_cleanly(self):                                 # Whether or not 'a' exists, the route must return a structured response, never crash
        with _client() as c:
            r = c.post('/browser/click', json={'url': TARGET__SGRAPH, 'selector': 'a'})
            assert r.status_code in (200, 422, 502), r.text                          # 200 if the click landed; 422/502 if the runtime classified the failure

    def test__fill_route_round_trips_cleanly(self):                                  # Same shape: the surface must surface a clean status, never a 5xx with no body
        with _client() as c:
            r = c.post('/browser/fill', json={'url'     : TARGET__SGRAPH         ,
                                               'selector': 'input[name=q]'        ,
                                               'value'   : 'hello'                })
            assert r.status_code in (200, 422, 502), r.text
