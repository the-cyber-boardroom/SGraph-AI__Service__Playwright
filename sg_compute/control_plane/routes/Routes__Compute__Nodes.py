# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Nodes
# Node management endpoints for the compute control plane.
# Placeholder — full implementation follows Node__Manager wiring.
#
# Endpoints
# ─────────
#   GET /api/nodes → {"nodes": [], "total": 0}
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes


TAG__ROUTES_COMPUTE_NODES = 'nodes'


class Routes__Compute__Nodes(Fast_API__Routes):
    tag    : str = TAG__ROUTES_COMPUTE_NODES
    prefix : str = '/api/nodes'

    def list_nodes(self) -> dict:                                             # GET /api/nodes
        return {'nodes': [], 'total': 0}
    list_nodes.__route_path__ = ''

    def setup_routes(self):
        self.add_route_get(self.list_nodes)
