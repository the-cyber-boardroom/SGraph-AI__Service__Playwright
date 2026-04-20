# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__Metrics
#
# Single GET /metrics endpoint. Returns the Prometheus text exposition format
# serialised from MITMPROXY_REGISTRY (the dedicated registry populated by
# Prometheus_Metrics addon in prometheus_metrics_addon.py).
#
# Auth: protected by the standard X-API-Key middleware (all routes are).
# ═══════════════════════════════════════════════════════════════════════════════

from prometheus_client                                                               import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses                                                               import Response
from osbot_fast_api.api.routes.Fast_API__Routes                                      import Fast_API__Routes

from agent_mitmproxy.addons.prometheus_metrics_addon                                 import MITMPROXY_REGISTRY


TAG__ROUTES_METRICS   = 'metrics'
ROUTES_PATHS__METRICS = [f'/{TAG__ROUTES_METRICS}']


class Routes__Metrics(Fast_API__Routes):
    tag : str = TAG__ROUTES_METRICS

    def metrics(self) -> Response:
        return Response(content    = generate_latest(MITMPROXY_REGISTRY),
                        media_type = CONTENT_TYPE_LATEST                )

    def setup_routes(self):
        self.add_route_get(self.metrics)
