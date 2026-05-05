# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — BV2.10 legacy route mount in Fast_API__Compute
# Verifies that Fast_API__Compute serves both /api/* (modern) and /legacy/*
# (deprecated SP CLI sub-app) from one process, and that every legacy response
# carries X-Deprecated: true + X-Migration-Path headers.
#
# Requires Python 3.12 (osbot_fast_api_serverless requires >=3.12).
# Run: python3.12 -m pytest sg_compute__tests/control_plane/test_Legacy__Routes__Mount.py
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                  import TestCase

from fastapi.testclient                                                        import TestClient

from sg_compute.control_plane.Fast_API__Compute                               import Fast_API__Compute


class test_Legacy__Routes__Mount(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fast_api = Fast_API__Compute().setup()
        cls.client   = TestClient(cls.fast_api.app(), raise_server_exceptions=False)

    # ── modern /api/* still works ────────────────────────────────────────────

    def test_api_health_still_reachable(self):
        r = self.client.get('/api/health')
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'

    def test_api_specs_still_reachable(self):
        r = self.client.get('/api/specs')
        assert r.status_code == 200
        assert 'specs' in r.json()

    # ── /api/* responses carry NO deprecation header ─────────────────────────

    def test_api_routes_have_no_deprecated_header(self):
        r = self.client.get('/api/health')
        assert 'x-deprecated' not in r.headers

    # ── /legacy/* routes enforce API-key auth (Fast_API__SP__CLI sub-app) ────

    def test_legacy_catalog_types_is_auth_gated(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.status_code == 401                                            # SP CLI middleware active

    def test_legacy_docker_stacks_is_auth_gated(self):
        r = self.client.get('/legacy/docker/stacks')
        assert r.status_code == 401

    def test_legacy_ec2_playwright_list_is_auth_gated(self):
        r = self.client.get('/legacy/ec2/playwright/list')
        assert r.status_code == 401

    # ── every legacy response carries X-Deprecated + X-Migration-Path ────────

    def test_legacy_catalog_has_deprecated_header(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.headers.get('x-deprecated') == 'true'

    def test_legacy_catalog_has_migration_path_header(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.headers.get('x-migration-path') == '/api/specs'

    def test_legacy_docker_has_deprecated_header(self):
        r = self.client.get('/legacy/docker/stacks')
        assert r.headers.get('x-deprecated') == 'true'

    def test_legacy_ec2_has_deprecated_header(self):
        r = self.client.get('/legacy/ec2/playwright/list')
        assert r.headers.get('x-deprecated') == 'true'

    # ── unknown legacy paths ──────────────────────────────────────────────────

    def test_unknown_legacy_path_is_auth_gated(self):
        r = self.client.get('/legacy/nonexistent/path')
        assert r.status_code == 401                                            # API key middleware fires before routing
