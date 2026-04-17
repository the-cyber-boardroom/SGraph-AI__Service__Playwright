# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Sequence__Runner (routes-catalogue-v2 §4.4)
#
# Layer-3 multi-step execution. One class method — `execute(request)` — drives
# a heterogeneous list of steps against one session and returns a single
# aggregated Schema__Sequence__Response.
#
# Flow:
#   1. Resolve sequence_id + trace_id (auto-generate if missing).
#   2. Resolve session:
#        • `request.session_id` set → look it up (404 if missing); we do NOT own it.
#        • Otherwise → ad-hoc create via browser_launcher + session_manager,
#          replaying the same validator gate + credentials_loader hand-off that
#          Playwright__Service.session_create() uses. We mark the session as
#          owned so teardown (if requested) cleans up the Chromium process.
#   3. Parse every step dict via sequence_dispatcher.parse_steps (wire → typed).
#   4. Reject duplicate step ids (Request__Validator.validate_step_ids_unique).
#   5. Resolve the active page (lazy context + page creation, same pattern as
#      Action__Runner.get_or_create_page — a freshly launched browser has
#      neither context nor page).
#   6. Iterate:
#        • If a previous failure has halted the run → mark remaining steps SKIPPED.
#        • Otherwise validate (JS allowlist + sink compatibility) and execute
#          via Step__Executor. Record the action on Session__Manager so
#          counters + artefact bucket stay in sync with single-action runs.
#        • On failure with halt_on_error=True → flip the halted flag; the
#          remainder of the loop walks the queue emitting SKIPPED results.
#   7. Derive sequence status: COMPLETED (no failures) / FAILED (failure + halt)
#      / PARTIAL (failure, continued).
#   8. If close_session_after → session_manager.close() + browser_launcher.stop()
#      (safe for both owned and caller-owned sessions — the flag is the caller's
#      explicit intent, regardless of who started the session).
#   9. Return Schema__Sequence__Response with the post-run session_info and a
#      cumulative artefact list drawn from every passed/failed step result.
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid
from typing                                                                                         import Any, List

from fastapi                                                                                        import HTTPException

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request                        import Schema__Sequence__Request
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Response                       import Schema__Sequence__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request                  import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sgraph_ai_service_playwright.service.Browser__Launcher                                         import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                                      import Capability__Detector
from sgraph_ai_service_playwright.service.Credentials__Loader                                       import Credentials__Loader
from sgraph_ai_service_playwright.service.Request__Validator                                        import Request__Validator
from sgraph_ai_service_playwright.service.Sequence__Dispatcher                                      import Sequence__Dispatcher
from sgraph_ai_service_playwright.service.Session__Manager                                          import Session__Manager
from sgraph_ai_service_playwright.service.Step__Executor                                            import Step__Executor


