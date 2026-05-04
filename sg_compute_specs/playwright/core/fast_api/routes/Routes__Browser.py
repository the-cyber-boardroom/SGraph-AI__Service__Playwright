# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Browser (v0.1.24 — stateless one-shot surface)
#
# Six POST endpoints. Each is a self-contained round-trip: launch fresh
# Chromium → run a tiny sequence (navigate → optional click → capture) → tear
# Chromium down → return result.
#
#   POST /browser/navigate    -> Schema__Browser__One_Shot__Response  (JSON)
#   POST /browser/click       -> Schema__Browser__One_Shot__Response  (JSON)
#   POST /browser/fill        -> Schema__Browser__One_Shot__Response  (JSON)
#   POST /browser/get-content -> Schema__Browser__One_Shot__Response  (JSON; html populated)
#   POST /browser/get-url     -> Schema__Browser__One_Shot__Response  (JSON)
#   POST /browser/screenshot  -> image/png                            (raw PNG bytes)
#
# Screenshot returns raw bytes; timings are surfaced as X-*-Ms response
# headers (same fields as Schema__Sequence__Timings). All other endpoints
# embed the timings block inside the JSON response body.
#
# Routes carry zero logic — they instantiate no schemas, they just forward the
# parsed body into Playwright__Service.browser_<action>() and serialise.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                            import Response

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Click__Request       import Schema__Browser__Click__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Fill__Request        import Schema__Browser__Fill__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Get_Content__Request import Schema__Browser__Get_Content__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Get_Url__Request     import Schema__Browser__Get_Url__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Navigate__Request    import Schema__Browser__Navigate__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Screenshot__Request  import Schema__Browser__Screenshot__Request
from sg_compute_specs.playwright.core.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_BROWSER   = 'browser'
ROUTES_PATHS__BROWSER = [f'/{TAG__ROUTES_BROWSER}/navigate'   ,
                         f'/{TAG__ROUTES_BROWSER}/click'      ,
                         f'/{TAG__ROUTES_BROWSER}/fill'       ,
                         f'/{TAG__ROUTES_BROWSER}/get-content',
                         f'/{TAG__ROUTES_BROWSER}/get-url'    ,
                         f'/{TAG__ROUTES_BROWSER}/screenshot' ]

MEDIA_TYPE__PNG = 'image/png'


class Routes__Browser(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_BROWSER
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def navigate(self, body: Schema__Browser__Navigate__Request) -> dict:
        return self.service.browser_navigate(body).json()

    def click(self, body: Schema__Browser__Click__Request) -> dict:
        return self.service.browser_click(body).json()

    def fill(self, body: Schema__Browser__Fill__Request) -> dict:
        return self.service.browser_fill(body).json()

    def get_content(self, body: Schema__Browser__Get_Content__Request) -> dict:     # osbot-fast-api converts `_` -> `-` in paths -> /browser/get-content
        return self.service.browser_get_content(body).json()

    def get_url(self, body: Schema__Browser__Get_Url__Request) -> dict:             # /browser/get-url
        return self.service.browser_get_url(body).json()

    def screenshot(self, body: Schema__Browser__Screenshot__Request) -> Response:   # Raw PNG — FastAPI passes Response objects through untouched
        result  = self.service.browser_screenshot(body)
        timings = result.timings
        headers = {'X-Playwright-Start-Ms': str(int(timings.playwright_start_ms)),  # Raw PNG body leaves no room for JSON timings, so surface them via response headers instead (same fields as Schema__Sequence__Timings)
                   'X-Browser-Launch-Ms'  : str(int(timings.browser_launch_ms  )),
                   'X-Steps-Ms'           : str(int(timings.steps_ms           )),
                   'X-Browser-Close-Ms'   : str(int(timings.browser_close_ms   )),
                   'X-Total-Ms'           : str(int(timings.total_ms           ))}
        return Response(content=result.png_bytes, media_type=MEDIA_TYPE__PNG, headers=headers)

    def setup_routes(self):
        self.add_route_post(self.navigate   )
        self.add_route_post(self.click      )
        self.add_route_post(self.fill       )
        self.add_route_post(self.get_content)
        self.add_route_post(self.get_url    )
        self.add_route_post(self.screenshot )
