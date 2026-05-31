# ═══════════════════════════════════════════════════════════════════════════════
# Live — Φ2 quick-win sentinels.
#   • FR-4 plain `wait` verb
#   • FR-1b `wait_for: selector_gone`
#   • FR-7 artefact dimensions on screenshot
#   • FR-7 viewport shorthand on screenshot
#
# FR-1a `wait_for: text` is NOT exercised here because the public *.sgraph
# targets don't expose a predictable late-loading text string the test
# could reliably watch for. The Φ2 unit suite covers the code path via
# _Fake_Page; this tier validates the verbs that round-trip observable
# side-effects (durations, dims, screenshots).
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _base_body(steps):
    return {'capture_config' : {}, 'sequence_config': {}, 'steps': steps}


class test_wait_verb(TestCase):

    def test__wait_step_completes_and_adds_duration(self):                           # FR-4 — duration_ms is honoured (the sequence took at least this long)
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH},
            {'action': 'wait'    , 'duration_ms': 300   },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['status'] == 'completed'
            wait_result = resp['step_results'][1]
            assert wait_result['action'] == 'wait'
            assert wait_result['status'] == 'passed'
            assert wait_result['duration_ms'] >= 250                                 # 300 nominal, allow 50ms slop on the lower bound


class test_wait_for_selector_gone(TestCase):

    def test__selector_gone_against_already_absent_selector_passes_immediately(self):  # FR-1b — selector that never existed is trivially "gone"
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH                                              },
            {'action': 'wait_for', 'selector': '#never-existed-selector', 'selector_gone': True,
             'timeout_ms': 3000                                                                        },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            assert resp['step_results'][1]['status'] == 'passed'                     # 'detached' state is satisfied by absence


class test_screenshot_dimensions_and_viewport(TestCase):

    def test__screenshot_ref_carries_width_and_height(self):                         # FR-7 — PNG dims surfaced on the artefact ref
        body = _base_body([
            {'action': 'navigate'  , 'url': TARGET__SGRAPH                            },
            {'action': 'screenshot', 'full_page': False                                },
        ])
        body['capture_config'] = {'screenshot': {'enabled': True, 'sink': 'inline'}}
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            artefacts = resp['step_results'][1].get('artefacts') or []
            assert artefacts, 'screenshot artefact missing from result'
            art = artefacts[0]
            assert art.get('width' ) is not None and int(art['width' ]) > 0
            assert art.get('height') is not None and int(art['height']) > 0

    def test__viewport_shorthand_resizes_before_snapping(self):                      # FR-7 — viewport on Schema__Step__Screenshot is honoured
        body = _base_body([
            {'action': 'navigate'  , 'url': TARGET__SGRAPH                                                 },
            {'action': 'screenshot', 'full_page': False, 'viewport': {'width': 800, 'height': 600}          },
        ])
        body['capture_config'] = {'screenshot': {'enabled': True, 'sink': 'inline'}}
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            artefacts = resp['step_results'][1].get('artefacts') or []
            assert artefacts, 'screenshot artefact missing from result'
            art = artefacts[0]
            assert int(art['width' ]) == 800
            assert int(art['height']) == 600
            png = base64.b64decode(art['inline_b64'])
            assert png[:8] == b'\x89PNG\r\n\x1a\n'                                   # Real PNG, not an error stub
