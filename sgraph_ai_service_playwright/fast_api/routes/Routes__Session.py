# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Session (routes-catalogue-v2 §3.2)
#
# Session lifecycle routes. Pure delegation to Playwright__Service — no logic
# here. Returns None from the service method → 404 here; every other result
# is serialised via `.json()` so Type_Safe schemas survive the wire.
#
# Paths (prefix from tag='session'):
#   POST   /session/create            -> Schema__Session__Create__Response
#   GET    /session/list              -> list[Schema__Session__Info]
#   GET    /session/get/by-id/{id}    -> Schema__Session__Info
#   POST   /session/save-state/{id}   -> Schema__Session__State__Save__Response
#   DELETE /session/close/{id}        -> Schema__Session__Close__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                            import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id             import Session_Id
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request      import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Request import Schema__Session__State__Save__Request
from sgraph_ai_service_playwright.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_SESSION   = 'session'
ROUTES_PATHS__SESSION = [f'/{TAG__ROUTES_SESSION}/create'            ,
                         f'/{TAG__ROUTES_SESSION}/list'              ,
                         f'/{TAG__ROUTES_SESSION}/get/by-id/{{id}}'  ,
                         f'/{TAG__ROUTES_SESSION}/save-state/{{id}}' ,
                         f'/{TAG__ROUTES_SESSION}/close/{{id}}'      ]


class Routes__Session(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_SESSION
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def create(self, body: Schema__Session__Create__Request) -> dict:
        return self.service.session_create(body).json()

    def list(self) -> list:
        return [s.json() for s in self.service.session_list()]

    def get__by_id__id(self, id: Session_Id) -> dict:
        result = self.service.session_get(id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Session {id} not found")
        return result.json()

    def save_state__id(self, id: Session_Id, body: Schema__Session__State__Save__Request) -> dict:
        result = self.service.session_save_state(id, body)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Session {id} not found")
        return result.json()

    def close__id(self, id: Session_Id) -> dict:
        result = self.service.session_close(id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Session {id} not found")
        return result.json()

    def setup_routes(self):
        self.add_route_post  (self.create          )
        self.add_route_get   (self.list            )
        self.add_route_get   (self.get__by_id__id  )
        self.add_route_post  (self.save_state__id  )
        self.add_route_delete(self.close__id       )