class Sequence__Runner(Type_Safe):

    session_manager     : Session__Manager
    capability_detector : Capability__Detector
    request_validator   : Request__Validator
    sequence_dispatcher : Sequence__Dispatcher
    step_executor       : Step__Executor
    browser_launcher    : Browser__Launcher
    credentials_loader  : Credentials__Loader

    def execute(self, request: Schema__Sequence__Request) -> Schema__Sequence__Response:
        sequence_id    = request.sequence_id or Sequence_Id()
        trace_id       = request.trace_id    or Safe_Str__Trace_Id(uuid.uuid4().hex[:8])
        capture_config = request.capture_config
        capabilities   = self.capability_detector.capabilities()
        target         = self.capability_detector.target()
        started_ms     = int(time.time() * 1000)

        session_id = self.resolve_session(request, trace_id, capabilities)

        parsed_steps = self.sequence_dispatcher.parse_steps(request.steps)
        self.request_validator.validate_step_ids_unique(parsed_steps)

        browser = self.session_manager.get_browser(session_id)
        page    = self.get_or_create_page(browser)

        step_results : List[Schema__Step__Result__Base] = []
        artefacts    : List[Schema__Artefact__Ref]      = []
        passed  = 0
        failed  = 0
        skipped = 0
        halted  = False

        for step_index, step in enumerate(parsed_steps):
            if halted:                                                                # Remaining steps after halt_on_error failure → SKIPPED
                result = self.skipped_result(step, step_index)
                step_results.append(result)
                skipped += 1
                continue

            self.request_validator.validate_step(step, capture_config, capabilities, target)        # Raises HTTPException(422) on reject

            result = self.step_executor.execute(page           = page           ,
                                                 step           = step           ,
                                                 step_index     = step_index     ,
                                                 capture_config = capture_config )
            step_results.append(result)
            self.session_manager.record_action(session_id, result)

            if result.status == Enum__Step__Status.PASSED:
                passed += 1
            elif result.status == Enum__Step__Status.FAILED:
                failed += 1
                if request.sequence_config.halt_on_error:
                    halted = True

            for ref in result.artefacts:                                              # Cumulative list across all executed steps
                artefacts.append(ref)

        status = self.sequence_status(failed=failed, halted=halted)

        if request.close_session_after:
            self.session_manager .close(session_id)
            self.browser_launcher.stop (session_id)                                   # Idempotent real-Chromium teardown; no-op on fakes

        session_after = self.session_manager.get(session_id)

        return Schema__Sequence__Response(sequence_id       = sequence_id                                       ,
                                           trace_id          = trace_id                                          ,
                                           status            = status                                            ,
                                           total_duration_ms = Safe_UInt__Milliseconds(int(time.time() * 1000) - started_ms),
                                           steps_total       = Safe_UInt(len(parsed_steps))                      ,
                                           steps_passed      = Safe_UInt(passed)                                 ,
                                           steps_failed      = Safe_UInt(failed)                                 ,
                                           steps_skipped     = Safe_UInt(skipped)                                ,
                                           step_results      = step_results                                      ,
                                           session_info      = session_after                                     ,
                                           artefacts         = artefacts                                         )

    def resolve_session(self, request, trace_id, capabilities):
        if request.session_id:                                                        # Caller named a session — prefer reuse when it actually exists
            session = self.session_manager.get(request.session_id)
            if session is not None:
                return request.session_id
            if request.browser_config is None:                                        # Named but not found + no ad-hoc fallback → 404
                raise HTTPException(404, f"Session {request.session_id} not found")
            # Named but not found + browser_config → fall through to ad-hoc. Note: osbot-fast-api's
            # Type_Safe->Pydantic bridge auto-generates a fresh Session_Id when the wire body omits
            # `session_id`, so a "truthy session_id the manager doesn't know" is the normal path
            # for an HTTP caller who simply didn't set it.

        if request.browser_config is None:                                            # Neither existing session nor ad-hoc inputs — unrecoverable
            raise HTTPException(422, 'browser_config required when session_id is not set')

        session_create_req = Schema__Session__Create__Request(browser_config = request.browser_config ,
                                                               credentials    = request.credentials    ,
                                                               capture_config = request.capture_config ,
                                                               trace_id       = trace_id               )
        self.request_validator.validate_session_create(session_create_req, capabilities)

        browser = self.browser_launcher.launch(request.browser_config)
        session = self.session_manager.create(browser      = browser            ,
                                               request      = session_create_req ,
                                               trace_id     = trace_id           ,
                                               capabilities = capabilities       )
        if request.credentials:
            self.credentials_loader.apply(session.session_id, self.session_manager, request.credentials)
        return session.session_id

    def get_or_create_page(self, browser: Any) -> Any:                               # Freshly launched browser has no context / page — create on demand
        contexts = browser.contexts                                                  # Playwright sync API: `contexts` is a @property returning List[BrowserContext] — NEVER call it as a method (`()` triggers 'list' object is not callable)
        context  = contexts[0] if contexts else browser.new_context()
        pages    = context.pages                                                     # Same pattern — `pages` is also a @property
        return pages[0] if pages else context.new_page()

    def skipped_result(self, step: Schema__Step__Base, step_index: int) -> Schema__Step__Result__Base:
        step_id = step.id if step.id is not None else Step_Id(str(step_index))        # Same fallback as Step__Executor.resolve_id
        return Schema__Step__Result__Base(step_id     = step_id                                      ,
                                           step_index  = Safe_UInt(step_index)                       ,
                                           action      = step.action                                 ,
                                           status      = Enum__Step__Status.SKIPPED                  ,
                                           duration_ms = Safe_UInt__Milliseconds(0)                  )

    def sequence_status(self, failed: int, halted: bool) -> Enum__Sequence__Status:
        if failed == 0:
            return Enum__Sequence__Status.COMPLETED
        if halted:
            return Enum__Sequence__Status.FAILED
        return Enum__Sequence__Status.PARTIAL
