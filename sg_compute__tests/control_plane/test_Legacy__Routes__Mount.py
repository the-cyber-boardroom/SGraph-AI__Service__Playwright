# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — BV2.10 legacy route mount in Fast_API__Compute
# Verifies that Fast_API__Compute serves both /api/* and /legacy/* from one
# process, and that every legacy response carries X-Deprecated: true.
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

    def test_api_specs_has_no_deprecated_header(self):
        r = self.client.get('/api/specs')
        assert 'x-deprecated' not in r.headers

    # ── /legacy/catalog/* responds correctly ──────────────────────────────────

    def test_legacy_catalog_types_returns_200(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.status_code == 200

    def test_legacy_catalog_types_has_deprecated_header(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.headers.get('x-deprecated') == 'true'

    def test_legacy_catalog_types_has_migration_path_header(self):
        r = self.client.get('/legacy/catalog/types')
        assert r.headers.get('x-migration-path') == '/api/specs'

    def test_legacy_catalog_manifest_is_reachable(self):
        r = self.client.get('/legacy/catalog/manifest')
        assert r.status_code == 200
        assert r.headers.get('x-deprecated') == 'true'

    # ── /legacy/* route topology ─────────────────────────────────────────────

    def test_legacy_routes_registered(self):
        all_paths = {str(r.path) for r in self.fast_api.app().routes
                     if hasattr(r, 'path')}
        assert '/legacy/catalog/types'            in all_paths
        assert '/legacy/catalog/stacks'           in all_paths
        assert '/legacy/catalog/manifest'         in all_paths
        assert '/legacy/ec2/playwright/list'      in all_paths
        assert '/legacy/ec2/playwright/info/{name}' in all_paths
        assert '/legacy/observability/stacks'     in all_paths

    def test_legacy_plugin_routes_registered(self):
        all_paths = {str(r.path) for r in self.fast_api.app().routes
                     if hasattr(r, 'path')}
        assert '/legacy/docker/stacks'            in all_paths
        assert '/legacy/docker/stack'             in all_paths

    def test_unknown_legacy_path_returns_404(self):
        r = self.client.get('/legacy/nonexistent/path')
        assert r.status_code == 404

    # ── /legacy/observability/stacks works (no AWS needed) ───────────────────

    def test_legacy_observability_stacks_returns_200(self):
        r = self.client.get('/legacy/observability/stacks')
        assert r.status_code == 200
        assert r.headers.get('x-deprecated') == 'true'
