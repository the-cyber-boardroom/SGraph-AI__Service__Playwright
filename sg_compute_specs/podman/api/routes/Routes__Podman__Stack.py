# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Routes__Podman__Stack
# HTTP surface for the podman compute spec. Zero logic — delegates to
# Podman__Service.
#
# Endpoints
# ─────────
#   POST   /api/specs/podman/stack                -> Schema__Podman__Create__Response
#   GET    /api/specs/podman/stacks               -> Schema__Podman__List
#   GET    /api/specs/podman/stack/{name}         -> Schema__Podman__Info
#   DELETE /api/specs/podman/stack/{name}         -> Schema__Podman__Delete__Response
#   GET    /api/specs/podman/stack/{name}/health  -> Schema__Podman__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sg_compute_specs.podman.schemas.Schema__Podman__Create__Request                import Schema__Podman__Create__Request
from sg_compute_specs.podman.service.Podman__Service                                import DEFAULT_REGION, Podman__Service


TAG__ROUTES_PODMAN = 'podman'


class Routes__Podman__Stack(Fast_API__Routes):
    tag     : str            = TAG__ROUTES_PODMAN
    service : Podman__Service

    def list_stacks(self, region: str = '') -> dict:                                # GET /api/specs/podman/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /api/specs/podman/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no podman stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Podman__Create__Request) -> dict:                # POST /api/specs/podman/stack
        return self.service.create_stack(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /api/specs/podman/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted:
            raise HTTPException(status_code=404, detail=f'no podman stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '') -> dict:                          # GET /api/specs/podman/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, timeout_sec=0).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
