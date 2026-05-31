# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Inspect (Φ5 — probe-batch headline feature)
#
# POST /inspect — snapshot-once, probe-many. Caller submits one navigate + a
# settle phase + a named bag of read-only probes; service returns probe
# results keyed by the caller's names + (optionally) a diagnostics bundle
# when any step failed.
#
# Mounted at root via prefix='/' + @route_path('/inspect') — matches the
# /screenshot pattern (flat endpoint, no inferred sub-path).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.decorators.route_path                                           import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix              import Safe_Str__Fast_API__Route__Prefix

from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Request              import Schema__Inspect__Request
from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Response             import Schema__Inspect__Response
from sg_compute_specs.playwright.core.service.Playwright__Service                           import Playwright__Service


TAG__ROUTES_INSPECT   = 'inspect'
ROUTES_PATHS__INSPECT = ['/inspect']


class Routes__Inspect(Fast_API__Routes):
    tag     : str                 = TAG__ROUTES_INSPECT
    service : Playwright__Service

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # Mount at root — flat /inspect

    @route_path('/inspect')
    def inspect(self, body: Schema__Inspect__Request) -> Schema__Inspect__Response:
        return self.service.inspect(body)

    def setup_routes(self):
        self.add_route_post(self.inspect)
