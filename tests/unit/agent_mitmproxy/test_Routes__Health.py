# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/fast_api/routes/Routes__Health.py
#
# Exercises the health routes via FastAPI TestClient. The config enables
# api-key middleware so we populate the env vars + send the X-API-Key header.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from agent_mitmproxy.consts                                                          import env_vars
from agent_mitmproxy.fast_api.Fast_API__Agent_Mitmproxy                              import Fast_API__Agent_Mitmproxy


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'test-key-health'


class test_Routes__Health(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[env_vars.ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE, None)

    def _auth_headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__info(self):
        response = self.client.get('/health/info', headers=self._auth_headers())
        assert response.status_code == 200
        body = response.json()
        assert body['service_name'   ] == 'agent-mitmproxy'
        assert body['service_version'].startswith('v0.1.')
        assert body['proxy_mode'     ] == 'direct'          # no upstream env var set in this suite

    def test__info__upstream_mode(self):
        os.environ['AGENT_MITMPROXY__UPSTREAM_URL'] = 'http://upstream-proxy:8080'
        try:
            response = self.client.get('/health/info', headers=self._auth_headers())
            assert response.status_code == 200
            assert response.json()['proxy_mode'] == 'upstream'
        finally:
            os.environ.pop('AGENT_MITMPROXY__UPSTREAM_URL', None)

    def test__status_runs_file_checks(self):
        response = self.client.get('/health/status', headers=self._auth_headers())
        assert response.status_code == 200
        body = response.json()
        check_names = {c['check_name'] for c in body['checks']}
        assert check_names == {'ca_cert_exists', 'interceptor_script_exists'}        # Both checks present — values depend on disk state, not asserted here

    def test__status_uses_env_override(self):                                        # Pointing at an existing file must flip the check to healthy=True
        os.environ[env_vars.ENV_VAR__CA_CERT_PATH    ] = __file__                    # This test file definitely exists
        os.environ[env_vars.ENV_VAR__INTERCEPTOR_PATH] = __file__
        try:
            response = self.client.get('/health/status', headers=self._auth_headers())
            body = response.json()
            assert body['healthy'] is True
            for check in body['checks']:
                assert check['healthy'] is True
        finally:
            os.environ.pop(env_vars.ENV_VAR__CA_CERT_PATH    , None)
            os.environ.pop(env_vars.ENV_VAR__INTERCEPTOR_PATH, None)

    def test__info_requires_api_key(self):
        response = self.client.get('/health/info')                                    # No auth header
        assert response.status_code == 401
