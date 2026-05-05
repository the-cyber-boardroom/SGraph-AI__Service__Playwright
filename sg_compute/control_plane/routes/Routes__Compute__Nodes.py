# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Nodes
# Node management endpoints for the compute control plane.
#
# Endpoints
# ─────────
#   GET    /api/nodes               → list all managed EC2 nodes
#   POST   /api/nodes               → create (launch) a node for a given spec
#   GET    /api/nodes/{node_id}     → info for one node
#   DELETE /api/nodes/{node_id}     → terminate a node
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                   import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base         import Schema__Node__Create__Request__Base
from sg_compute.platforms.Platform                                             import Platform

DEFAULT_REGION = 'eu-west-2'

TAG__ROUTES_COMPUTE_NODES = 'nodes'


class Routes__Compute__Nodes(Fast_API__Routes):
    tag      : str      = TAG__ROUTES_COMPUTE_NODES
    prefix   : str      = '/api/nodes'
    platform : Platform

    def list_nodes(self, region: str = DEFAULT_REGION) -> dict:               # GET /api/nodes
        return self.platform.list_nodes(region).json()
    list_nodes.__route_path__ = ''

    def create_node(self, body: Schema__Node__Create__Request__Base) -> dict: # POST /api/nodes
        node = self.platform.create_node(body)
        return node.json()
    create_node.__route_path__ = ''

    def get_node(self, node_id: str, region: str = DEFAULT_REGION) -> dict:   # GET /api/nodes/{node_id}
        node = self.platform.get_node(node_id, region)
        if node is None:
            raise HTTPException(status_code=404, detail=f'Node {node_id!r} not found in {region}')
        return node.json()
    get_node.__route_path__ = '/{node_id}'

    def delete_node(self, node_id: str, region: str = DEFAULT_REGION) -> dict: # DELETE /api/nodes/{node_id}
        result = self.platform.delete_node(node_id, region)
        if not result.deleted:
            raise HTTPException(status_code=404, detail=result.message)
        return result.json()
    delete_node.__route_path__ = '/{node_id}'

    def setup_routes(self):
        self.add_route_get   (self.list_nodes  )
        self.add_route_post  (self.create_node )
        self.add_route_get   (self.get_node    )
        self.add_route_delete(self.delete_node )
