# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Playwright__Stack
# Action-mapped HTTP surface for the sp playwright section. Mirrors
# Routes__Vnc__Stack. Routes carry zero logic — they delegate to
# Playwright__Stack__Service and serialise the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /playwright/stack                  -> Schema__Playwright__Stack__Create__Response
#   GET    /playwright/stacks                 -> Schema__Playwright__Stack__List
#   GET    /playwright/stack/{name}           -> Schema__Playwright__Stack__Info  (404 on miss)
#   DELETE /playwright/stack/{name}           -> Schema__Playwright__Stack__Delete__Response (404 on miss)
#   GET    /playwright/stack/{name}/health    -> Schema__Playwright__Health
#
# `name` is the logical stack name (== host-plane pod name). host_url +
# host_api_key locate the target host control plane; both fall back to env
# vars inside the service when blank.
#
# The `create` handler takes `body: dict` and round-trips via
# `Schema__Playwright__Stack__Create__Request.from_json(body)` — same
# workaround Routes__Vnc__Stack uses for Swagger-friendly bodies.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Request import Schema__Playwright__Stack__Create__Request
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Service import Playwright__Stack__Service


TAG__ROUTES_PLAYWRIGHT = 'playwright'                                               # URL prefix; OpenAPI groups all five endpoints together


class Routes__Playwright__Stack(Fast_API__Routes):
    tag     : str                       = TAG__ROUTES_PLAYWRIGHT
    service : Playwright__Stack__Service                                            # Injected by Fast_API__SP__CLI.setup_routes()

    def list_stacks(self, host_url: str = '', host_api_key: str = '') -> dict:       # GET /playwright/stacks
        return self.service.list_stacks(host_url, host_api_key).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, host_url: str = '', host_api_key: str = '') -> dict:   # GET /playwright/stack/{name}
        result = self.service.get_stack_info(host_url, host_api_key, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no playwright stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /playwright/stack
        request = Schema__Playwright__Stack__Create__Request.from_json(body)
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, host_url: str = '', host_api_key: str = '') -> dict: # DELETE /playwright/stack/{name}
        response = self.service.delete_stack(host_url, host_api_key, name)
        if not response.removed:
            raise HTTPException(status_code=404, detail=f'no playwright stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, host_url: str = '', host_api_key: str = '') -> dict: # GET /playwright/stack/{name}/health
        return self.service.health(host_url, host_api_key, name).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
