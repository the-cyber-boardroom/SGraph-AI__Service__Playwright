# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Browser (routes-catalogue-v2 §3.3)
#
# Layer-0 direct browser actions. Every route is POST, wraps the wire step
# in Schema__Action__Request, delegates to Playwright__Service.execute_action
# (which in turn calls Action__Runner.execute), and serialises the typed
# Schema__Action__Response.
#
# Phase 2.10 Slice B (current scope) — six endpoints matching the six
# Step__Executor handlers that are live today:
#   POST /browser/navigate    -> Schema__Action__Response
#   POST /browser/click       -> Schema__Action__Response
#   POST /browser/fill        -> Schema__Action__Response
#   POST /browser/screenshot  -> Schema__Action__Response
#   POST /browser/get-content -> Schema__Action__Response (get_content -> /get-content)
#   POST /browser/get-url     -> Schema__Action__Response (get_url     -> /get-url)
#
# The remaining 10 actions (press / select / hover / scroll / wait-for /
# video-start / video-stop / evaluate / dispatch-event / set-viewport) stay
# gated behind Step__Executor NotImplementedError until Phase 2.11 brings
# their handlers online — then the matching routes wire straight through.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                  import Schema__Action__Request
from sgraph_ai_service_playwright.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_BROWSER   = 'browser'
ROUTES_PATHS__BROWSER = [f'/{TAG__ROUTES_BROWSER}/navigate'   ,
                         f'/{TAG__ROUTES_BROWSER}/click'      ,
                         f'/{TAG__ROUTES_BROWSER}/fill'       ,
                         f'/{TAG__ROUTES_BROWSER}/screenshot' ,
                         f'/{TAG__ROUTES_BROWSER}/get-content',
                         f'/{TAG__ROUTES_BROWSER}/get-url'    ]


class Routes__Browser(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_BROWSER
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def navigate(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def click(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def fill(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def screenshot(self, body: Schema__Action__Request) -> dict:
        return self.service.execute_action(body).json()

    def get_content(self, body: Schema__Action__Request) -> dict:                   # osbot-fast-api converts `_` -> `-` in paths -> /browser/get-content
        return self.service.execute_action(body).json()

    def get_url(self, body: Schema__Action__Request) -> dict:                       # osbot-fast-api converts `_` -> `-` in paths -> /browser/get-url
        return self.service.execute_action(body).json()

    def setup_routes(self):
        self.add_route_post(self.navigate   )
        self.add_route_post(self.click      )
        self.add_route_post(self.fill       )
        self.add_route_post(self.screenshot )
        self.add_route_post(self.get_content)
        self.add_route_post(self.get_url    )
