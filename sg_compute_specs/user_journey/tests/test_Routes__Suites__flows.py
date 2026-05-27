# ═══════════════════════════════════════════════════════════════════════════════
# Tests — conductor GET /suites/{run}/flows (NDJSON, proxied from the capture sidecar)
# Swaps the module-level CAPTURE_CLIENT for a canned one (no HTTP, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from sg_compute_specs.user_journey.core.clients.Mitmproxy__Capture__Client import Mitmproxy__Capture__Client
from sg_compute_specs.user_journey.core.conductor.api.Fast_API__Conductor   import Fast_API__Conductor
import sg_compute_specs.user_journey.core.conductor.api.routes.Routes__Suites as routes_mod

API_KEY_HEADER = 'X-API-Key'
API_KEY_VALUE  = 'test-key-conductor'


class _Canned_Capture(Mitmproxy__Capture__Client):
    def network_log(self, run_id):
        return [{'method': 'GET',  'status': 200, 'url': f'https://shop.test/{run_id}'},
                {'method': 'POST', 'status': 403, 'url': 'https://shop.test/checkout'}]


class test_flows_route(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['FAST_API__AUTH__API_KEY__NAME' ] = API_KEY_HEADER
        os.environ['FAST_API__AUTH__API_KEY__VALUE'] = API_KEY_VALUE
        cls.client = TestClient(Fast_API__Conductor().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop('FAST_API__AUTH__API_KEY__NAME' , None)
        os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)

    def setUp(self):
        self._saved = routes_mod.CAPTURE_CLIENT
        routes_mod.CAPTURE_CLIENT = _Canned_Capture()

    def tearDown(self):
        routes_mod.CAPTURE_CLIENT = self._saved

    def test__flows_returns_ndjson(self):
        response = self.client.get('/suites/run-1/flows', headers={API_KEY_HEADER: API_KEY_VALUE})
        assert response.status_code == 200
        lines = [line for line in response.text.splitlines() if line.strip()]
        assert len(lines) == 2
        assert 'https://shop.test/run-1' in lines[0]
        assert '403' in lines[1]

    def test__flows_path_registered(self):
        assert '/suites/{suite_run_id}/flows' in routes_mod.ROUTES_PATHS__SUITES
