# ═══════════════════════════════════════════════════════════════════════════════
# Live — Φ5 POST /inspect probe-batch.
#
# Headline feature from the @Content debrief: snapshot-once, probe-many.
# One navigate + settle, then a named bag of read-only probes against the
# same DOM state. Caller looks up results by their own probe names.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


class test_inspect_happy_path(TestCase):

    def test__navigate_settle_three_probes_returns_named_results(self):
        body = {'navigate' : {'url': TARGET__SGRAPH                                                                  },
                'settle'   : [{'action': 'wait_for', 'state': 'load'                                                  }],
                'probes'   : {'current_url' : {'action': 'get_url'                                                    },
                              'page_text'   : {'action': 'get_text'                                                   },
                              'page_dom'    : {'action': 'get_dom_tree' , 'max_depth': 2                              }},
                'diagnostics_on_fail': True}
        with _client() as c:
            r = c.post('/inspect', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['status']                                  == 'completed'
            assert resp['navigate_result']['action']               == 'navigate'
            assert resp['navigate_result']['status']               == 'passed'
            assert len(resp['settle_results'])                     == 1
            assert resp['settle_results'][0]['action']             == 'wait_for'
            assert set(resp['probe_results'].keys())               == {'current_url', 'page_text', 'page_dom'}
            assert resp['probe_results']['current_url']['status']  == 'passed'
            assert resp['probe_results']['current_url']['url'].startswith('https://sgraph.ai')
            assert resp['probe_results']['page_dom']['dom_tree']['tag'] == 'body'
            assert resp['diagnostics']                             is None                              # All passed → no diagnostics

    def test__inspect_supports_a11y_probe_via_cdp(self):
        body = {'navigate': {'url': TARGET__SGRAPH                                  },
                'settle'  : []                                                       ,
                'probes'  : {'a11y': {'action': 'get_a11y_tree', 'interesting_only': False}}}
        with _client() as c:
            r = c.post('/inspect', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            a11y = resp['probe_results']['a11y']
            assert a11y['status'] == 'passed', f'a11y probe failed: {a11y.get("error_message")}'
            assert 'nodes' in (a11y.get('accessibility_tree') or {})


class test_inspect_validation(TestCase):

    def test__mutating_probe_action_is_rejected_422(self):                                              # Probes are read-only by contract; mutating verbs are caller error
        body = {'navigate': {'url': TARGET__SGRAPH                                  },
                'settle'  : []                                                       ,
                'probes'  : {'bad': {'action': 'click', 'selector': 'a'}}}
        with _client() as c:
            r = c.post('/inspect', json=body)
            assert r.status_code == 422, f'expected 422 (read-only allowlist), got {r.status_code}: {r.text[:300]}'
            err = (r.json().get('detail') or r.text).lower()
            assert 'read-only' in err or 'click' in err


class test_inspect_diagnostics_on_fail(TestCase):

    def test__failed_settle_populates_diagnostics(self):                                                 # settle waits for a selector that doesn't exist → step fails → diagnostics emitted
        body = {'navigate'           : {'url': TARGET__SGRAPH                                                                            },
                'settle'             : [{'action': 'wait_for', 'selector': '#never-going-to-be-here-xyz', 'timeout_ms': 2000             }],
                'probes'             : {'current_url': {'action': 'get_url'}}                                                              ,
                'diagnostics_on_fail': True                                                                                                 }
        with _client() as c:
            r = c.post('/inspect', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['status'] in ('failed', 'partial'), f'expected failed/partial, got {resp["status"]}'
            assert resp['diagnostics'] is not None,        'expected diagnostics on settle failure'
            assert 'console_log'      in resp['diagnostics']
            assert 'network_failures' in resp['diagnostics']

    def test__diagnostics_off_skips_diagnostics_field_even_on_failure(self):
        body = {'navigate'           : {'url': TARGET__SGRAPH                                                                            },
                'settle'             : [{'action': 'wait_for', 'selector': '#never-going-to-be-here-xyz', 'timeout_ms': 2000             }],
                'probes'             : {'current_url': {'action': 'get_url'}}                                                              ,
                'diagnostics_on_fail': False                                                                                                }
        with _client() as c:
            r = c.post('/inspect', json=body)
            assert r.status_code == 200, r.text
            assert r.json()['diagnostics'] is None
