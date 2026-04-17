# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Fast_API__Playwright__Service (spec §4.1)
#
# Extends Serverless__Fast_API (which itself extends osbot-fast-api Fast_API
# and adds a Mangum handler for Lambda). Holds ONE Playwright__Service
# instance and wires that through to every Routes__* class.
#
# Phase 2.7  scope: Routes__Health.
# Phase 2.10 Slice A: Routes__Session  (session lifecycle).
# Phase 2.10 Slice B: Routes__Browser  (6 of 16 single-action endpoints — the six Step__Executor handlers live today).
# Phase 2.10 Slice C: Routes__Sequence (POST /sequence/execute — Sequence__Runner).
# Quick slice      : Routes__Quick     (POST /quick/{html,screenshot} — one-shot
#                    convenience endpoints with flat Swagger-friendly schemas).
#
# This class is importable without side effects — lambda_handler.py calls
# `.setup().app()` explicitly to boot.
# ═══════════════════════════════════════════════════════════════════════════════

import uuid

from osbot_fast_api.api.routes.Routes__Set_Cookie                                    import Routes__Set_Cookie
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                          import Serverless__Fast_API

from sgraph_ai_service_playwright.fast_api.routes.Routes__Browser                    import Routes__Browser
from sgraph_ai_service_playwright.fast_api.routes.Routes__Health                     import Routes__Health
from sgraph_ai_service_playwright.fast_api.routes.Routes__Quick                      import Routes__Quick
from sgraph_ai_service_playwright.fast_api.routes.Routes__Sequence                   import Routes__Sequence
from sgraph_ai_service_playwright.fast_api.routes.Routes__Session                    import Routes__Session
from sgraph_ai_service_playwright.service.Playwright__Service                        import Playwright__Service
from sgraph_ai_service_playwright.service.Request__Watchdog                          import Request__Watchdog


class Fast_API__Playwright__Service(Serverless__Fast_API):
    service  : Playwright__Service
    watchdog : Request__Watchdog                                                    # Started in setup(); kills process via os._exit(2) when a request exceeds the hard cap so AWS provisions a fresh Lambda container

    def setup(self):
        self.service.setup()                                                        # Prime Capability__Detector before any request lands
        self.watchdog.setup().start()                                               # Background thread — disabled via ENV_VAR__WATCHDOG_DISABLED='1' for local / tests
        result = super().setup()                                                    # API-key middleware is enabled by Serverless__Fast_API__Config default (reads FAST_API__AUTH__API_KEY__NAME / FAST_API__AUTH__API_KEY__VALUE)
        self.attach_watchdog_middleware()                                           # Needs the app instance built by super().setup()
        return result

    def attach_watchdog_middleware(self):
        watchdog = self.watchdog
        app      = self.app()

        @app.middleware('http')                                                     # Runs for every HTTP request; async wrapper around the sync route stack
        async def watchdog_middleware(request, call_next):
            request_id = str(uuid.uuid4())                                          # Local to the watchdog — not the trace_id surfaced to callers
            watchdog.register(request_id)
            try:
                return await call_next(request)
            finally:
                watchdog.unregister(request_id)                                     # Runs even when call_next raises so the in-flight map stays accurate

    def setup_routes(self):
        self.add_routes(Routes__Health    , service=self.service)
        self.add_routes(Routes__Session   , service=self.service)
        self.add_routes(Routes__Browser   , service=self.service)
        self.add_routes(Routes__Sequence  , service=self.service)
        self.add_routes(Routes__Quick     , service=self.service)                   # /quick/html + /quick/screenshot — flat-schema convenience surface
        self.add_routes(Routes__Set_Cookie)                                         # /auth/set-cookie-form (HTML UI) + /auth/set-auth-cookie (POST) — both in AUTH__EXCLUDED_PATHS so they bypass the API-key middleware
