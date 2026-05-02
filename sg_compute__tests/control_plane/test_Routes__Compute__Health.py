# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Health
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Health                 import Routes__Compute__Health
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry


class test_Routes__Compute__Health(TestCase):

    def setUp(self):
        self.registry = Spec__Loader().load_all()
        fast_api      = Fast_API()
        fast_api.add_routes(Routes__Compute__Health, prefix='/api/health', registry=self.registry)
        self.client   = TestClient(fast_api.app())

    def test_ping_returns_ok(self):
        r = self.client.get('/api/health')
        assert r.status_code == 200
        assert r.json() == {'status': 'ok'}

    def test_ready_returns_ok_and_spec_count(self):
        r = self.client.get('/api/health/ready')
        assert r.status_code == 200
        data = r.json()
        assert data['status']       == 'ok'
        assert data['specs_loaded'] == len(self.registry)
        assert data['specs_loaded'] >= 4

    def test_ready_with_empty_registry(self):
        empty    = Spec__Registry()
        fast_api = Fast_API()
        fast_api.add_routes(Routes__Compute__Health, prefix='/api/health', registry=empty)
        client = TestClient(fast_api.app())
        r = client.get('/api/health/ready')
        assert r.status_code == 200
        assert r.json()['specs_loaded'] == 0

    def test_unknown_path_returns_404(self):
        r = self.client.get('/api/health/unknown')
        assert r.status_code == 404
