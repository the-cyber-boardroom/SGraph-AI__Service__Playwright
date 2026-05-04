# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Health (spec §4 — /health/* endpoints)
#
# Three GET endpoints, pure delegation to Playwright__Service. No logic lives
# here; the route class is a FastAPI wire-up that binds URLs to service methods.
#
# Paths (prefix from tag='health'):
#   GET /health/info         -> Schema__Service__Info
#   GET /health/status       -> Schema__Health
#   GET /health/capabilities -> Schema__Service__Capabilities
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sg_compute_specs.playwright.core.schemas.service.Schema__Health                        import Schema__Health
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Capabilities         import Schema__Service__Capabilities
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Info                 import Schema__Service__Info
from sg_compute_specs.playwright.core.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_HEALTH   = 'health'
ROUTES_PATHS__HEALTH = [f'/{TAG__ROUTES_HEALTH}/info'         ,
                        f'/{TAG__ROUTES_HEALTH}/status'       ,
                        f'/{TAG__ROUTES_HEALTH}/capabilities' ]


class Routes__Health(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_HEALTH
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def info(self) -> Schema__Service__Info:
        return self.service.get_service_info()

    def status(self) -> Schema__Health:
        return self.service.get_health()

    def capabilities(self) -> Schema__Service__Capabilities:
        return self.service.get_capabilities()

    def setup_routes(self):
        self.add_route_get(self.info        )
        self.add_route_get(self.status      )
        self.add_route_get(self.capabilities)
