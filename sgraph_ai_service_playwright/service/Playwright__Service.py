# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Playwright__Service (v2 spec §4.1 orchestrator)
#
# Thin orchestrator that composes the lower-level service classes and exposes
# a single surface for FastAPI routes to call. Routes contain zero logic; they
# delegate here. All cross-schema validation happens via request_validator.
#
# Phase 2.7 scope — /health family:
#   • get_service_info()   → Schema__Service__Info           (/health/info)
#   • get_health()         → Schema__Health                  (/health/status)
#   • get_capabilities()   → Schema__Service__Capabilities   (/health/capabilities)
#
# Phase 2.10 Slice A — /session family:
#   • session_create()     → Schema__Session__Create__Response   (POST   /session/create)
#   • session_list()       → List[Schema__Session__Info]         (GET    /session/list)
#   • session_get()        → Schema__Session__Info | None        (GET    /session/get/by-id/{id})
#   • session_save_state() → Schema__Session__State__Save__Response | None (POST   /session/save-state/{id})
#   • session_close()      → Schema__Session__Close__Response | None      (DELETE /session/close/{id})
#   • generate_trace_id()  → str — used when the caller doesn't supply one
#
# Phase 2.10 Slice B subset — single-action surface:
#   • execute_action()     → Schema__Action__Response            (POST /browser/{navigate|click|screenshot})
#
# Sequence method lands in Slice C together with Sequence__Runner.
#
# setup() is idempotent; it primes Capability__Detector so service_info /
# capabilities are ready on first request (keeps the /health/info path cheap
# and predictable — no first-request detection spike).
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid
from typing                                                                             import List

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now        import Timestamp_Now

from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                  import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Response                 import Schema__Action__Response
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id     import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id             import Session_Id
from sgraph_ai_service_playwright.schemas.service.Schema__Health                        import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities         import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                 import Schema__Service__Info
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Close__Response      import Schema__Session__Close__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request      import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Response     import Schema__Session__Create__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                 import Schema__Session__Info
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Request  import Schema__Session__State__Save__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Response import Schema__Session__State__Save__Response
from sgraph_ai_service_playwright.service.Action__Runner                                import Action__Runner
from sgraph_ai_service_playwright.service.Browser__Launcher                             import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                          import Capability__Detector
from sgraph_ai_service_playwright.service.Credentials__Loader                           import Credentials__Loader
from sgraph_ai_service_playwright.service.Request__Validator                            import Request__Validator
from sgraph_ai_service_playwright.service.Session__Manager                              import Session__Manager


class Playwright__Service(Type_Safe):

    capability_detector : Capability__Detector
    session_manager     : Session__Manager
    browser_launcher    : Browser__Launcher
    request_validator   : Request__Validator
    credentials_loader  : Credentials__Loader
    action_runner       : Action__Runner

    def setup(self) -> 'Playwright__Service':
        if self.capability_detector.detected_target is None:
            self.capability_detector.detect()
        self.action_runner.session_manager     = self.session_manager                   # Share orchestrator state — default-constructed attrs would be isolated instances
        self.action_runner.capability_detector = self.capability_detector
        self.action_runner.request_validator   = self.request_validator
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

    # ─── Session surface (Phase 2.10 Slice A) ─────────────────────────────────

    def session_create(self, request: Schema__Session__Create__Request) -> Schema__Session__Create__Response:
        self.setup()
        capabilities = self.capability_detector.capabilities()
        self.request_validator.validate_session_create(request, capabilities)       # Raises HTTPException(422) on reject
        trace_id     = request.trace_id or Safe_Str__Trace_Id(self.generate_trace_id())
        browser      = self.browser_launcher.launch(request.browser_config)         # Real Chromium process (or raises)
        session      = self.session_manager.create(browser      = browser     ,
                                                    request      = request     ,
                                                    trace_id     = trace_id    ,
                                                    capabilities = capabilities)
        if request.credentials:
            self.credentials_loader.apply(session.session_id, self.session_manager, request.credentials)
        return Schema__Session__Create__Response(session_info = session     ,
                                                  capabilities = capabilities)

    def session_list(self) -> List[Schema__Session__Info]:
        return self.session_manager.list_active()

    def session_get(self, session_id: Session_Id) -> Schema__Session__Info:
        return self.session_manager.get(session_id)                                 # None → route emits 404

    def session_save_state(self                                              ,
                           session_id : Session_Id                           ,
                           request    : Schema__Session__State__Save__Request
                      ) -> Schema__Session__State__Save__Response:
        session = self.session_manager.get(session_id)
        if session is None:
            return None                                                             # Route emits 404
        browser  = self.session_manager.get_browser(session_id)
        state    = browser.contexts()[0].storage_state()                            # Playwright storage-state dict — {cookies, origins}
        self.credentials_loader.save_state_to_vault(request.vault_ref, state)
        return Schema__Session__State__Save__Response(session_id = session_id        ,
                                                       vault_ref  = request.vault_ref ,
                                                       saved_at   = Timestamp_Now()   )

    def session_close(self, session_id: Session_Id) -> Schema__Session__Close__Response:
        session = self.session_manager.get(session_id)
        if session is None:
            return None                                                             # Route emits 404
        artefacts   = self.session_manager.get_artefacts(session_id)
        start_time  = self.session_manager.get_start_time(session_id)
        duration_ms = int((time.time() * 1000) - start_time)
        self.session_manager.close(session_id)
        self.browser_launcher.stop(session_id)                                      # Real Chromium .close()
        return Schema__Session__Close__Response(session_info      = session      ,
                                                 artefacts         = list(artefacts),
                                                 total_duration_ms = duration_ms  )

    # ─── Action surface (Phase 2.10 Slice B subset) ───────────────────────────

    def execute_action(self, request: Schema__Action__Request) -> Schema__Action__Response:
        self.setup()                                                                # Idempotent — re-shares Action__Runner deps in case of late mutation
        return self.action_runner.execute(request)

    # ─── Utility ──────────────────────────────────────────────────────────────

    def generate_trace_id(self) -> str:                                             # Short random hex; callers may supply their own
        return uuid.uuid4().hex[:8]
