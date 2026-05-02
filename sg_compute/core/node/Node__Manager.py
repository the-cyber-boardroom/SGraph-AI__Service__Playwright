# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Node__Manager
# Orchestrates node lifecycle by delegating to the active Platform.
# The control plane FastAPI calls this; spec services may also use it.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import Optional

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base        import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.platforms.Platform                                            import Platform


class Node__Manager(Type_Safe):
    platform : Platform

    def setup(self, platform: Platform) -> 'Node__Manager':
        self.platform = platform
        self.platform.setup()
        return self

    def create_node(self,
                    request : Schema__Node__Create__Request__Base,
                    spec    : Schema__Spec__Manifest__Entry) -> Schema__Node__Info:
        return self.platform.create_node(request, spec)

    def list_nodes(self, region: str = '') -> Schema__Node__List:
        return self.platform.list_nodes(region)

    def get_node(self, node_id: str, region: str = '') -> Optional[Schema__Node__Info]:
        return self.platform.get_node(node_id, region)

    def delete_node(self, node_id: str, region: str = '') -> Schema__Node__Delete__Response:
        return self.platform.delete_node(node_id, region)
