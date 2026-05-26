# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Fast_API__Conductor (the conductor's suite API)
#
# Extends osbot_fast_api.Fast_API (uvicorn inside the conductor container — not
# Lambda). Registers the suite routes. Auth: X-API-Key middleware, same convention
# as the Playwright + agent-mitmproxy services (FAST_API__AUTH__API_KEY__NAME/_VALUE).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.Fast_API import Fast_API

from sg_compute_specs.user_journey.core.conductor.api.routes.Routes__Suites import Routes__Suites


class Fast_API__Conductor(Fast_API):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.enable_api_key = True                                            # X-API-Key required for every route

    def setup_routes(self):
        self.add_routes(Routes__Suites)
