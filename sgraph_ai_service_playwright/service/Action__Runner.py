# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Action__Runner (routes-catalogue-v2 §4.3)
#
# Layer-0 single-action execution. One class method — `execute(request)` —
# is the entire surface; POST /browser/* routes delegate here via
# Playwright__Service.execute_action().
#
# Flow:
#   1. Look up the session (404 if missing).
#   2. Resolve trace_id (falls back to the session's trace_id).
#   3. Resolve the page (creates context + page on first use — a freshly
#      launched browser has no contexts, so the very first /navigate would
#      otherwise trip over `contexts()[0]`).
#   4. Resolve capture_config (per-request override, then session default).
#   5. Parse the step dict into the typed Schema__Step__* via dispatcher.
#   6. Validate the step (JS allowlist + sink compatibility) via
#      Request__Validator — raises HTTPException(422) on reject.
#   7. Execute via Step__Executor (THE class that touches page.*).
#   8. Record the action on Session__Manager (bumps counters + collects
#      artefact refs on the session).
#   9. Build and return Schema__Action__Response with the fresh session_info.
#
# Spec deviation: v2 §4.3 has Action__Runner call
# `sequence_dispatcher.execute_step(...)`, but Sequence__Dispatcher today only
# parses (spec itself notes execute_step is deferred). Calling Step__Executor
# directly keeps Sequence__Dispatcher's responsibility narrow (wire → typed
# schema) and matches the existing Phase 2.9 implementation of Step__Executor.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Any

from fastapi                                                                                        import HTTPException

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                              import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Response                             import Schema__Action__Response
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.service.Capability__Detector                                      import Capability__Detector
from sgraph_ai_service_playwright.service.Request__Validator                                        import Request__Validator
from sgraph_ai_service_playwright.service.Sequence__Dispatcher                                      import Sequence__Dispatcher
from sgraph_ai_service_playwright.service.Session__Manager                                          import Session__Manager
from sgraph_ai_service_playwright.service.Step__Executor                                            import Step__Executor


class Action__Runner(Type_Safe):

    session_manager     : Session__Manager
    capability_detector : Capability__Detector
    request_validator   : Request__Validator
    sequence_dispatcher : Sequence__Dispatcher
    step_executor       : Step__Executor

    def execute(self, request: Schema__Action__Request) -> Schema__Action__Response:
        session = self.session_manager.get(request.session_id)
        if session is None:
            raise HTTPException(404, f"Session {request.session_id} not found")

        trace_id     = request.trace_id or session.trace_id or Safe_Str__Trace_Id('no-trace')
        browser      = self.session_manager.get_browser(request.session_id)
        page         = self.get_or_create_page(browser)
        cap_config   = request.capture_config or self.session_manager.get_capture_config(request.session_id)
        capabilities = self.capability_detector.capabilities()
        target       = self.capability_detector.target()

        step = self.sequence_dispatcher.parse_single_step(request.step, 0)
        self.request_validator.validate_step(step, cap_config, capabilities, target)

        step_result = self.step_executor.execute(page           = page       ,
                                                  step           = step       ,
                                                  step_index     = 0          ,
                                                  capture_config = cap_config )

        self.session_manager.record_action(request.session_id, step_result)
        session_after = self.session_manager.get(request.session_id)

        return Schema__Action__Response(session_id   = request.session_id  ,
                                         trace_id     = trace_id            ,
                                         step_result  = step_result         ,
                                         session_info = session_after       )

    def get_or_create_page(self, browser: Any) -> Any:                                  # Freshly launched browser has no context / page — create on demand
        contexts = browser.contexts()                                                   # sync_api: list of BrowserContext (existing Playwright__Service uses the same calling convention)
        context  = contexts[0] if contexts else browser.new_context()
        pages    = context.pages                                                        # sync_api: list of Page (attribute, not a call)
        return pages[0] if pages else context.new_page()
