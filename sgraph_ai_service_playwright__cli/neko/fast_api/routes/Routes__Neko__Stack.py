# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Neko__Stack
# Stub router — all routes return 501 Not Implemented.
# The plugin manifest ships with enabled=False; these routes are never mounted
# unless force-enabled for experiment purposes.
#
# When the Neko evaluation (v0.23.x) lands, this file gains real delegations
# to Neko__Service matching the VNC route shape.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                    import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                 import Fast_API__Routes

from sgraph_ai_service_playwright__cli.neko.service.Neko__Service import Neko__Service


TAG__ROUTES_NEKO = 'neko'


class Routes__Neko__Stack(Fast_API__Routes):
    tag     : str          = TAG__ROUTES_NEKO
    service : Neko__Service

    def list_stacks(self, region: str = '') -> dict:
        raise HTTPException(status_code=501, detail='Neko plugin not yet implemented — see neko/docs/README.md')
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:
        raise HTTPException(status_code=501, detail='Neko plugin not yet implemented — see neko/docs/README.md')
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:
        raise HTTPException(status_code=501, detail='Neko plugin not yet implemented — see neko/docs/README.md')
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:
        raise HTTPException(status_code=501, detail='Neko plugin not yet implemented — see neko/docs/README.md')
    delete.__route_path__ = '/stack/{name}'
