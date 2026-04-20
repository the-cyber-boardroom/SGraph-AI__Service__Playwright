# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/fast_api/routes/Routes__Metrics.py (GET /metrics)
#
# Verifies route registration, correct Content-Type, expected metric names,
# and API-key enforcement. Uses the same setUpClass + TestClient pattern as
# sibling agent_mitmproxy route tests.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from agent_mitmproxy.consts                                                          import env_vars
from agent_mitmproxy.fast_api.Fast_API__Agent_Mitmproxy                              import Fast_API__Agent_Mitmproxy
from agent_mitmproxy.fast_api.routes.Routes__Metrics                                 import (ROUTES_PATHS__METRICS,
                                                                                             TAG__ROUTES_METRICS  )


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'test-key-metrics'


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_METRICS   == 'metrics'
        assert ROUTES_PATHS__METRICS == ['/metrics']


class test_Routes__Metrics(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[env_vars.ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE, None)

    def _auth(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__returns_200_with_prometheus_content_type(self):
        response = self.client.get('/metrics', headers=self._auth())
        assert response.status_code == 200
        assert 'text/plain' in response.headers.get('content-type', '')

    def test__response_body_contains_expected_metric_names(self):
        response = self.client.get('/metrics', headers=self._auth())
        body     = response.text
        assert 'sg_mitmproxy_flows_total'          in body
        assert 'sg_mitmproxy_flow_duration_seconds' in body
        assert 'sg_mitmproxy_bytes_request_total'  in body
        assert 'sg_mitmproxy_bytes_response_total' in body

    def test__requires_api_key(self):
        response = self.client.get('/metrics')                                      # No auth header
        assert response.status_code == 401
