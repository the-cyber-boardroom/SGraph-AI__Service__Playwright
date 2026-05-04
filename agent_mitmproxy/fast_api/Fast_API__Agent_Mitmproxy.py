# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Fast_API__Agent_Mitmproxy (admin API base class)
#
# Extends osbot_fast_api.Fast_API (NOT Serverless__Fast_API — we don't deploy
# to Lambda; uvicorn inside the container is the runtime). Registers the
# four route classes on setup_routes().
#
# Auth: X-API-Key middleware is enabled via config.enable_api_key=True.
# Values come from FAST_API__AUTH__API_KEY__NAME / _VALUE env vars (same
# convention as Playwright).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.Fast_API                                                         import Fast_API

from agent_mitmproxy.fast_api.routes.Routes__CA                                          import Routes__CA
from agent_mitmproxy.fast_api.routes.Routes__Config                                      import Routes__Config
from agent_mitmproxy.fast_api.routes.Routes__Health                                      import Routes__Health
from agent_mitmproxy.fast_api.routes.Routes__Metrics                                     import Routes__Metrics
from agent_mitmproxy.fast_api.routes.Routes__Web                                         import Routes__Web


class Fast_API__Agent_Mitmproxy(Fast_API):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.enable_api_key = True                                                # X-API-Key required for every route (default routes like /docs stay open per osbot-fast-api defaults)

    def setup_routes(self):
        self.add_routes(Routes__Health )
        self.add_routes(Routes__CA     )
        self.add_routes(Routes__Config )
        self.add_routes(Routes__Metrics)
        self.add_routes(Routes__Web    )
