# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Quick
#
# Low-friction, "one-shot" convenience endpoints. Each spins up a throwaway
# session, runs a tiny internal sequence (navigate → optional click → capture),
# tears the session down, and returns exactly what the caller asked for.
#
#   POST /quick/html        -> Schema__Quick__Html__Response   (JSON body)
#   POST /quick/screenshot  -> image/png                        (raw PNG bytes)
#
# Schemas are deliberately FLAT — the whole point is to give Swagger UI a
# minimal, obvious example body (just `url`, plus one or two optional fields)
# rather than the full Schema__Action__Request / Schema__Sequence__Request
# tree with nested capture_config + browser_config.
#
# Screenshot returns a raw image response rather than a Type_Safe schema — the
# bytes come straight from the captured artefact's inline_b64 field. Swagger
# renders a "Download file" button. HTML is still JSON because callers almost
# always want structured metadata alongside the markup.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                            import Response

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Html__Request            import Schema__Quick__Html__Request
from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Screenshot__Request      import Schema__Quick__Screenshot__Request
from sgraph_ai_service_playwright.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_QUICK   = 'quick'
ROUTES_PATHS__QUICK = [f'/{TAG__ROUTES_QUICK}/html'      ,
                       f'/{TAG__ROUTES_QUICK}/screenshot']

MEDIA_TYPE__PNG = 'image/png'


class Routes__Quick(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_QUICK
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def html(self, body: Schema__Quick__Html__Request) -> dict:
        return self.service.quick_html(body).json()

    def screenshot(self, body: Schema__Quick__Screenshot__Request) -> Response:     # Raw PNG — FastAPI passes Response objects through untouched
        png_bytes = self.service.quick_screenshot(body)
        return Response(content=png_bytes, media_type=MEDIA_TYPE__PNG)

    def setup_routes(self):
        self.add_route_post(self.html      )
        self.add_route_post(self.screenshot)
