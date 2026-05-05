# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Catalog
# Utility endpoints on the compute control plane.
#
# Endpoints
# ─────────
#   GET /catalog/caller-ip  → Schema__Caller__IP  (auth-free; detects caller IP)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                   import Request

from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.catalog.schemas.Schema__Caller__IP                            import Schema__Caller__IP
from sg_compute.primitives.Safe_Str__IP__Address                              import Safe_Str__IP__Address


TAG__ROUTES_COMPUTE_CATALOG = 'catalog'


class Routes__Compute__Catalog(Fast_API__Routes):
    tag    : str = TAG__ROUTES_COMPUTE_CATALOG
    prefix : str = '/catalog'

    def setup_routes(self):
        router = self.router

        @router.get('/caller-ip')
        def caller_ip(request: Request) -> dict:
            xff = request.headers.get('x-forwarded-for', '')
            ip  = xff.split(',')[0].strip() if xff else ''
            return Schema__Caller__IP(ip=Safe_Str__IP__Address(ip)).json()
