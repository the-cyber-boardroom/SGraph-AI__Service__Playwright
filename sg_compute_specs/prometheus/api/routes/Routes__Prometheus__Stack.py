# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Routes__Prometheus__Stack
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sg_compute_specs.prometheus.schemas.Schema__Prom__Stack__Create__Request       import Schema__Prom__Stack__Create__Request
from sg_compute_specs.prometheus.service.Prometheus__Service                        import DEFAULT_REGION, Prometheus__Service


TAG__ROUTES_PROMETHEUS = 'prometheus'


class Routes__Prometheus__Stack(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_PROMETHEUS
    service : Prometheus__Service

    def list_stacks(self, region: str = '') -> dict:                                # GET /api/specs/prometheus/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /api/specs/prometheus/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no prometheus stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /api/specs/prometheus/stack
        request = Schema__Prom__Stack__Create__Request.from_json(body)              # body: dict avoids pydantic schema generation for nested List__Schema__Prom__Scrape__Target
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /api/specs/prometheus/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.terminated_instance_ids:
            raise HTTPException(status_code=404, detail=f'no prometheus stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '', username: str = '', password: str = '') -> dict:  # GET /api/specs/prometheus/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, username, password).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
