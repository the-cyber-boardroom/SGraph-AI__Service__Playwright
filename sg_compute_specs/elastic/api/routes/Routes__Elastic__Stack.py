# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Routes__Elastic__Stack
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sg_compute_specs.elastic.schemas.Schema__Elastic__Create__Request              import Schema__Elastic__Create__Request
from sg_compute_specs.elastic.service.Elastic__Service                              import DEFAULT_REGION, Elastic__Service


TAG__ROUTES_ELASTIC = 'elastic'


class Routes__Elastic__Stack(Fast_API__Routes):
    tag     : str             = TAG__ROUTES_ELASTIC
    service : Elastic__Service

    def list_stacks(self, region: str = '') -> dict:                                # GET /api/specs/elastic/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /api/specs/elastic/stack/{name}
        result = self.service.get_stack_info(name, region or DEFAULT_REGION)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Elastic__Create__Request) -> dict:               # POST /api/specs/elastic/stack
        return self.service.create(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /api/specs/elastic/stack/{name}
        response = self.service.delete_stack(name, region or DEFAULT_REGION)
        if not response.target:
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '', password: str = '') -> dict:     # GET /api/specs/elastic/stack/{name}/health
        return self.service.health(name, region or DEFAULT_REGION, password).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
