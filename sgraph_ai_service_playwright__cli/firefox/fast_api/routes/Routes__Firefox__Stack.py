# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Firefox__Stack
# HTTP surface for the Firefox plugin. Routes carry zero logic —
# pure delegation to Firefox__Service.
#
# Endpoints:
#   POST   /firefox/stack                → Schema__Firefox__Stack__Create__Response
#   GET    /firefox/stacks               → Schema__Firefox__Stack__List
#   GET    /firefox/stack/{name}         → Schema__Firefox__Stack__Info   (404 on miss)
#   DELETE /firefox/stack/{name}         → Schema__Firefox__Stack__Delete__Response
#   GET    /firefox/stack/{name}/health  → Schema__Firefox__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service             import DEFAULT_REGION, Firefox__Service


TAG__ROUTES_FIREFOX = 'firefox'


class Routes__Firefox__Stack(Fast_API__Routes):
    tag     : str             = TAG__ROUTES_FIREFOX
    service : Firefox__Service

    def list_stacks(self, region: str = '') -> dict:                                # GET /firefox/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /firefox/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no firefox stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /firefox/stack
        request = Schema__Firefox__Stack__Create__Request.from_json(body)
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /firefox/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted and not response.target:
            raise HTTPException(status_code=404, detail=f'no firefox stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '') -> dict:                          # GET /firefox/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, timeout_sec=0).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
