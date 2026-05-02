# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Health
# Health endpoints for the compute control plane.
#
# Endpoints
# ─────────
#   GET /api/health        → {"status": "ok"}
#   GET /api/health/ready  → {"status": "ok", "specs_loaded": N}
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.core.spec.Spec__Registry                                      import Spec__Registry


TAG__ROUTES_COMPUTE_HEALTH = 'health'


class Routes__Compute__Health(Fast_API__Routes):
    tag      : str           = TAG__ROUTES_COMPUTE_HEALTH
    prefix   : str           = '/api/health'
    registry : Spec__Registry

    def ping(self) -> dict:                                                   # GET /api/health
        return {'status': 'ok'}
    ping.__route_path__ = ''

    def ready(self) -> dict:                                                  # GET /api/health/ready
        return {'status': 'ok', 'specs_loaded': len(self.registry)}
    ready.__route_path__ = '/ready'

    def setup_routes(self):
        self.add_route_get(self.ping )
        self.add_route_get(self.ready)
