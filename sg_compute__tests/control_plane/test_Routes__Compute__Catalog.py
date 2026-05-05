# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Catalog (caller-ip endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Catalog                import Routes__Compute__Catalog


class test_Routes__Compute__Catalog(TestCase):

    def setUp(self):
        fast_api    = Fast_API()
        fast_api.add_routes(Routes__Compute__Catalog, prefix='/catalog')
        self.client = TestClient(fast_api.app())

    def test_caller_ip_no_xff_returns_empty(self):
        r = self.client.get('/catalog/caller-ip')
        assert r.status_code == 200
        data = r.json()
        assert 'ip' in data
        assert data['ip'] == ''

    def test_caller_ip_single_xff(self):
        r = self.client.get('/catalog/caller-ip',
                            headers={'X-Forwarded-For': '203.0.113.42'})
        assert r.status_code == 200
        assert r.json()['ip'] == '203.0.113.42'

    def test_caller_ip_multi_xff_returns_first(self):
        r = self.client.get('/catalog/caller-ip',
                            headers={'X-Forwarded-For': '203.0.113.42, 10.0.0.1, 172.16.0.5'})
        assert r.status_code == 200
        assert r.json()['ip'] == '203.0.113.42'

    def test_caller_ip_response_shape(self):
        r = self.client.get('/catalog/caller-ip')
        assert r.status_code == 200
        data = r.json()
        assert list(data.keys()) == ['ip']
