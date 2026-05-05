# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Pods + Pod__Manager
# In-memory composition: fake Platform + fake Sidecar__Client subclasses.
# Zero mock.patch calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Pods                   import Routes__Compute__Pods
from sg_compute.core.pod.Pod__Manager                                        import Pod__Manager
from sg_compute.core.pod.Sidecar__Client                                     import Sidecar__Client
from sg_compute.core.pod.schemas.Schema__Pod__Info                           import Schema__Pod__Info
from sg_compute.core.pod.schemas.Schema__Pod__List                           import Schema__Pod__List
from sg_compute.core.pod.schemas.Schema__Pod__Logs__Response                 import Schema__Pod__Logs__Response
from sg_compute.core.pod.schemas.Schema__Pod__Start__Request                 import Schema__Pod__Start__Request
from sg_compute.core.pod.schemas.Schema__Pod__Stop__Response                 import Schema__Pod__Stop__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State
from sg_compute.primitives.enums.Enum__Pod__State                            import Enum__Pod__State


# ── fake sidecar client ──────────────────────────────────────────────────────

class Fake__Sidecar__Client(Sidecar__Client):
    """Returns canned data; makes no real HTTP calls."""

    def list_pods(self) -> list:
        return [{'name': 'web', 'image': 'nginx:latest', 'status': 'running',
                 'state': 'Up 5 minutes', 'ports': {}, 'created_at': '', 'type_id': 'docker'}]

    def get_pod(self, name: str) -> dict | None:
        if name == 'web':
            return {'name': 'web', 'image': 'nginx:latest', 'status': 'running',
                    'state': 'Up 5 minutes', 'ports': {}, 'created_at': '', 'type_id': 'docker'}
        return None

    def get_pod_logs(self, name: str, tail: int = 100, timestamps: bool = False) -> dict | None:
        if name == 'web':
            return {'container': 'web', 'lines': 3, 'content': 'log line 1\nlog line 2\nlog line 3',
                    'truncated': False}
        return None

    def get_pod_stats(self, name: str) -> dict | None:
        return None

    def start_pod(self, body: dict) -> dict:
        return {'name': body.get('name', 'new-pod'), 'image': body.get('image', ''),
                'status': 'created', 'state': 'created', 'ports': {}, 'created_at': '', 'type_id': ''}

    def stop_pod(self, name: str) -> dict:
        return {'name': name, 'stopped': True, 'removed': False, 'error': ''}

    def remove_pod(self, name: str) -> dict:
        return {'name': name, 'stopped': True, 'removed': True, 'error': ''}


# ── fake platform (returns a node with a public IP) ──────────────────────────

class Fake__Platform__With_IP(Platform):
    def get_node(self, node_id, region='eu-west-2'):
        return Schema__Node__Info(node_id='test-node', spec_id='docker',
                                  region='eu-west-2', state=Enum__Node__State.READY,
                                  public_ip='10.0.0.1', instance_id='i-abc')

    def get_node_missing(self, node_id, region='eu-west-2'):
        return None


class Fake__Platform__No_Node(Platform):
    def get_node(self, node_id, region='eu-west-2'):
        return None


# ── fake pod manager (wires the fake sidecar client) ────────────────────────

class Fake__Pod__Manager(Pod__Manager):
    def _sidecar_client(self, node_id: str) -> Sidecar__Client | None:
        node = self.platform.get_node(node_id)
        if node is None or not node.public_ip:
            return None
        return Fake__Sidecar__Client(host_api_url=f'http://{node.public_ip}:19009', api_key='test-key')


def _client(manager: Pod__Manager) -> TestClient:
    fast_api = Fast_API()
    fast_api.add_routes(Routes__Compute__Pods, prefix='/api/nodes', manager=manager)
    return TestClient(fast_api.app())


def _manager_with_ip() -> Fake__Pod__Manager:
    return Fake__Pod__Manager(platform=Fake__Platform__With_IP())


