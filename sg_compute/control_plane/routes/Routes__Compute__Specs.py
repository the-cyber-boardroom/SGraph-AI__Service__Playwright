# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Specs
# Spec catalogue endpoints for the compute control plane.
#
# Endpoints
# ─────────
#   GET /api/specs                    → Schema__Spec__Catalogue  (full catalogue)
#   GET /api/specs/{spec_id}          → Schema__Spec__Manifest__Entry (single spec)
#   GET /api/specs/{spec_id}/readme   → text/markdown (spec README, 404 if absent)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                   import HTTPException
from fastapi.responses                                                         import Response

from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.core.spec.Spec__Readme__Resolver                              import Spec__Readme__Resolver
from sg_compute.core.spec.Spec__Registry                                      import Spec__Registry


TAG__ROUTES_COMPUTE_SPECS = 'specs'


class Routes__Compute__Specs(Fast_API__Routes):
    tag                  : str           = TAG__ROUTES_COMPUTE_SPECS
    prefix               : str           = '/api/specs'
    registry             : Spec__Registry
    readme_root_override : str           = ''

    def catalogue(self) -> dict:                                               # GET /api/specs
        return self.registry.catalogue().json()
    catalogue.__route_path__ = ''

    def spec_info(self, spec_id: str) -> dict:                                # GET /api/specs/{spec_id}
        entry = self.registry.get(spec_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f'spec {spec_id!r} not found')
        return entry.json()
    spec_info.__route_path__ = '/{spec_id}'

    def readme(self, spec_id: str) -> Response:                               # GET /api/specs/{spec_id}/readme
        if self.registry.get(spec_id) is None:
            raise HTTPException(status_code=404, detail=f'spec {spec_id!r} not found')
        resolver = Spec__Readme__Resolver(readme_root_override=self.readme_root_override)
        path     = resolver.readme_path_for_spec(spec_id)
        if path is None:
            raise HTTPException(status_code=404, detail=f'spec {spec_id!r} has no README')
        content  = path.read_text(encoding='utf-8')
        return Response(content=content, media_type='text/markdown; charset=utf-8')
    readme.__route_path__ = '/{spec_id}/readme'

    def setup_routes(self):
        self.add_route_get(self.catalogue)
        self.add_route_get(self.spec_info)
        self.add_route_get(self.readme)
