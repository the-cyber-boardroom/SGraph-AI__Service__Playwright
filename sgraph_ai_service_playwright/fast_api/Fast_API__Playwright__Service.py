# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Fast_API__Playwright__Service (spec §4.1)
#
# Extends Serverless__Fast_API (which itself extends osbot-fast-api Fast_API
# and adds a Mangum handler for Lambda). Holds ONE Playwright__Service
# instance and wires that through to every Routes__* class.
#
# Phase 2.7 scope: only Routes__Health is registered. The remaining route
# classes (Routes__Session, Routes__Browser, Routes__Sequence) are added in
# Phase 2.10 once Step__Executor + Action__Runner + Sequence__Runner exist.
#
# This class is importable without side effects — lambda_handler.py calls
# `.setup().app()` explicitly to boot.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Routes__Set_Cookie                                    import Routes__Set_Cookie
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                          import Serverless__Fast_API

from sgraph_ai_service_playwright.fast_api.routes.Routes__Health                     import Routes__Health
from sgraph_ai_service_playwright.service.Playwright__Service                        import Playwright__Service


class Fast_API__Playwright__Service(Serverless__Fast_API):
    service : Playwright__Service

    def setup(self):
        self.service.setup()                                                        # Prime Capability__Detector before any request lands
        return super().setup()                                                      # API-key middleware is enabled by Serverless__Fast_API__Config default (reads FAST_API__AUTH__API_KEY__NAME / FAST_API__AUTH__API_KEY__VALUE)

    def setup_routes(self):
        self.add_routes(Routes__Health    , service=self.service)
        self.add_routes(Routes__Set_Cookie)                                         # /auth/set-cookie-form (HTML UI) + /auth/set-auth-cookie (POST) — both in AUTH__EXCLUDED_PATHS so they bypass the API-key middleware
