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
# Phase 2.10 Slice B — single-action surface (all six live Step__Executor actions):
#   • execute_action()     → Schema__Action__Response            (POST /browser/{navigate|click|fill|screenshot|get-content|get-url})
#
# Phase 2.10 Slice C — sequence surface:
#   • execute_sequence()   → Schema__Sequence__Response          (POST /sequence/execute)
#
# setup() is idempotent; it primes Capability__Detector so service_info /
# capabilities are ready on first request (keeps the /health/info path cheap
# and predictable — no first-request detection spike).
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import time
import traceback
import uuid
from typing                                                                             import List

from fastapi                                                                            import HTTPException
from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now        import Timestamp_Now
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Sink_Config        import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config               import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config               import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                  import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Response                 import Schema__Action__Response
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                    import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type                    import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                  import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                      import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id     import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id             import Session_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds    import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Page__Content       import Safe_Str__Page__Content
from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Html__Request            import Schema__Quick__Html__Request
from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Html__Response           import Schema__Quick__Html__Response
from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Screenshot__Request      import Schema__Quick__Screenshot__Request
from sgraph_ai_service_playwright.schemas.quick.Schema__Quick__Screenshot__Result       import Schema__Quick__Screenshot__Result
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config             import Schema__Sequence__Config
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request            import Schema__Sequence__Request
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Response           import Schema__Sequence__Response
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
from sgraph_ai_service_playwright.service.Sequence__Runner                              import Sequence__Runner
from sgraph_ai_service_playwright.service.Session__Manager                              import Session__Manager


