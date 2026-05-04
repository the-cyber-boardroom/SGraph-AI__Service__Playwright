# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Nodes
# In-memory composition via fake Platform; zero mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.Fast_API__Compute                              import Fast_API__Compute
from sg_compute.control_plane.routes.Routes__Compute__Nodes                  import Routes__Compute__Nodes
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.platforms.exceptions.Exception__AWS__No_Credentials          import Exception__AWS__No_Credentials
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


# ── fake platform helpers ────────────────────────────────────────────────────

class Fake__Platform__Empty(Platform):
    def list_nodes(self, region='eu-west-2'):
        return Schema__Node__List(nodes=[], total=0, region=region)

    def get_node(self, node_id, region='eu-west-2'):
        return None

    def delete_node(self, node_id, region='eu-west-2'):
        return Schema__Node__Delete__Response(node_id=node_id, deleted=False, message='node not found')


class Fake__Platform__With_Node(Platform):
    def __init__(self, node, **kwargs):
        super().__init__(**kwargs)
        self._node = node

    def list_nodes(self, region='eu-west-2'):
        return Schema__Node__List(nodes=[self._node], total=1, region=region)

    def get_node(self, node_id, region='eu-west-2'):
        return self._node if self._node.node_id == node_id else None

    def delete_node(self, node_id, region='eu-west-2'):
        return Schema__Node__Delete__Response(node_id=node_id, deleted=True, message='terminated')


class Fake__Platform__No_Creds(Platform):
    def list_nodes(self, region='eu-west-2'):
        raise Exception__AWS__No_Credentials('no creds configured')


def _client(platform):
    fast_api = Fast_API()
    fast_api.add_routes(Routes__Compute__Nodes, prefix='/api/nodes', platform=platform)
    return TestClient(fast_api.app())


def _client_with_handler(platform):
    api = Fast_API__Compute(platform=platform)
    api.setup()
    return TestClient(api.app(), raise_server_exceptions=False)


# ── tests ────────────────────────────────────────────────────────────────────

class test_Routes__Compute__Nodes(TestCase):

    def setUp(self):
        self.node = Schema__Node__Info(node_id       = 'test-node'    ,
                                       spec_id       = 'docker'       ,
                                       region        = 'eu-west-2'    ,
                                       state         = Enum__Node__State.READY,
                                       instance_id   = 'i-0123456789' ,
                                       instance_type = 't3.medium'    )

    def test_list_nodes__empty(self):
        client = _client(Fake__Platform__Empty())
        r      = client.get('/api/nodes')
        assert r.status_code == 200
        data = r.json()
        assert data['nodes'] == []
        assert data['total'] == 0

    def test_list_nodes__returns_nodes(self):
        client = _client(Fake__Platform__With_Node(self.node))
        r      = client.get('/api/nodes')
        assert r.status_code == 200
        data = r.json()
        assert data['total']     == 1
        assert len(data['nodes']) == 1

    def test_get_node__not_found(self):
        client = _client(Fake__Platform__Empty())
        r      = client.get('/api/nodes/missing-node')
        assert r.status_code == 404

    def test_get_node__found(self):
        client = _client(Fake__Platform__With_Node(self.node))
        r      = client.get('/api/nodes/test-node')
        assert r.status_code == 200
        assert r.json()['node_id'] == 'test-node'

    def test_delete_node__not_found(self):
        client = _client(Fake__Platform__Empty())
        r      = client.delete('/api/nodes/x')
        assert r.status_code == 404

    def test_delete_node__success(self):
        client = _client(Fake__Platform__With_Node(self.node))
        r      = client.delete('/api/nodes/test-node')
        assert r.status_code == 200
        data = r.json()
        assert data['deleted']  is True
        assert data['node_id'] == 'test-node'

    def test_list_nodes__credential_error_returns_503(self):
        client = _client_with_handler(Fake__Platform__No_Creds())
        r      = client.get('/api/nodes')
        assert r.status_code == 503
        assert 'AWS credentials' in r.json()['detail']
