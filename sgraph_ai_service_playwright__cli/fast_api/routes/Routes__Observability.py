# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Observability
# Exposes the read-only + delete surface of Observability__Service as HTTP
# routes. Matches the brief v0.1.72 naming, adjusted for the single-service
# Lambda (we are not mounted behind /v1 here — apply that prefix at API-GW
# if needed).
#
#   GET    /observability/stacks              -> Schema__Stack__List
#   GET    /observability/stacks/{name}       -> Schema__Stack__Info        (404 on miss)
#   DELETE /observability/stacks/{name}       -> Schema__Stack__Delete__Response
#
# Routes carry zero logic — pure delegation to Observability__Service, same
# pattern as Routes__Ec2.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.observability.service.Observability__Service import Observability__Service


TAG__ROUTES_OBSERVABILITY = 'observability'


class Routes__Observability(Fast_API__Routes):
    tag     : str                  = TAG__ROUTES_OBSERVABILITY
    service : Observability__Service                                                # Injected by Fast_API__SP__CLI.setup_routes()

    def stacks(self) -> dict:                                                       # GET /observability/stacks
        return self.service.list_stacks().json()

    def get_stack(self, name: str) -> dict:                                         # GET /observability/stacks/{name}
        info = self.service.get_stack_info(name=name)
        if info is None or (info.amp is None and info.opensearch is None and info.grafana is None):
            raise HTTPException(status_code=404, detail=f'no stack matched {name!r}')
        return info.json()
    get_stack.__route_path__ = '/stacks/{name}'                                     # Override the parser — canonical REST path, disambiguate GET vs DELETE

    def delete_stack(self, name: str) -> dict:                                      # DELETE /observability/stacks/{name}
        response = self.service.delete_stack(name=name)
        return response.json()                                                      # NOT_FOUND results are part of the response body, not a 404 — deleting a partially-missing stack is a valid outcome
    delete_stack.__route_path__ = '/stacks/{name}'

    def setup_routes(self):
        self.add_route_get   (self.stacks       )
        self.add_route_get   (self.get_stack    )
        self.add_route_delete(self.delete_stack )
