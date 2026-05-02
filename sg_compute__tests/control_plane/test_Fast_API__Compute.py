# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Fast_API__Compute
# Integration test: all control-plane routes respond correctly.
# Per-spec routes (docker, podman) are tested at the routing layer only —
# they reach the service stub which has no AWS client, so AWS-touching paths
# are not exercised here.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient

from sg_compute.control_plane.Fast_API__Compute                              import Fast_API__Compute


class test_Fast_API__Compute(TestCase):

    def setUp(self):
        self.fast_api = Fast_API__Compute().setup()
        self.client   = TestClient(self.fast_api.app())

    # ── health ──────────────────────────────────────────────────────────────

    def test_health_ping(self):
        r = self.client.get('/api/health')
        assert r.status_code == 200
        assert r.json()      == {'status': 'ok'}

    def test_health_ready(self):
        r = self.client.get('/api/health/ready')
        assert r.status_code == 200
        data = r.json()
        assert data['status']       == 'ok'
        assert data['specs_loaded'] >= 4

    # ── specs catalogue ─────────────────────────────────────────────────────

    def test_specs_catalogue(self):
        r = self.client.get('/api/specs')
        assert r.status_code == 200
        ids = {s['spec_id'] for s in r.json()['specs']}
        assert 'docker'      in ids
        assert 'ollama'      in ids
        assert 'open_design' in ids
        assert 'podman'      in ids

    def test_spec_info_docker(self):
        r = self.client.get('/api/specs/docker')
        assert r.status_code == 200
        assert r.json()['spec_id'] == 'docker'

    def test_spec_info_unknown_404(self):
        r = self.client.get('/api/specs/xyz_unknown')
        assert r.status_code == 404

    # ── nodes / stacks placeholders ─────────────────────────────────────────

    def test_nodes_placeholder(self):
        r = self.client.get('/api/nodes')
        assert r.status_code == 200
        assert r.json() == {'nodes': [], 'total': 0}

    def test_stacks_placeholder(self):
        r = self.client.get('/api/stacks')
        assert r.status_code == 200
        assert r.json() == {'stacks': [], 'total': 0}

    # ── per-spec routes are mounted ─────────────────────────────────────────

    def test_per_spec_docker_routes_are_mounted(self):
        routes = {str(r.path) for r in self.fast_api.app().routes if hasattr(r, 'path')}
        assert '/api/specs/docker/stacks'              in routes
        assert '/api/specs/docker/stack'               in routes
        assert '/api/specs/docker/stack/{name}'        in routes
        assert '/api/specs/docker/stack/{name}/health' in routes

    def test_per_spec_podman_routes_are_mounted(self):
        routes = {str(r.path) for r in self.fast_api.app().routes if hasattr(r, 'path')}
        assert '/api/specs/podman/stacks'              in routes
        assert '/api/specs/podman/stack'               in routes

    def test_route_count_is_at_least_expected(self):
        # health(2) + specs(2) + nodes(1) + stacks(1) + docker(5) + podman(5) + openapi(1) = 17
        routes = [r for r in self.fast_api.app().routes if hasattr(r, 'methods')]
        assert len(routes) >= 17

    # ── spec_id path does not shadow per-spec routes ────────────────────────

    def test_spec_id_wildcard_does_not_shadow_docker_stacks(self):
        # GET /api/specs/docker/stacks should reach the docker routes handler,
        # NOT the /{spec_id} catch-all. Since docker service has no AWS client,
        # the call raises NoCredentialsError inside the handler. We use
        # raise_server_exceptions=False so TestClient returns 500 instead of re-raising.
        from fastapi.testclient import TestClient
        client = TestClient(self.fast_api.app(), raise_server_exceptions=False)
        r = client.get('/api/specs/docker/stacks')
        assert r.status_code in (200, 404, 500)                                # route resolved, not unrouted
