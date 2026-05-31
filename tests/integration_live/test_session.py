# ═══════════════════════════════════════════════════════════════════════════════
# Live — Φ7 opt-in stateful session handle.
#
# Open → act (navigate) → probe (read multiple facets) → close.
# Proves the amortisation use-case: one browser launch + navigate, then N
# probe batches against the same DOM state without re-paying launch cost.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _open(c, ttl_ms=60_000):
    r = c.post('/session/open', json={'ttl_ms': ttl_ms})
    assert r.status_code == 200, r.text
    return r.json()['session_id']


def _close(c, session_id):
    return c.post(f'/session/{session_id}/close')


class test_session_lifecycle(TestCase):

    def test__open_returns_session_id_and_expiry(self):
        with _client() as c:
            r = c.post('/session/open', json={'ttl_ms': 30_000})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body.get('session_id')
            assert int(body['expires_in_ms']) == 30_000
            assert int(body['expires_at_ms']) > 0
            _close(c, body['session_id'])

    def test__close_marks_session_closed(self):
        with _client() as c:
            sid = _open(c)
            r = _close(c, sid)
            assert r.status_code == 200, r.text
            assert r.json()['closed'] is True

    def test__close_unknown_session_returns_closed_false(self):
        with _client() as c:
            r = _close(c, 'never-existed-id')
            assert r.status_code == 200, r.text
            assert r.json()['closed'] is False


class test_session_act_then_probe(TestCase):

    def test__act_navigates_held_page_then_probe_reads_same_page(self):                   # The amortisation pattern: one act (navigate), multiple probes
        with _client() as c:
            sid = _open(c)
            try:
                # act: navigate the held page
                act_body = {'steps': [{'action': 'navigate', 'url': TARGET__SGRAPH}]}
                ra = c.post(f'/session/{sid}/act', json=act_body)
                assert ra.status_code == 200, ra.text
                act_resp = ra.json()
                # Surface the per-step error_message on failure — bare "status=failed" is uninformative
                if act_resp['status'] != 'completed':
                    step_errors = [(r.get('action'), r.get('status'), r.get('error_type'), r.get('error_message'))
                                   for r in act_resp.get('step_results', [])]
                    self.fail(f'/session/act navigate failed. sequence status={act_resp["status"]}, step_results={step_errors}')

                # probe: read URL + DOM tree, no navigate (page is already loaded)
                probe_body = {'settle': [], 'probes': {'where': {'action': 'get_url'},
                                                        'shape': {'action': 'get_dom_tree', 'max_depth': 2}}}
                rp = c.post(f'/session/{sid}/probe', json=probe_body)
                assert rp.status_code == 200, rp.text
                probe_resp = rp.json()
                assert probe_resp['probe_results']['where']['url'].startswith('https://sgraph.ai')
                assert probe_resp['probe_results']['shape']['dom_tree']['tag'] == 'body'

                # probe again — proves the page persists across calls
                rp2 = c.post(f'/session/{sid}/probe', json=probe_body)
                assert rp2.status_code == 200, rp2.text
                assert rp2.json()['probe_results']['where']['url'].startswith('https://sgraph.ai')
            finally:
                _close(c, sid)

    def test__probe_against_unknown_session_returns_404(self):
        with _client() as c:
            r = c.post('/session/does-not-exist/probe',
                        json={'settle': [], 'probes': {'x': {'action': 'get_url'}}})
            assert r.status_code == 404, r.text

    def test__act_against_unknown_session_returns_404(self):
        with _client() as c:
            r = c.post('/session/does-not-exist/act', json={'steps': []})
            assert r.status_code == 404, r.text
