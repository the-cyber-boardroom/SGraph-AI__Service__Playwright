# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Neko__Stack
# HTTP surface for the Neko (WebRTC browser) plugin. Routes carry zero logic —
# pure delegation to Neko__Service.
#
# Endpoints:
#   POST   /neko/stack           → Schema__Neko__Stack__Create__Response
#   GET    /neko/stacks          → Schema__Neko__Stack__List
#   GET    /neko/stack/{name}    → Schema__Neko__Stack__Info   (404 on miss)
#   DELETE /neko/stack/{name}    → Schema__Neko__Stack__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Create__Request import Schema__Neko__Stack__Create__Request
from sgraph_ai_service_playwright__cli.neko.service.Neko__Service                   import DEFAULT_REGION, Neko__Service


TAG__ROUTES_NEKO = 'neko'


class Routes__Neko__Stack(Fast_API__Routes):
    tag     : str          = TAG__ROUTES_NEKO
    service : Neko__Service

    def list_stacks(self, region: str = '') -> dict:                                # GET /neko/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /neko/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no neko stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /neko/stack
        request = Schema__Neko__Stack__Create__Request.from_json(body)
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /neko/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted and not response.target:
            raise HTTPException(status_code=404, detail=f'no neko stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'
