# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — TestClient integration tests for Fast_API__SP__CLI
# Boots the real FastAPI app and checks plugin-route wiring + auth middleware.
# The legacy /ec2/playwright/* routes were retired in v0.2.29 — superseded by
# sg_compute_specs/playwright/ and the upcoming sg aws ec2 namespace.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                                                          import Fast_API__SP__CLI


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'
API_KEY_NAME           = 'X-API-Key'
API_KEY_VALUE          = 'test-key-sp-cli'


class test_Fast_API__SP__CLI(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        cls.fast_api      = Fast_API__SP__CLI().setup()
        cls.client        = cls.fast_api.client()

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(ENV_VAR__API_KEY_VALUE, None)

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test_docker_routes_are_mounted(self):                                       # Verify all five docker/* paths are registered
        paths  = {str(p) for p in self.fast_api.routes_paths_all()}                # osbot helper expands _IncludedRouter (FastAPI >= 0.137 / Starlette 1.x no longer flattens)
        assert '/docker/stacks'              in paths
        assert '/docker/stack'               in paths
        assert '/docker/stack/{name}'        in paths
        assert '/docker/stack/{name}/health' in paths

    def test_docker_list_stacks__is_reachable(self):                                # GET /docker/stacks — unauthenticated → 401
        response = self.client.get('/docker/stacks')
        assert response.status_code == 401

    def test_catalog_routes_are_mounted(self):
        paths = {str(p) for p in self.fast_api.routes_paths_all()}                 # osbot helper expands _IncludedRouter (FastAPI >= 0.137 / Starlette 1.x no longer flattens)
        assert '/catalog/types'  in paths
        assert '/catalog/stacks' in paths

    def test_elastic_routes_are_mounted(self):
        paths = {str(p) for p in Fast_API__SP__CLI().setup().routes_paths_all()}   # osbot helper expands _IncludedRouter (FastAPI >= 0.137 / Starlette 1.x no longer flattens)
        assert '/elastic/stacks'              in paths
        assert '/elastic/stack/{name}'        in paths
        assert '/elastic/stack'               in paths
        assert '/elastic/stack/{name}/health' in paths

    def test_vnc_routes_are_mounted(self):                                            # Verify all VNC paths are registered (Stack + Flows)
        paths = {str(p) for p in Fast_API__SP__CLI().setup().routes_paths_all()}   # osbot helper expands _IncludedRouter (FastAPI >= 0.137 / Starlette 1.x no longer flattens)
        assert '/vnc/stacks'              in paths
        assert '/vnc/stack'               in paths
        assert '/vnc/stack/{name}'        in paths
        assert '/vnc/stack/{name}/health' in paths
        assert '/vnc/stack/{name}/flows'  in paths

    def test_vnc_service_is_wired(self):                                              # plugin_registry.setup_all() must call vnc_service.setup() or first request AttributeErrors
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__SG__Helper import Vnc__SG__Helper
        api     = Fast_API__SP__CLI().setup()
        vnc_svc = api.plugin_registry.service_for('vnc')
        assert isinstance(vnc_svc.aws_client.sg, Vnc__SG__Helper)
