# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Nodes
# Tests use in-memory FastAPI stack; EC2 calls do not fire.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase
from unittest.mock                                                            import patch, MagicMock

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Nodes                  import Routes__Compute__Nodes
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


def _make_client(platform_mock):
    fast_api = Fast_API()
    fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
    return TestClient(fast_api.app())


class test_Routes__Compute__Nodes(TestCase):

    def setUp(self):
        self.node = Schema__Node__Info(node_id       = 'test-node'    ,
                                       spec_id       = 'docker'       ,
                                       region        = 'eu-west-2'    ,
                                       state         = Enum__Node__State.READY,
                                       instance_id   = 'i-0123456789' ,
                                       instance_type = 't3.medium'    )

    def test_list_nodes__empty(self):
        empty_listing = Schema__Node__List(nodes=[])
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.list_nodes.return_value = empty_listing
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.get('/api/nodes')
        assert r.status_code == 200
        data = r.json()
        assert data['nodes'] == []
        assert data['total'] == 0

    def test_list_nodes__returns_nodes(self):
        listing = Schema__Node__List(nodes=[self.node])
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.list_nodes.return_value = listing
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.get('/api/nodes')
        assert r.status_code == 200
        data = r.json()
        assert data['total'] == 1
        assert len(data['nodes']) == 1

    def test_get_node__not_found(self):
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.get_node.return_value = None
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.get('/api/nodes/missing-node')
        assert r.status_code == 404

    def test_get_node__found(self):
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.get_node.return_value = self.node
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.get('/api/nodes/test-node')
        assert r.status_code == 200

    def test_delete_node__not_found(self):
        resp = Schema__Node__Delete__Response(node_id='x', deleted=False, message='node not found')
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.delete_node.return_value = resp
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.delete('/api/nodes/x')
        assert r.status_code == 404

    def test_delete_node__success(self):
        resp = Schema__Node__Delete__Response(node_id='test-node', deleted=True, message='terminated')
        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.delete_node.return_value = resp
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app())
            r = client.delete('/api/nodes/test-node')
        assert r.status_code == 200
        data = r.json()
        assert data['deleted']  is True
        assert data['node_id'] == 'test-node'

    def test_list_nodes__credential_error_returns_503(self):
        class FakeNoCredentials(Exception):
            pass
        FakeNoCredentials.__name__ = 'NoCredentialsError'

        with patch('sg_compute.control_plane.routes.Routes__Compute__Nodes._platform') as mock_plat:
            mock_plat.return_value.list_nodes.side_effect = FakeNoCredentials('no creds')
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes')
            client = TestClient(fast_api.app(), raise_server_exceptions=False)
            r = client.get('/api/nodes')
        assert r.status_code == 503
