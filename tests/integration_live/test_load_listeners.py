# ═══════════════════════════════════════════════════════════════════════════════
# Live — Φ4 load-time forensics (FR-5c console + network + FR-1d network_idle_ms).
#
# Sequence__Runner attaches the listener buffer BEFORE the first navigate.
# These tests prove the buffered events round-trip through the new verbs
# and (when caller opts in via capture_config) get emitted as terminal
# artefacts at sequence end.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _base_body(steps, capture_config=None):
    return {'capture_config' : capture_config or {} ,
            'sequence_config': {}                   ,
            'steps'          : steps                }


class test_get_console_tail(TestCase):

    def test__after_navigate_returns_a_console_log_list(self):                            # Console list may be empty (sgraph.ai is quiet); contract is "list returned, no crash"
        body = _base_body([
            {'action': 'navigate'        , 'url': TARGET__SGRAPH},
            {'action': 'get_console_tail', 'lines': 50          },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            step = r.json()['step_results'][1]
            assert step['status']         == 'passed', f'get_console_tail failed: {step.get("error_message")}'
            assert step['action']         == 'get_console_tail'
            assert isinstance(step.get('console_log'), list)                                # May be [] if site has no console output


class test_get_network_failures(TestCase):

    def test__after_navigate_returns_a_failures_list(self):                               # sgraph.ai likely has zero requestfailed events — the verb's job is to return [] gracefully
        body = _base_body([
            {'action': 'navigate'            , 'url': TARGET__SGRAPH},
            {'action': 'get_network_failures'                       },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            step = r.json()['step_results'][1]
            assert step['status']            == 'passed', f'get_network_failures failed: {step.get("error_message")}'
            assert step['action']            == 'get_network_failures'
            assert isinstance(step.get('network_failures'), list)


import pytest


class test_wait_for_network_idle_ms(TestCase):

    @pytest.mark.skip(reason='sgraph.ai marketing site has analytics beacons + long-polling '
                              'that prevent in_flight from ever reaching 0 within a sensible '
                              'timeout — even with websocket/eventsource filtering. The verb '
                              'itself works (covered by 3 unit tests in test_Step__Executor.py '
                              ': test_wait_for_network_idle_ms) and is useful on pages that '
                              'do actually go quiet (vault, internal apps). Re-enable when '
                              'we have a quiet *.sgraph target to point at.')
    def test__waits_for_quiet_window_after_navigate(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH                                       },
            {'action': 'wait_for', 'network_idle_ms': 500, 'timeout_ms': 15000                 },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            assert results[1]['status'] == 'passed', f'wait_for network_idle_ms failed: {results[1].get("error_message")}'
            assert results[1]['action'] == 'wait_for'


class test_end_of_sequence_artefact_emission(TestCase):                                    # FR-5c — opt-in via capture_config

    def test__console_log_artefact_emitted_when_enabled(self):
        body = _base_body(
            steps=[{'action': 'navigate', 'url': TARGET__SGRAPH}],
            capture_config={'console_log': {'enabled': True, 'sink': 'inline'}})
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            console_arts = [a for a in resp.get('artefacts', []) if a.get('artefact_type') == 'console_log']
            # The artefact only fires when the page actually produced console output.
            # sgraph.ai may or may not — assertion is "if it fired, it's well-formed".
            for art in console_arts:
                assert int(art['size_bytes']) > 0
                if art.get('inline_b64'):
                    decoded = base64.b64decode(art['inline_b64']).decode('utf-8')
                    payload = json.loads(decoded)
                    assert isinstance(payload, list)

    def test__network_log_artefact_emitted_when_enabled(self):                            # network_log SHOULD fire — any navigate produces requests
        body = _base_body(
            steps=[{'action': 'navigate', 'url': TARGET__SGRAPH}],
            capture_config={'network_log': {'enabled': True, 'sink': 'inline'}})
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            resp = r.json()
            network_arts = [a for a in resp.get('artefacts', []) if a.get('artefact_type') == 'network_log']
            assert network_arts, f'expected a network_log artefact, got: {[a.get("artefact_type") for a in resp.get("artefacts", [])]}'
            art = network_arts[0]
            assert int(art['size_bytes']) > 0
            decoded = base64.b64decode(art['inline_b64']).decode('utf-8')
            payload = json.loads(decoded)
            assert set(payload.keys()) == {'requests', 'responses', 'failed'}
            assert len(payload['requests']) >= 1                                          # At least the document GET
