# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Playwright__Service (v2 spec §4.1 orchestrator)
#
# Thin orchestrator that composes the lower-level service classes and exposes
# a single surface for FastAPI routes to call. Routes contain zero logic; they
# delegate here. All cross-schema validation happens via request_validator.
#
# Phase 2.7 scope — ONLY the /health family is wired:
#   • get_service_info()   → Schema__Service__Info           (/health/info)
#   • get_health()         → Schema__Health                  (/health/status)
#   • get_capabilities()   → Schema__Service__Capabilities   (/health/capabilities)
#
# Session/action/sequence methods are NOT on this class yet — they land when
# Routes__Session / Routes__Browser / Routes__Sequence arrive in Phase 2.10
# alongside Step__Executor + Action__Runner + Sequence__Runner.
#
# setup() is idempotent; it primes Capability__Detector so service_info /
# capabilities are ready on first request (keeps the /health/info path cheap
# and predictable — no first-request detection spike).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright.schemas.service.Schema__Health                        import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities         import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                 import Schema__Service__Info
from sgraph_ai_service_playwright.service.Browser__Launcher                             import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                          import Capability__Detector
from sgraph_ai_service_playwright.service.Request__Validator                            import Request__Validator
from sgraph_ai_service_playwright.service.Session__Manager                              import Session__Manager


class Playwright__Service(Type_Safe):

    capability_detector : Capability__Detector
    session_manager     : Session__Manager
    browser_launcher    : Browser__Launcher
    request_validator   : Request__Validator

    def setup(self) -> 'Playwright__Service':
        if self.capability_detector.detected_target is None:
            self.capability_detector.detect()
        return self

    # ─── Health surface (Phase 2.7) ────────────────────────────────────────────

    def get_service_info(self) -> Schema__Service__Info:
        self.setup()                                                                # Self-heal if a caller forgot to wire setup()
        return self.capability_detector.service_info()

    def get_capabilities(self) -> Schema__Service__Capabilities:
        self.setup()
        return self.capability_detector.capabilities()

    def get_health(self) -> Schema__Health:
        checks  = [self.browser_launcher  .healthcheck()        ,
                   self.session_manager   .healthcheck()        ,
                   self.capability_detector.connectivity_check()]
        healthy = all(c.healthy for c in checks)
        return Schema__Health(healthy = healthy ,
                              checks  = checks  )
