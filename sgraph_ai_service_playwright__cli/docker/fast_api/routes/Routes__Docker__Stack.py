# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Docker__Stack
# HTTP surface for the sp docker section. Zero logic — delegates to
# Docker__Service and serialises the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /docker/stack                  -> Schema__Docker__Create__Response
#   GET    /docker/stacks                 -> Schema__Docker__List
#   GET    /docker/stack/{name}           -> Schema__Docker__Info  (404 on miss)
#   DELETE /docker/stack/{name}           -> Schema__Docker__Delete__Response (404 on miss)
#   GET    /docker/stack/{name}/health    -> Schema__Docker__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service               import DEFAULT_REGION, Docker__Service


TAG__ROUTES_DOCKER = 'docker'


class Routes__Docker__Stack(Fast_API__Routes):
    tag     : str            = TAG__ROUTES_DOCKER
    service : Docker__Service                                                       # Injected by caller

    def list_stacks(self, region: str = '') -> dict:                                # GET /docker/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /docker/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no docker stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Docker__Create__Request) -> dict:                # POST /docker/stack
        return self.service.create_stack(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /docker/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted:
            raise HTTPException(status_code=404, detail=f'no docker stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '') -> dict:                          # GET /docker/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, timeout_sec=0).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
