# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Elastic__Stack
# Lifecycle HTTP routes for the Elastic service. Mirrors Routes__Linux__Stack.
# Only lifecycle operations — seed/wipe/kibana/AMI ops stay CLI-only.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                                    import Fast_API__Routes

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service


DEFAULT_REGION     = 'eu-west-2'
TAG__ROUTES_ELASTIC = 'elastic'


class Routes__Elastic__Stack(Fast_API__Routes):
    tag     : str              = TAG__ROUTES_ELASTIC
    service : Elastic__Service                                                      # Injected by caller

    def list_stacks(self, region: str = '') -> dict:                                # GET /elastic/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /elastic/stack/{name}
        result = self.service.get_stack_info(name, region or DEFAULT_REGION)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Elastic__Create__Request) -> dict:               # POST /elastic/stack
        return self.service.create(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /elastic/stack/{name}
        response = self.service.delete_stack(name, region or DEFAULT_REGION)
        if not response.target:                                                     # target is empty when no stack was found
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str) -> dict:                                            # GET /elastic/stack/{name}/health
        return self.service.health(stack_name=name).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
