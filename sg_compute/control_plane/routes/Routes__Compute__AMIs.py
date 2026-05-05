# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__AMIs
# AMI catalogue endpoints.
#
# Endpoints
# ─────────
#   GET /api/amis?spec_id=<id> → Schema__AMI__List__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes import Fast_API__Routes

from sg_compute.core.ami.service.AMI__Lister   import AMI__Lister

TAG__ROUTES_COMPUTE_AMIS = 'amis'


class Routes__Compute__AMIs(Fast_API__Routes):
    tag    : str         = TAG__ROUTES_COMPUTE_AMIS
    prefix : str         = '/api/amis'
    lister : AMI__Lister

    def list_amis(self, spec_id: str = '') -> dict:                            # GET /api/amis?spec_id=<id>
        return self.lister.list_amis(spec_id).json()
    list_amis.__route_path__ = ''

    def setup_routes(self):
        self.add_route_get(self.list_amis)
