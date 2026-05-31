# ═══════════════════════════════════════════════════════════════════════════════
# Live — regression sentinels for the @Content driving-session debrief
# (2026-05-30). Each test maps 1:1 to a bug fixed in Φ1 (commit b5d951c).
# If any of these go red, a fix has been undone. They are intentionally
# narrow and well-named so a CI failure points straight at the regression.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__EXAMPLE, TARGET__VAULT_URL


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _base_body(steps):
    return {'capture_config' : {}                ,
            'sequence_config': {}                ,
            'steps'          : steps             }


class test_bug_1__vault_url_validation(TestCase):

    def test__navigate_step_accepts_vault_url_with_colon_in_fragment(self):              # BUG-1 — pre-fix this returned HTTP 422 from Safe_Str__Url regex
        body = _base_body([{'action': 'navigate', 'url': TARGET__VAULT_URL,
                            'timeout_ms': 5000}])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text                                          # 200 even if navigation later fails — the validation gate is what we test
            resp = r.json()
            assert 'completed' in resp['status'] or 'partial' in resp['status'] or 'failed' in resp['status']


class test_bug_2__polymorphic_step_results(TestCase):

    def test__content_field_survives_json_serialisation(self):                           # BUG-2 — pre-fix step_results[*].content was stripped by Pydantic narrowing to Schema__Step__Result__Base
        body = _base_body([
            {'action': 'navigate'   , 'url': TARGET__EXAMPLE                              },
            {'action': 'get_content', 'content_format': 'html', 'inline_in_response': True},
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            assert results[1].get('content') is not None                                 # Pre-fix: None (stripped); post-fix: actual HTML

    def test__url_field_survives_json_serialisation(self):                               # BUG-2 — same regression class, different subclass field
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__EXAMPLE},
            {'action': 'get_url'                          },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            assert results[1].get('url') is not None
            assert results[1]['url'].startswith('https://example.com')


class test_fr_5a__evaluate_return_value(TestCase):

    def test__screenshot_with_javascript_proves_evaluate_execution(self):                # FR-5a — /screenshot's allow_all runner is the only public path that exercises evaluate today; if the JS doesn't mutate the DOM, the evaluate plumbing is broken
        with _client() as c:
            r = c.post('/screenshot', json={'url': TARGET__EXAMPLE,
                                             'format': 'html',
                                             'javascript': 'document.body.setAttribute("data-evaluated","yes")'})
            assert r.status_code == 200, r.text
            html = r.json().get('html') or ''
            assert 'data-evaluated="yes"' in html                                        # The JS ran before the HTML capture
