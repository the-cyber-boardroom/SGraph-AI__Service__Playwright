# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.api.routes.Routes__Config
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from sg_compute_specs.mitmproxy.core.consts                                          import env_vars
from sg_compute_specs.mitmproxy.api.Fast_API__Agent_Mitmproxy                        import Fast_API__Agent_Mitmproxy


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'test-key-config'
SCRIPT_SRC    = "# fake interceptor\naddons = []\n"


class test_Routes__Config(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w')
        cls.tmp.write(SCRIPT_SRC)
        cls.tmp.close()
        os.environ[env_vars.ENV_VAR__API_KEY_NAME     ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE    ] = API_KEY_VALUE
        os.environ[env_vars.ENV_VAR__INTERCEPTOR_PATH ] = cls.tmp.name
        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME    , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE   , None)
        os.environ.pop(env_vars.ENV_VAR__INTERCEPTOR_PATH, None)
        os.unlink(cls.tmp.name)

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__interceptor_returns_source(self):
        response = self.client.get('/config/interceptor', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['path'      ].endswith('.py')
        assert body['size_bytes'] == len(SCRIPT_SRC)
        assert body['source'    ] == SCRIPT_SRC

    def test__interceptor_missing_returns_503(self):
        original = os.environ[env_vars.ENV_VAR__INTERCEPTOR_PATH]
        try:
            os.environ[env_vars.ENV_VAR__INTERCEPTOR_PATH] = '/tmp/definitely-not-here.py'
            response = self.client.get('/config/interceptor', headers=self._headers())
            assert response.status_code == 503
        finally:
            os.environ[env_vars.ENV_VAR__INTERCEPTOR_PATH] = original
