# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__OpenSearch__Stack
# Action-mapped HTTP surface for the sp os section. Mirrors
# Routes__Ec2__Playwright. Routes carry zero logic — they delegate to
# OpenSearch__Service and serialise the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /opensearch/stack                       -> Schema__OS__Stack__Create__Response
#   GET    /opensearch/stacks                      -> Schema__OS__Stack__List
#   GET    /opensearch/stack/{name}                -> Schema__OS__Stack__Info  (404 on miss)
#   DELETE /opensearch/stack/{name}                -> Schema__OS__Stack__Delete__Response (404 on miss)
#   GET    /opensearch/stack/{name}/health         -> Schema__OS__Health
#
# `name` is the logical stack name (sg:stack-name tag). Region defaults to
# the body's region or DEFAULT_REGION inside the service.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Service       import DEFAULT_REGION, OpenSearch__Service


TAG__ROUTES_OPENSEARCH = 'opensearch'                                               # URL prefix; OpenAPI groups all five endpoints together


class Routes__OpenSearch__Stack(Fast_API__Routes):
    tag     : str                  = TAG__ROUTES_OPENSEARCH
    service : OpenSearch__Service                                                   # Injected by Fast_API__SP__CLI.setup_routes()

    def list_stacks(self, region: str = '') -> dict:                                # GET /opensearch/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /opensearch/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no opensearch stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__OS__Stack__Create__Request) -> dict:             # POST /opensearch/stack
        return self.service.create_stack(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /opensearch/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.terminated_instance_ids:
            raise HTTPException(status_code=404, detail=f'no opensearch stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '', username: str = '', password: str = '') -> dict:  # GET /opensearch/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, username, password).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
