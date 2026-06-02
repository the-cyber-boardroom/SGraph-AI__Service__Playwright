# ═══════════════════════════════════════════════════════════════════════════════
# Live — /sequence/execute multi-step. This is the route that hides the
# BUG-2 class of regression: typed response_model on a polymorphic list
# silently drops subclass-only fields (content / url / return_value).
# Pure-Python unit tests can't see that bug — only a JSON round-trip over
# real HTTP exposes it. These tests assert on the wire payload directly.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH, TARGET__SEND


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _base_body(steps):                                                                   # Minimal valid Schema__Sequence__Request payload
    return {'capture_config' : {}                ,
            'sequence_config': {}                ,
            'steps'          : steps             }


class test_sequence_execute__sgraph_ai(TestCase):

    def test__navigate_then_get_url_then_get_content__all_subclass_fields_preserved(self):  # BUG-2 sentinel — every subclass-only field must survive the wire
        body = _base_body([
            {'action': 'navigate'   , 'url': TARGET__SGRAPH                               },
            {'action': 'get_url'                                                          },
            {'action': 'get_content', 'content_format': 'html', 'inline_in_response': True},
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['status']       == 'completed'
            assert resp['steps_passed'] == 3
            results = resp['step_results']
            assert len(results) == 3
            assert results[1].get('url', '').startswith('https://sgraph.ai')         # get_url result — would be None pre-BUG-2-fix
            html = results[2].get('content') or ''                                   # get_content result — would be None pre-BUG-2-fix
            assert '<html' in html.lower()
            assert results[2].get('content_format') == 'html'


class test_sequence_execute__send_sgraph_ai(TestCase):

    def test__real_product_surface_loads_and_renders_dom(self):                      # send.sgraph.ai is the live product UI — heavier JS than the marketing site
        body = _base_body([
            {'action': 'navigate'   , 'url': TARGET__SEND, 'wait_until': 'load'           },
            {'action': 'get_url'                                                          },
            {'action': 'get_content', 'content_format': 'html', 'inline_in_response': True},
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['status']       == 'completed'
            results = resp['step_results']
            assert results[1].get('url', '').startswith('https://send.sgraph.ai')
            html = results[2].get('content') or ''
            assert len(html) > 500                                                   # Some real markup arrived
