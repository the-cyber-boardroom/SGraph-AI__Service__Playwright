# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Fast_API__Playwright__Service (v0.1.29 — agentic base)
#
# Extends Agentic_FastAPI (which in turn extends Serverless__Fast_API — the
# Mangum-backed Lambda handler base). Holds ONE Playwright__Service instance
# and wires that through to every Routes__* class. The agentic admin surface
# (/admin/info, /admin/skills/{name}, /admin/manifest) lands on the parent
# class in Day 3 of the v0.1.29 refactor and becomes available here for free.
#
# Route groups (v0.1.24):
#   • Routes__Health     — 3 endpoints (info, status, capabilities)
#   • Routes__Browser    — 6 one-shot endpoints (navigate / click / fill /
#                          get-content / get-url / screenshot) — each launches
#                          fresh Chromium, runs tiny sequence, tears down
#   • Routes__Sequence   — POST /sequence/execute (multi-step declarative)
#   • Routes__Set_Cookie — /auth/set-cookie-form + /auth/set-auth-cookie
#
# Routes__Session and Routes__Quick were removed in v0.1.24 — sessions are no
# longer a wire-visible resource, and /quick/* was absorbed into the new
# stateless /browser/* surface.
#
# This class is importable without side effects — lambda_handler.py calls
# `.setup().app()` explicitly to boot.
# ═══════════════════════════════════════════════════════════════════════════════

import uuid

from osbot_fast_api.api.routes.Routes__Set_Cookie                                    import Routes__Set_Cookie

from sgraph_ai_service_playwright.agentic_fastapi.Agentic_FastAPI                    import Agentic_FastAPI
from sgraph_ai_service_playwright.fast_api.routes.Routes__Browser                    import Routes__Browser
from sgraph_ai_service_playwright.fast_api.routes.Routes__Health                     import Routes__Health
from sgraph_ai_service_playwright.fast_api.routes.Routes__Sequence                   import Routes__Sequence
from sgraph_ai_service_playwright.service.Playwright__Service                        import Playwright__Service
from sgraph_ai_service_playwright.service.Request__Watchdog                          import Request__Watchdog


class Fast_API__Playwright__Service(Agentic_FastAPI):
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
        super().setup_routes()                                                      # Agentic_FastAPI mounts the /admin/* surface (health, info, manifest, SKILLs, capabilities)
        self.add_routes(Routes__Health   , service=self.service)
        self.add_routes(Routes__Browser  , service=self.service)
        self.add_routes(Routes__Sequence , service=self.service)
        self.add_routes(Routes__Set_Cookie)                                         # /auth/set-cookie-form (HTML UI) + /auth/set-auth-cookie (POST) — both in AUTH__EXCLUDED_PATHS so they bypass the API-key middleware
