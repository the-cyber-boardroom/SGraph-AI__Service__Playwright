# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Screenshot
#
#   POST /screenshot        → Schema__Screenshot__Response        (JSON)
#   POST /screenshot/batch  → Schema__Screenshot__Batch__Response (JSON)
#
# Simple API: URL in, base64 PNG (or HTML) out. No session management, no
# sequence definition. Full /browser/* and /sequence/* surfaces unchanged.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.decorators.route_path                                           import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix              import Safe_Str__Fast_API__Route__Prefix

from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Batch__Request  import Schema__Screenshot__Batch__Request
from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Request         import Schema__Screenshot__Request
from sgraph_ai_service_playwright.service.Playwright__Service                            import Playwright__Service


TAG__ROUTES_SCREENSHOT   = 'screenshot'
ROUTES_PATHS__SCREENSHOT = ['/screenshot', '/screenshot/batch']


class Routes__Screenshot(Fast_API__Routes):
    tag     : str                 = TAG__ROUTES_SCREENSHOT
    service : Playwright__Service

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')              # Mount at root so @route_path gives full paths directly

    @route_path('/screenshot')
    def screenshot(self, body: Schema__Screenshot__Request) -> dict:
        return self.service.screenshot_simple(body).json()

    @route_path('/screenshot/batch')
    def batch(self, body: Schema__Screenshot__Batch__Request) -> dict:
        return self.service.screenshot_batch(body).json()

    def setup_routes(self):
        self.add_route_post(self.screenshot)
        self.add_route_post(self.batch     )
