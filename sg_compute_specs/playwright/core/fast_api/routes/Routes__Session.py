# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Session (Φ7 — opt-in stateful)
#
#   POST /session/open                    -> Schema__Session__Open__Response
#   POST /session/{session_id}/act        -> Schema__Sequence__Response
#   POST /session/{session_id}/probe      -> Schema__Inspect__Response
#   POST /session/{session_id}/close      -> {session_id, closed: bool}
#
# Use case: amortise navigate + decrypt across multiple probe batches.
# Open once, act/probe many times, close (or let TTL expire).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.decorators.route_path                                           import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix              import Safe_Str__Fast_API__Route__Prefix

from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Response             import Schema__Inspect__Response
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response            import Schema__Sequence__Response
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Act__Request   import Schema__Session__Act__Request
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Open__Request  import Schema__Session__Open__Request
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Open__Response import Schema__Session__Open__Response
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Probe__Request import Schema__Session__Probe__Request
from sg_compute_specs.playwright.core.service.Playwright__Service                            import Playwright__Service


TAG__ROUTES_SESSION   = 'session'
ROUTES_PATHS__SESSION = ['/session/open',
                         '/session/{session_id}/act',
                         '/session/{session_id}/probe',
                         '/session/{session_id}/close']


class Routes__Session(Fast_API__Routes):
    tag     : str                 = TAG__ROUTES_SESSION
    service : Playwright__Service

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # Mount at root so @route_path gives full paths

    @route_path('/session/open')
    def open(self, body: Schema__Session__Open__Request) -> Schema__Session__Open__Response:
        return self.service.session_open(body)

    @route_path('/session/{session_id}/act')
    def act(self, session_id: str, body: Schema__Session__Act__Request) -> Schema__Sequence__Response:
        return self.service.session_act(session_id, body)

    @route_path('/session/{session_id}/probe')
    def probe(self, session_id: str, body: Schema__Session__Probe__Request) -> Schema__Inspect__Response:
        return self.service.session_probe(session_id, body)

    @route_path('/session/{session_id}/close')
    def close(self, session_id: str) -> dict:
        return self.service.session_close(session_id)

    def setup_routes(self):
        self.add_route_post(self.open )
        self.add_route_post(self.act  )
        self.add_route_post(self.probe)
        self.add_route_post(self.close)
