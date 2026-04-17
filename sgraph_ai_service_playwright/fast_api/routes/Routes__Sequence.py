# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Sequence (routes-catalogue-v2 §3.4)
#
# Layer-3 multi-step execution surface.
#   POST /sequence/execute   -> Schema__Sequence__Response
#
# Zero logic here; the route delegates straight to
# Playwright__Service.execute_sequence → Sequence__Runner.execute.
# Request body is Schema__Sequence__Request (heterogeneous `steps: List[dict]`,
# parsed by the dispatcher inside the runner).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request            import Schema__Sequence__Request
from sgraph_ai_service_playwright.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_SEQUENCE   = 'sequence'
ROUTES_PATHS__SEQUENCE = [f'/{TAG__ROUTES_SEQUENCE}/execute']


class Routes__Sequence(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_SEQUENCE
    service : Playwright__Service                                                   # Injected by Fast_API__Playwright__Service.setup_routes()

    def execute(self, body: Schema__Sequence__Request) -> dict:
        return self.service.execute_sequence(body).json()

    def setup_routes(self):
        self.add_route_post(self.execute)