class Playwright__Service(Type_Safe):

    capability_detector : Capability__Detector
    session_manager     : Session__Manager
    browser_launcher    : Browser__Launcher
    request_validator   : Request__Validator
    credentials_loader  : Credentials__Loader
    action_runner       : Action__Runner
    sequence_runner     : Sequence__Runner

    def setup(self) -> 'Playwright__Service':
        if self.capability_detector.detected_target is None:
            self.capability_detector.detect()
        self.action_runner.session_manager       = self.session_manager                 # Share orchestrator state — default-constructed attrs would be isolated instances
        self.action_runner.capability_detector   = self.capability_detector
        self.action_runner.request_validator     = self.request_validator
        self.sequence_runner.session_manager     = self.session_manager
        self.sequence_runner.capability_detector = self.capability_detector
        self.sequence_runner.request_validator   = self.request_validator
        self.sequence_runner.browser_launcher    = self.browser_launcher
        self.sequence_runner.credentials_loader  = self.credentials_loader
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
        capabilities  = self.capability_detector.capabilities()
        self.request_validator.validate_session_create(request, capabilities)       # Raises HTTPException(422) on reject
        trace_id      = request.trace_id or Safe_Str__Trace_Id(self.generate_trace_id())
        launch_result = self.browser_launcher.launch(request.browser_config)        # Returns Schema__Browser__Launch__Result (browser + playwright + timings)
        session       = self.session_manager.create(browser      = launch_result.browser,
                                                     request      = request              ,
                                                     trace_id     = trace_id             ,
                                                     capabilities = capabilities         )
        self.browser_launcher.register(session.session_id, launch_result)           # Track launch handles so session_close() can stop both
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
        state    = browser.contexts[0].storage_state()                              # Playwright sync API: `contexts` is a @property returning a list — do NOT call with ()
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

    # ─── Action surface (Phase 2.10 Slice B) ──────────────────────────────────

    def execute_action(self, request: Schema__Action__Request) -> Schema__Action__Response:
        self.setup()                                                                # Idempotent — re-shares Action__Runner deps in case of late mutation
        return self.action_runner.execute(request)

    # ─── Sequence surface (Phase 2.10 Slice C) ────────────────────────────────

    def execute_sequence(self, request: Schema__Sequence__Request) -> Schema__Sequence__Response:
        self.setup()                                                                # Idempotent — re-shares Sequence__Runner deps too
        return self.sequence_runner.execute(request)

    # ─── Quick surface ─────────────────────────────────────────────────────────
    # Thin wrappers over execute_sequence(). Each builds a throwaway sequence
    # (ad-hoc browser + close_session_after=True), delegates to Sequence__Runner,
    # then extracts exactly what the caller wanted out of the step results.
    # Caller sees a minimal flat schema in Swagger — no capture_config / sink
    # trees — and an equally minimal response (or raw image bytes).

    def quick_html(self, request: Schema__Quick__Html__Request) -> Schema__Quick__Html__Response:
        try:
            self.setup()
            steps = [dict(action = Enum__Step__Action.NAVIGATE.value ,
                           url        = str(request.url)              ,
                           wait_until = request.wait_until.value       )]
            click = str(request.click) if request.click else ''                         # osbot-fast-api's Pydantic bridge may auto-instantiate Safe_Str__Selector to a non-None empty value — only queue the click when the caller actually set a selector string
            if click:
                steps.append(dict(action = Enum__Step__Action.CLICK.value,
                                   selector = click                      ))
            steps.append(dict(action = Enum__Step__Action.GET_URL.value    ))
            steps.append(dict(action             = Enum__Step__Action.GET_CONTENT.value,
                              inline_in_response = True                                ))

            seq_request = self.quick_build_sequence_request(steps=steps, capture_config=Schema__Capture__Config(), timeout_ms=request.timeout_ms)
            seq_response = self.sequence_runner.execute(seq_request)
            self.quick_raise_on_failure(seq_response)

            final_url = Safe_Str__Url(str(request.url))                                 # Fallback if get_url somehow missing
            html      = ''
            for result in seq_response.step_results:
                if result.action == Enum__Step__Action.GET_URL and getattr(result, 'url', None):
                    final_url = Safe_Str__Url(str(result.url))
                if result.action == Enum__Step__Action.GET_CONTENT and getattr(result, 'content', None) is not None:
                    html = str(result.content)

            return Schema__Quick__Html__Response(url         = request.url                     ,
                                                  final_url   = final_url                       ,
                                                  html        = Safe_Str__Page__Content(html)   ,     # 10 MB cap; 64 KB Safe_Str__Text__Dangerous was too small for real pages
                                                  duration_ms = seq_response.total_duration_ms  ,
                                                  timings     = seq_response.timings            )     # Surface the same per-phase breakdown Sequence__Runner computed
        except HTTPException:
            raise                                                                       # Already a clean 4xx/5xx — let it through
        except Exception as error:
            raise HTTPException(502, self.quick_error_detail('quick_html', error))       # Rich detail with traceback — osbot-fast-api's Type_Safe wrapper would otherwise squash this to "{Type}: {msg}" with no stack

    def quick_screenshot(self, request: Schema__Quick__Screenshot__Request) -> Schema__Quick__Screenshot__Result:
        try:
            self.setup()
            steps = [dict(action = Enum__Step__Action.NAVIGATE.value ,
                           url        = str(request.url)              ,
                           wait_until = request.wait_until.value       )]
            click = str(request.click) if request.click else ''                         # Same truthy-check as quick_html — Pydantic bridge auto-instantiates Safe_Str__Selector
            if click:
                steps.append(dict(action = Enum__Step__Action.CLICK.value,
                                   selector = click                      ))
            screenshot_step = dict(action    = Enum__Step__Action.SCREENSHOT.value,
                                    full_page = bool(request.full_page)            )
            selector = str(request.selector) if request.selector else ''
            if selector:
                screenshot_step['selector'] = selector                                  # Element-only screenshot overrides full_page in Step__Executor
            steps.append(screenshot_step)

            capture_config = Schema__Capture__Config(screenshot = Schema__Artefact__Sink_Config(enabled = True                         ,     # INLINE sink so Step__Executor routes the PNG bytes into artefact.inline_b64 — we base64-decode below
                                                                                                 sink    = Enum__Artefact__Sink.INLINE))
            seq_request  = self.quick_build_sequence_request(steps=steps, capture_config=capture_config, timeout_ms=request.timeout_ms)
            seq_response = self.sequence_runner.execute(seq_request)
            self.quick_raise_on_failure(seq_response)

            for artefact in seq_response.artefacts:                                     # Find the screenshot we just captured
                if artefact.artefact_type == Enum__Artefact__Type.SCREENSHOT and artefact.inline_b64 is not None:
                    png_bytes = base64.b64decode(str(artefact.inline_b64))
                    return Schema__Quick__Screenshot__Result(png_bytes = png_bytes             ,
                                                              timings   = seq_response.timings  )     # Route emits these as X-*-Ms headers alongside the raw PNG body
            raise HTTPException(500, 'Screenshot artefact missing from sequence response')
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(502, self.quick_error_detail('quick_screenshot', error))

    def quick_build_sequence_request(self                                                 ,
                                      steps           : list                              ,
                                      capture_config  : Schema__Capture__Config            ,
                                      timeout_ms                                          = None
                                 ) -> Schema__Sequence__Request:
        if timeout_ms is not None and int(timeout_ms) > 0:                          # Swagger renders integer defaults as 0 — treat 0 as "unset" so every step keeps its own default timeout instead of timing out instantly
            for step in steps:
                step.setdefault('timeout_ms', int(timeout_ms))                      # Apply caller's timeout to every step that didn't already override
        return Schema__Sequence__Request(browser_config      = Schema__Browser__Config()                 ,
                                          capture_config      = capture_config                            ,
                                          sequence_config     = Schema__Sequence__Config(halt_on_error=True),
                                          steps               = steps                                      ,
                                          close_session_after = True                                       )

    def quick_raise_on_failure(self, seq_response: Schema__Sequence__Response) -> None:
        if seq_response.status == Enum__Sequence__Status.COMPLETED:                 # Happy path — every step passed
            return
        failed = next((r for r in seq_response.step_results if r.error_message), None)   # Surface the first failure's message
        if failed is not None:
            action = getattr(failed, 'action', None)
            action = action.value if action is not None and hasattr(action, 'value') else str(action)
            step_index = getattr(failed, 'step_index', None)
            detail = f'step[{step_index}] action={action} error={failed.error_message}'   # Include step index + action so callers know WHICH step blew up
        else:
            detail = f'sequence status={seq_response.status.value} (no per-step error_message)'
        raise HTTPException(502, f'Quick call failed: {detail}')

    def quick_error_detail(self, where: str, error: Exception) -> str:              # Format unexpected exceptions with a compact traceback so Swagger's 400/502 "detail" is actionable — otherwise osbot-fast-api's wrapper would squash this to just "{Type}: {msg}"
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        tb_text  = ''.join(tb_lines)[-1800:]                                        # Trim to the last ~1800 chars — AWS API Gateway caps detail size, and the tail frames are the most useful
        return f'{where} failed: {type(error).__name__}: {error}\n{tb_text}'

    # ─── Utility ──────────────────────────────────────────────────────────────

    def generate_trace_id(self) -> str:                                             # Short random hex; callers may supply their own
        return uuid.uuid4().hex[:8]
