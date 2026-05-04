# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Sequence__Runner (v0.1.24 — stateless)
#
# Layer-3 multi-step execution. Stateless by design: every call launches a
# fresh sync_playwright + Chromium, runs the declared step list, and tears
# both down in try/finally before returning.
#
# Flow:
#   1. Resolve sequence_id + trace_id (auto-generate if missing).
#   2. Parse every step dict via sequence_dispatcher.parse_steps (wire → typed).
#   3. Reject duplicate step ids (Request__Validator.validate_step_ids_unique).
#   4. Validate browser_config — CDP endpoint URL required when provider=cdp_connect.
#   5. Launch a fresh Chromium (Schema__Browser__Launch__Result) — mint an
#      internal session_id for the launcher's per-request key + teardown hook.
#   6. Create context + page; apply SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS if set
#      (needed when the agent_mitmproxy sidecar does TLS interception on EC2).
#   7. Apply optional credentials (cookies / storage state / headers) to the
#      fresh context via Credentials__Loader.
#   8. Iterate:
#        • If halted or deadline breached → mark remaining steps SKIPPED.
#        • Otherwise validate (JS allowlist + sink compat) and execute via
#          Step__Executor. Collect artefact refs.
#        • On failure with halt_on_error=True → flip halted.
#   9. Derive status (COMPLETED / FAILED / PARTIAL).
#  10. try/finally: always stop the launched Chromium + sync_playwright runtime.
#  11. Build + return Schema__Sequence__Response with aggregated counters, full
#      artefact list, and Schema__Sequence__Timings block.
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid
from typing                                                                                         import Any, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.utils.Env                                                                          import get_env

from sgraph_ai_service_playwright.consts.env_vars                                                   import ENV_VAR__IGNORE_HTTPS_ERRORS, ENV_VAR__REQUEST_DEADLINE_MS
from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request                        import Schema__Sequence__Request
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Response                       import Schema__Sequence__Response
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Timings                        import Schema__Sequence__Timings
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sgraph_ai_service_playwright.service.Browser__Launcher                                         import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                                      import Capability__Detector
from sgraph_ai_service_playwright.service.Credentials__Loader                                       import Credentials__Loader
from sgraph_ai_service_playwright.service.Request__Validator                                        import Request__Validator
from sgraph_ai_service_playwright.service.Sequence__Dispatcher                                      import Sequence__Dispatcher
from sgraph_ai_service_playwright.service.Step__Executor                                            import Step__Executor


DEFAULT_REQUEST_DEADLINE_MS = 25000                                                 # 5 s headroom under CloudFront's 30 s gateway timeout


class Sequence__Runner(Type_Safe):

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

        parsed_steps = self.sequence_dispatcher.parse_steps(request.steps)
        self.request_validator.validate_step_ids_unique(parsed_steps)
        self.request_validator.validate_browser_config(request.browser_config, capabilities)

        browser_config       = request.browser_config or Schema__Browser__Config()      # Defaults (headless Chromium) when caller omits
        launch_result        = self.browser_launcher.launch(browser_config)             # Fresh sync_playwright + Chromium per call
        session_id           = Session_Id()                                             # Internal trace-only handle for launcher registry + teardown
        self.browser_launcher.register(session_id, launch_result)
        playwright_start_ms  = int(launch_result.playwright_start_ms)
        browser_launch_ms    = int(launch_result.browser_launch_ms)

        step_results : List[Schema__Step__Result__Base] = []
        artefacts    : List[Schema__Artefact__Ref]      = []
        passed  = 0
        failed  = 0
        skipped = 0
        halted  = False

        deadline_ms      = started_ms + self.get_deadline_ms()                          # Wall-clock soft deadline — between-step check only
        steps_started_ms = int(time.time() * 1000)
        browser_close_ms = 0

        try:
            page = self.get_or_create_page(launch_result.browser, session_id)
            if request.credentials:
                context = launch_result.browser.contexts[0] if launch_result.browser.contexts else None
                self.credentials_loader.apply(context, request.credentials)

            for step_index, step in enumerate(parsed_steps):
                if halted:                                                              # After halt_on_error failure → SKIPPED
                    result = self.skipped_result(step, step_index)
                    step_results.append(result)
                    skipped += 1
                    continue

                if int(time.time() * 1000) >= deadline_ms:                              # Deadline breached — treat like halt_on_error
                    halted = True
                    result = self.skipped_result(step, step_index)
                    step_results.append(result)
                    skipped += 1
                    continue

                self.request_validator.validate_step(step, capture_config, capabilities, target)

                result = self.step_executor.execute(page           = page           ,
                                                     step           = step           ,
                                                     step_index     = step_index     ,
                                                     capture_config = capture_config )
                step_results.append(result)

                if result.status == Enum__Step__Status.PASSED:
                    passed += 1
                elif result.status == Enum__Step__Status.FAILED:
                    failed += 1
                    if request.sequence_config.halt_on_error:
                        halted = True

                for ref in result.artefacts:
                    artefacts.append(ref)
        finally:
            steps_ms         = int(time.time() * 1000) - steps_started_ms
            browser_close_ms = int(self.browser_launcher.stop(session_id))              # try/finally + idempotent stop() = guaranteed Chromium teardown even on step exceptions

        status   = self.sequence_status(failed=failed, halted=halted)
        total_ms = int(time.time() * 1000) - started_ms

        timings  = Schema__Sequence__Timings(playwright_start_ms = Safe_UInt__Milliseconds(playwright_start_ms),
                                              browser_launch_ms   = Safe_UInt__Milliseconds(browser_launch_ms  ),
                                              steps_ms            = Safe_UInt__Milliseconds(steps_ms            ),
                                              browser_close_ms    = Safe_UInt__Milliseconds(browser_close_ms    ),
                                              total_ms            = Safe_UInt__Milliseconds(total_ms            ))

        return Schema__Sequence__Response(sequence_id       = sequence_id                                       ,
                                           trace_id          = trace_id                                          ,
                                           status            = status                                            ,
                                           total_duration_ms = Safe_UInt__Milliseconds(total_ms)                  ,
                                           steps_total       = Safe_UInt(len(parsed_steps))                      ,
                                           steps_passed      = Safe_UInt(passed)                                 ,
                                           steps_failed      = Safe_UInt(failed)                                 ,
                                           steps_skipped     = Safe_UInt(skipped)                                ,
                                           step_results      = step_results                                      ,
                                           artefacts         = artefacts                                         ,
                                           timings           = timings                                           )

    def get_or_create_page(self, browser: Any, session_id: Any) -> Any:              # Freshly launched browser has no context / page — create on demand
        contexts = browser.contexts                                                  # Playwright sync API: `contexts` is a @property returning List[BrowserContext]
        if contexts:
            context = contexts[0]
        else:
            ctx_kwargs = {}
            if get_env(ENV_VAR__IGNORE_HTTPS_ERRORS):
                ctx_kwargs['ignore_https_errors'] = True                             # Set on EC2 when the agent_mitmproxy sidecar does TLS interception
            context = browser.new_context(**ctx_kwargs)

        pages = context.pages
        if pages:
            return pages[0]
        return context.new_page()

    def skipped_result(self, step: Schema__Step__Base, step_index: int) -> Schema__Step__Result__Base:
        step_id = step.id if step.id is not None else Step_Id(str(step_index))
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

    def get_deadline_ms(self) -> int:
        raw = get_env(ENV_VAR__REQUEST_DEADLINE_MS)
        return int(raw) if raw else DEFAULT_REQUEST_DEADLINE_MS
