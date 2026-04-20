# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Metrics
#
# Single GET /metrics endpoint. Returns the Prometheus text exposition format
# consumed by a Prometheus scraper. The response is raw bytes with a
# text/plain media type — NOT a JSON schema — so it returns a FastAPI Response
# object directly rather than calling .json() on a Type_Safe schema.
#
# Auth: protected by the standard X-API-Key middleware (all routes are).
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi.responses                                                               import Response
from osbot_fast_api.api.routes.Fast_API__Routes                                      import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix            import Safe_Str__Fast_API__Route__Prefix

from sgraph_ai_service_playwright.metrics.Metrics__Collector                         import Metrics__Collector


TAG__ROUTES_METRICS   = 'metrics'
ROUTES_PATHS__METRICS = [f'/{TAG__ROUTES_METRICS}']


class Routes__Metrics(Fast_API__Routes):
    tag       : str               = TAG__ROUTES_METRICS
    collector : Metrics__Collector                                                   # Auto-instantiated by Type_Safe; shares module-level _REGISTRY

    def metrics(self) -> Response:
        return Response(content    = self.collector.generate_metrics(),
                        media_type = self.collector.content_type()   )

    def setup_routes(self):
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # Include router without prefix so /metrics (fn path) is the final path, not /metrics/metrics
        self.add_route_get(self.metrics)