def _manager_no_node() -> Fake__Pod__Manager:
    return Fake__Pod__Manager(platform=Fake__Platform__No_Node())


# ── route tests ──────────────────────────────────────────────────────────────

class test_Routes__Compute__Pods(TestCase):

    def test_list_pods__empty_when_no_node(self):
        client = _client(_manager_no_node())
        r      = client.get('/api/nodes/ghost/pods/list')
        assert r.status_code == 200
        data = r.json()
        assert data['pods'] == []

    def test_list_pods__returns_pods(self):
        client = _client(_manager_with_ip())
        r      = client.get('/api/nodes/test-node/pods/list')
        assert r.status_code == 200
        data = r.json()
        assert len(data['pods']) == 1
        assert data['pods'][0]['pod_name'] == 'web'
        assert data['pods'][0]['state']    == Enum__Pod__State.RUNNING.value

    def test_get_pod__found(self):
        client = _client(_manager_with_ip())
        r      = client.get('/api/nodes/test-node/pods/web')
        assert r.status_code == 200
        assert r.json()['pod_name'] == 'web'

    def test_get_pod__not_found(self):
        client = _client(_manager_with_ip())
        r      = client.get('/api/nodes/test-node/pods/missing')
        assert r.status_code == 404

    def test_get_pod_logs(self):
        client = _client(_manager_with_ip())
        r      = client.get('/api/nodes/test-node/pods/web/logs?tail=10')
        assert r.status_code == 200
        data = r.json()
        assert data['container'] == 'web'
        assert data['lines']     == 3
        assert 'log line 1'      in data['content']

    def test_stop_pod(self):
        client = _client(_manager_with_ip())
        r      = client.post('/api/nodes/test-node/pods/web/stop')
        assert r.status_code == 200
        data = r.json()
        assert data['stopped'] is True
        assert data['name']    == 'web'

    def test_remove_pod(self):
        client = _client(_manager_with_ip())
        r      = client.delete('/api/nodes/test-node/pods/web')
        assert r.status_code == 200
        data = r.json()
        assert data['removed'] is True

    def test_start_pod(self):
        client = _client(_manager_with_ip())
        payload = {'name': 'new-pod', 'image': 'alpine:latest', 'ports': {}, 'env': {}, 'type_id': ''}
        r       = client.post('/api/nodes/test-node/pods', json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data['pod_name'] == 'new-pod'


# ── pod manager unit tests ────────────────────────────────────────────────────

class test_Pod__Manager(TestCase):

    def setUp(self):
        self.manager = Fake__Pod__Manager(platform=Fake__Platform__With_IP())

    def test_list_pods(self):
        result = self.manager.list_pods('test-node')
        assert isinstance(result, Schema__Pod__List)
        assert len(result.pods) == 1
        assert result.pods[0].pod_name == 'web'
        assert result.pods[0].node_id  == 'test-node'
        assert result.pods[0].state    == Enum__Pod__State.RUNNING

    def test_get_pod__found(self):
        result = self.manager.get_pod('test-node', 'web')
        assert isinstance(result, Schema__Pod__Info)
        assert result.pod_name == 'web'

    def test_get_pod__not_found(self):
        result = self.manager.get_pod('test-node', 'ghost')
        assert result is None

    def test_get_pod_logs(self):
        result = self.manager.get_pod_logs('test-node', 'web', tail=10)
        assert isinstance(result, Schema__Pod__Logs__Response)
        assert result.container == 'web'
        assert result.lines     == 3

    def test_stop_pod(self):
        result = self.manager.stop_pod('test-node', 'web')
        assert isinstance(result, Schema__Pod__Stop__Response)
        assert result.stopped is True

    def test_remove_pod(self):
        result = self.manager.remove_pod('test-node', 'web')
        assert isinstance(result, Schema__Pod__Stop__Response)
        assert result.removed is True

    def test_list_pods__no_node_returns_empty(self):
        mgr    = Fake__Pod__Manager(platform=Fake__Platform__No_Node())
        result = mgr.list_pods('ghost')
        assert result.pods == []
