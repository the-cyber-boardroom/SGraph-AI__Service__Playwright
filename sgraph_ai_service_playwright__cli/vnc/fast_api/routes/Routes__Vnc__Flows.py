# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Vnc__Flows
# Per-stack mitmweb flow listing. Per N4 there is no auto-export — flows
# live on the EC2 and die with it; this is just a peek for human debug.
#
# Endpoint
# ────────
#   GET /vnc/stack/{name}/flows  -> {"flows": [Schema__Vnc__Mitm__Flow__Summary, ...]}
#
# Returns 404 if the stack doesn't exist; otherwise an envelope with the
# (possibly empty) list of flow summaries.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import DEFAULT_REGION, Vnc__Service


TAG__ROUTES_VNC_FLOWS = 'vnc'                                                       # Same prefix as the stack routes — keeps OpenAPI grouping tidy


class Routes__Vnc__Flows(Fast_API__Routes):
    tag     : str           = TAG__ROUTES_VNC_FLOWS
    service : Vnc__Service                                                          # Injected by Fast_API__SP__CLI.setup_routes()

    def flows(self, name: str, region: str = '', username: str = '', password: str = '') -> dict:
        if self.service.get_stack_info(region or DEFAULT_REGION, name) is None:
            raise HTTPException(status_code=404, detail=f'no vnc stack matched {name!r}')
        listing = self.service.flows(region or DEFAULT_REGION, name, username, password)
        return {'flows': [summary.json() for summary in listing]}
    flows.__route_path__ = '/stack/{name}/flows'

    def setup_routes(self):
        self.add_route_get(self.flows)
