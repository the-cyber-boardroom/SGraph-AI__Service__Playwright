# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Linux__Stack
# HTTP surface for the sp linux section. Zero logic — delegates to
# Linux__Service and serialises the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /linux/stack                   -> Schema__Linux__Create__Response
#   GET    /linux/stacks                  -> Schema__Linux__List
#   GET    /linux/stack/{name}            -> Schema__Linux__Info  (404 on miss)
#   DELETE /linux/stack/{name}            -> Schema__Linux__Delete__Response (404 on miss)
#   GET    /linux/stack/{name}/health     -> Schema__Linux__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Request import Schema__Linux__Create__Request
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import DEFAULT_REGION, Linux__Service


TAG__ROUTES_LINUX = 'linux'


class Routes__Linux__Stack(Fast_API__Routes):
    tag     : str            = TAG__ROUTES_LINUX
    service : Linux__Service                                                        # Injected by caller

    def list_stacks(self, region: str = '') -> dict:                                # GET /linux/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /linux/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no linux stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Linux__Create__Request) -> dict:                 # POST /linux/stack
        return self.service.create_stack(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /linux/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted:
            raise HTTPException(status_code=404, detail=f'no linux stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '') -> dict:                          # GET /linux/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, timeout_sec=0).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
