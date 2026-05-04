# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Stacks
# Cross-spec stack listing for the compute control plane.
# Placeholder — full implementation follows per-spec service aggregation.
#
# Endpoints
# ─────────
#   GET /api/stacks → {"stacks": [], "total": 0}
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes


TAG__ROUTES_COMPUTE_STACKS = 'stacks'


class Routes__Compute__Stacks(Fast_API__Routes):
    tag    : str = TAG__ROUTES_COMPUTE_STACKS
    prefix : str = '/api/stacks'

    def list_stacks(self) -> dict:                                            # GET /api/stacks
        return {'stacks': [], 'total': 0}
    list_stacks.__route_path__ = ''

    def setup_routes(self):
        self.add_route_get(self.list_stacks)
