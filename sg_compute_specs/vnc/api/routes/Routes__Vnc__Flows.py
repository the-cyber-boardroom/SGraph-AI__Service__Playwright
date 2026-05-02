# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Routes__Vnc__Flows
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sg_compute_specs.vnc.service.Vnc__Service                                      import DEFAULT_REGION, Vnc__Service


TAG__ROUTES_VNC_FLOWS = 'vnc'


class Routes__Vnc__Flows(Fast_API__Routes):
    tag     : str         = TAG__ROUTES_VNC_FLOWS
    service : Vnc__Service

    def flows(self, name: str, region: str = '', username: str = '', password: str = '') -> dict:  # GET /api/specs/vnc/stack/{name}/flows
        if self.service.get_stack_info(region or DEFAULT_REGION, name) is None:
            raise HTTPException(status_code=404, detail=f'no vnc stack matched {name!r}')
        listing = self.service.flows(region or DEFAULT_REGION, name, username, password)
        return {'flows': [summary.json() for summary in listing]}
    flows.__route_path__ = '/stack/{name}/flows'

    def setup_routes(self):
        self.add_route_get(self.flows)
