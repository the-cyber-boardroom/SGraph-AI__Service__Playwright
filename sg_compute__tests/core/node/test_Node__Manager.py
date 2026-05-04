# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Node__Manager
# Uses a fake Platform implementation — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.core.node.Node__Manager                                      import Node__Manager
from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base        import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


class Fake__Platform(Platform):
    """Fake platform that records calls and returns predictable values."""
    name            : str  = 'fake'
    created_nodes   : list
    deleted_node_ids: list

    def __init__(self):
        self.created_nodes    = []
        self.deleted_node_ids = []

    def setup(self) -> 'Fake__Platform':
        return self

    def create_node(self, request, spec) -> Schema__Node__Info:
        node = Schema__Node__Info(
            node_id  = request.node_name or f'{spec.spec_id}-test-node-0001',
            spec_id  = spec.spec_id                                          ,
            state    = Enum__Node__State.READY                               ,
        )
        self.created_nodes.append(node)
        return node

    def list_nodes(self, region: str = '') -> Schema__Node__List:
        return Schema__Node__List(nodes=list(self.created_nodes))

    def get_node(self, node_id: str, region: str = '') -> 'Schema__Node__Info | None':
        for node in self.created_nodes:
            if node.node_id == node_id:
                return node
        return None

    def delete_node(self, node_id: str, region: str = '') -> Schema__Node__Delete__Response:
        self.deleted_node_ids.append(node_id)
        return Schema__Node__Delete__Response(node_id=node_id, deleted=True, message='terminated')


class test_Node__Manager(TestCase):

    def setUp(self):
        self.platform = Fake__Platform()
        self.manager  = Node__Manager()
        self.manager.setup(self.platform)

    def _spec(self, spec_id='firefox') -> Schema__Spec__Manifest__Entry:
        return Schema__Spec__Manifest__Entry(spec_id=spec_id)

    def test_create_node(self):
        request = Schema__Node__Create__Request__Base(spec_id='firefox', node_name='ff-test-0001')
        node    = self.manager.create_node(request, self._spec('firefox'))
        assert node.spec_id == 'firefox'
        assert len(self.platform.created_nodes) == 1

    def test_list_nodes(self):
        node_list = self.manager.list_nodes()
        assert isinstance(node_list, Schema__Node__List)

    def test_get_node_found(self):
        request = Schema__Node__Create__Request__Base(spec_id='firefox', node_name='ff-quiet-0001')
        self.manager.create_node(request, self._spec('firefox'))
        result = self.manager.get_node('ff-quiet-0001')
        assert result is not None
        assert result.node_id == 'ff-quiet-0001'

    def test_get_node_not_found(self):
        result = self.manager.get_node('nonexistent-node')
        assert result is None

    def test_delete_node(self):
        request = Schema__Node__Create__Request__Base(spec_id='firefox', node_name='ff-del-0001')
        self.manager.create_node(request, self._spec('firefox'))
        response = self.manager.delete_node('ff-del-0001')
        assert response.deleted          is True
        assert 'ff-del-0001'             in self.platform.deleted_node_ids
