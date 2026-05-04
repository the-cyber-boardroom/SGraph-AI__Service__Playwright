# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Nodes
# Node management endpoints for the compute control plane.
#
# Endpoints
# ─────────
#   GET /api/nodes               → list all managed EC2 nodes
#   GET /api/nodes/{node_id}     → info for one node
#   DELETE /api/nodes/{node_id}  → terminate a node
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                    import Optional

from fastapi                                                                   import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

DEFAULT_REGION = 'eu-west-2'

TAG__ROUTES_COMPUTE_NODES = 'nodes'


def _platform():
    from sg_compute.platforms.ec2.EC2__Platform import EC2__Platform
    return EC2__Platform().setup()


class Routes__Compute__Nodes(Fast_API__Routes):
    tag    : str = TAG__ROUTES_COMPUTE_NODES
    prefix : str = '/api/nodes'

    def list_nodes(self, region: str = DEFAULT_REGION) -> dict:              # GET /api/nodes
        try:
            listing = _platform().list_nodes(region)
            return {'nodes': [n.json() for n in listing.nodes], 'total': len(listing.nodes)}
        except Exception as e:
            if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
                raise HTTPException(status_code=503, detail=f'AWS credentials not configured: {e}')
            raise
    list_nodes.__route_path__ = ''

    def get_node(self, node_id: str, region: str = DEFAULT_REGION) -> dict:  # GET /api/nodes/{node_id}
        node = _platform().get_node(node_id, region)
        if node is None:
            raise HTTPException(status_code=404, detail=f'Node {node_id!r} not found in {region}')
        return node.json()
    get_node.__route_path__ = '/{node_id}'

    def delete_node(self, node_id: str, region: str = DEFAULT_REGION) -> dict:  # DELETE /api/nodes/{node_id}
        result = _platform().delete_node(node_id, region)
        if not result.deleted:
            raise HTTPException(status_code=404, detail=result.message)
        return {'node_id': node_id, 'deleted': True}
    delete_node.__route_path__ = '/{node_id}'

    def setup_routes(self):
        self.add_route_get   (self.list_nodes )
        self.add_route_get   (self.get_node   )
        self.add_route_delete(self.delete_node)
