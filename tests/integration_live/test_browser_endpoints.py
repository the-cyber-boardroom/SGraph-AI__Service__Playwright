# ═══════════════════════════════════════════════════════════════════════════════
# Live — /browser/* one-shot endpoints. Each of the six routes exercised
# once against a stable target. Reuses the session-scoped HTTPX client so
# total wall-clock is dominated by Chromium launches (~1.5–3s each), not
# Python/connection setup.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__EXAMPLE


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


class test_browser_routes(TestCase):

    def test__navigate(self):
        with _client() as c:
            r = c.post('/browser/navigate', json={'url': TARGET__EXAMPLE})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['url']                == TARGET__EXAMPLE
            assert body['final_url'].startswith('https://example.com')
            assert body['duration_ms'] > 0
            assert body['timings']['total_ms'] > 0

    def test__get_content_returns_html(self):
        with _client() as c:
            r = c.post('/browser/get-content', json={'url': TARGET__EXAMPLE})
            assert r.status_code == 200, r.text
            body = r.json()
            assert 'Example Domain' in (body.get('html') or '')                           # example.com's distinctive content

    def test__get_url(self):
        with _client() as c:
            r = c.post('/browser/get-url', json={'url': TARGET__EXAMPLE})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['final_url'].startswith('https://example.com')

    def test__screenshot_returns_png_bytes(self):
        with _client() as c:
            r = c.post('/browser/screenshot', json={'url': TARGET__EXAMPLE})
            assert r.status_code == 200, r.text
            assert r.headers.get('content-type', '').startswith('image/png')
            assert r.content[:8] == b'\x89PNG\r\n\x1a\n'                                  # PNG magic bytes
            assert int(r.headers.get('X-Total-Ms', '0')) > 0

    def test__click_no_op_against_static_page(self):                                     # No clickable target on example.com beyond <a>; assert the route at least round-trips
        with _client() as c:
            r = c.post('/browser/click', json={'url': TARGET__EXAMPLE,
                                                'selector': 'a'})                        # example.com has exactly one <a>
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['final_url']                                                     # URL recorded post-click

    def test__fill_against_form_input_returns_200_or_validation_error(self):             # example.com has no <input>; the route must surface a clean failure, not crash
        with _client() as c:
            r = c.post('/browser/fill', json={'url': TARGET__EXAMPLE,
                                               'selector': 'input[name=q]',
                                               'value': 'hello'})
            assert r.status_code in (200, 422, 502)                                      # 200 if the runtime treats missing selector as no-op; 422/502 if it raises
