# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Desktop (sg-playwright-vnc image variant)
#
#   POST /desktop/browser  -> Schema__Desktop__Browser__Response
#
# Opens a long-lived HEADED browser on the container's X display so it is
# visible/drivable in noVNC (:6080). vnc display mode only — a headless instance
# 400s (guard lives in Desktop__Browser__Manager). The returned session_id works
# with every /session/{id}/* endpoint: automation and the human viewer share the
# same browser. Pure delegation — no logic here (rule §19).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.decorators.route_path                                           import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix              import Safe_Str__Fast_API__Route__Prefix

from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Request  import Schema__Desktop__Browser__Request
from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Response import Schema__Desktop__Browser__Response
from sg_compute_specs.playwright.core.service.Desktop__Browser__Manager                  import Desktop__Browser__Manager


TAG__ROUTES_DESKTOP   = 'desktop'
ROUTES_PATHS__DESKTOP = ['/desktop/browser']


class Routes__Desktop(Fast_API__Routes):
    tag     : str = TAG__ROUTES_DESKTOP
    manager : Desktop__Browser__Manager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # Mount at root so @route_path gives full paths

    @route_path('/desktop/browser')
    def browser(self, body: Schema__Desktop__Browser__Request) -> Schema__Desktop__Browser__Response:
        return self.manager.open_browser(body)

    def setup_routes(self):
        self.add_route_post(self.browser)
