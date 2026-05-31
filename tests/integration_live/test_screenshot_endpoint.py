# ═══════════════════════════════════════════════════════════════════════════════
# Live — /screenshot endpoint (Schema__Screenshot__Response, base64 PNG in JSON).
# Distinct from /browser/screenshot which streams raw image/png. The simple
# /screenshot surface also bypasses the JS allowlist (allow_all=True on its
# dedicated runner) — so this is where FR-5a evaluate-return gets live cover.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from unittest import TestCase

from tests.integration_live.conftest import TARGET__EXAMPLE


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


class test_screenshot_simple(TestCase):

    def test__png_format_returns_base64_png(self):
        with _client() as c:
            r = c.post('/screenshot', json={'url': TARGET__EXAMPLE, 'format': 'png'})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body['url']        == TARGET__EXAMPLE
            assert body['screenshot_b64']                                                # non-empty
            png_bytes = base64.b64decode(body['screenshot_b64'])
            assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test__html_format_returns_rendered_html(self):
        with _client() as c:
            r = c.post('/screenshot', json={'url': TARGET__EXAMPLE, 'format': 'html'})
            assert r.status_code == 200, r.text
            body = r.json()
            assert 'Example Domain' in (body.get('html') or '')

    def test__javascript_param_runs_against_allow_all_runner(self):                       # FR-5a sentinel — /screenshot uses allow_all=True so arbitrary JS is permitted (each call is an isolated session); proves the evaluate plumbing works end-to-end
        with _client() as c:
            r = c.post('/screenshot', json={'url': TARGET__EXAMPLE,
                                             'format': 'html',
                                             'javascript': 'document.title = "patched"'})
            assert r.status_code == 200, r.text
            body = r.json()
            assert '<title>patched</title>' in (body.get('html') or '')                  # JS actually ran before HTML capture
