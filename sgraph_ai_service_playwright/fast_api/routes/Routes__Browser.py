# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Browser (routes-catalogue-v2 §3.3)
#
# Layer-0 direct browser actions. Every route is POST, wraps the wire step
# in Schema__Action__Request, delegates to Playwright__Service.execute_action
# (which in turn calls Action__Runner.execute), and serialises the typed
# Schema__Action__Response.
#
# Phase 2.10 Slice B subset — three endpoints only, to let integration tests
# start exercising real sites while the remaining 13 action types stay gated
# behind their Step__Executor NotImplementedError:
#   POST /browser/navigate   -> Schema__Action__Response
#   POST /browser/click      -> Schema__Action__Response
#   POST /browser/screenshot -> Schema__Action__Response
#
# Full fan-out to the remaining 13 actions (fill / press / select / hover /
# scroll / wait-for / video-start / video-stop / evaluate / dispatch-event /
# set-viewport / get-content / get-url) lands after the subset ships green
# and the Step__Executor deferred handlers come online in Phase 2.11.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                  import Schema__Action__Request
from sgraph_ai_service_playwright.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_BROWSER   = 'browser'
ROUTES_PATHS__BROWSER = [f'/{TAG__ROUTES_BROWSER}/navigate'  ,
                         f'/{TAG__ROUTES_BROWSER}/click'     ,
                         f'/{TAG__ROUTES_BROWSER}/screenshot']


class Routes__Browser(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_BROWSER
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def navigate(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def click(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def screenshot(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def setup_routes(self):
        self.add_route_post(self.navigate  )
        self.add_route_post(self.click     )
        self.add_route_post(self.screenshot)
