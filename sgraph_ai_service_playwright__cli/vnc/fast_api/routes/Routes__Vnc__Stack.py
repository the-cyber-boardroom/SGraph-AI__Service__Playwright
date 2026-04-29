# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Vnc__Stack
# Action-mapped HTTP surface for the sp vnc section. Mirrors
# Routes__Prometheus__Stack. Routes carry zero logic — they delegate to
# Vnc__Service and serialise the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /vnc/stack                        -> Schema__Vnc__Stack__Create__Response
#   GET    /vnc/stacks                       -> Schema__Vnc__Stack__List
#   GET    /vnc/stack/{name}                 -> Schema__Vnc__Stack__Info  (404 on miss)
#   DELETE /vnc/stack/{name}                 -> Schema__Vnc__Stack__Delete__Response (404 on miss)
#   GET    /vnc/stack/{name}/health          -> Schema__Vnc__Health
#
# `name` is the logical stack name (sg:stack-name tag). Region defaults to
# DEFAULT_REGION inside the service.
#
# The `create` handler takes `body: dict` and round-trips via
# `Schema__Vnc__Stack__Create__Request.from_json(body)` because the request
# carries a nested Schema__Vnc__Interceptor__Choice — same workaround used
# in Routes__Prometheus__Stack.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import DEFAULT_REGION, Vnc__Service


TAG__ROUTES_VNC = 'vnc'                                                             # URL prefix; OpenAPI groups all five endpoints together


class Routes__Vnc__Stack(Fast_API__Routes):
    tag     : str           = TAG__ROUTES_VNC
    service : Vnc__Service                                                          # Injected by Fast_API__SP__CLI.setup_routes()

    def list_stacks(self, region: str = '') -> dict:                                # GET /vnc/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /vnc/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no vnc stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /vnc/stack
        request = Schema__Vnc__Stack__Create__Request.from_json(body)               # body: dict avoids pydantic schema-generation for nested Interceptor__Choice
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /vnc/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.terminated_instance_ids:
            raise HTTPException(status_code=404, detail=f'no vnc stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '', username: str = '', password: str = '') -> dict:  # GET /vnc/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, username, password).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
