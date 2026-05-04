# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Platform
# Abstract base for compute backends (EC2 today; K8s, GCP, local: future).
# Each Platform implements: create_node, list_nodes, get_node, delete_node.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base        import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class Platform(Type_Safe):
    name : str = ''                                                            # 'ec2' | 'k8s' | 'gcp' | 'local'

    def setup(self) -> 'Platform':
        return self

    def create_node(self,
                    request : Schema__Node__Create__Request__Base,
                    spec    : Schema__Spec__Manifest__Entry) -> Schema__Node__Info:
        raise NotImplementedError(f'{self.__class__.__name__}.create_node')

    def list_nodes(self, region: str = '') -> Schema__Node__List:
        raise NotImplementedError(f'{self.__class__.__name__}.list_nodes')

    def get_node(self, node_id: str) -> 'Schema__Node__Info | None':
        raise NotImplementedError(f'{self.__class__.__name__}.get_node')

    def delete_node(self, node_id: str) -> Schema__Node__Delete__Response:
        raise NotImplementedError(f'{self.__class__.__name__}.delete_node')
