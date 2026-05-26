# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.api.routes.Routes__Capture
#
# GET /capture/network-log/{run_id}. Verifies route registration, NDJSON body,
# the flow-count header, empty-200 for unknown runs, and API-key enforcement.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from sg_compute_specs.mitmproxy.core.consts                                          import env_vars
from sg_compute_specs.mitmproxy.api.Fast_API__Agent_Mitmproxy                        import Fast_API__Agent_Mitmproxy
from sg_compute_specs.mitmproxy.api.routes.Routes__Capture                           import (ROUTES_PATHS__CAPTURE ,
                                                                                             TAG__ROUTES_CAPTURE   ,
                                                                                             HEADER__FLOW_COUNT    )
from sg_compute_specs.mitmproxy.core.addons.run_capture_addon                        import RUN_CAPTURE


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'test-key-capture'


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_CAPTURE   == 'capture'
        assert ROUTES_PATHS__CAPTURE == ['/capture/network-log/{run_id}']


class test_Routes__Capture(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[env_vars.ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE, None)

    def setUp(self):
        RUN_CAPTURE.clear()

    def _auth(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__returns_ndjson_for_run(self):
        RUN_CAPTURE.record('run-1', {'run_id': 'run-1', 'request': {'url': 'https://a.test/1'}})
        RUN_CAPTURE.record('run-1', {'run_id': 'run-1', 'request': {'url': 'https://a.test/2'}})

        response = self.client.get('/capture/network-log/run-1', headers=self._auth())
        assert response.status_code                       == 200
        assert 'application/x-ndjson' in response.headers.get('content-type', '')
        assert response.headers.get(HEADER__FLOW_COUNT)   == '2'

        lines = [json.loads(line) for line in response.text.splitlines()]
        assert len(lines)                  == 2
        assert lines[0]['request']['url']  == 'https://a.test/1'
        assert lines[1]['request']['url']  == 'https://a.test/2'

    def test__unknown_run_is_empty_200(self):
        response = self.client.get('/capture/network-log/does-not-exist', headers=self._auth())
        assert response.status_code                     == 200
        assert response.text                            == ''
        assert response.headers.get(HEADER__FLOW_COUNT) == '0'

    def test__requires_api_key(self):
        response = self.client.get('/capture/network-log/run-1')                    # no auth header
        assert response.status_code == 401
