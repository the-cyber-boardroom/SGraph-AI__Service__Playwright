# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Playwright__Service (v0.1.24 — stateless surface)
#
# Thin orchestrator. Routes contain zero logic; they delegate here. Every
# mutating request builds a throwaway sequence and runs it via
# Sequence__Runner — no Session__Manager, no Action__Runner, no quick-* adapters.
#
# Health surface (unchanged):
#   • get_service_info()   → Schema__Service__Info           (/health/info)
#   • get_health()         → Schema__Health                  (/health/status)
#   • get_capabilities()   → Schema__Service__Capabilities   (/health/capabilities)
#
# Stateless one-shot surface (v0.1.24):
#   • browser_navigate / browser_click / browser_fill   → Schema__Browser__One_Shot__Response
#   • browser_get_content / browser_get_url             → Schema__Browser__One_Shot__Response
#   • browser_screenshot                                → Schema__Browser__Screenshot__Result
#     (raw PNG + timings; route emits X-*-Ms headers alongside the bytes)
#
# Sequence surface (unchanged URL; schema simplified):
#   • execute_sequence()   → Schema__Sequence__Response      (POST /sequence/execute)
#
# setup() is idempotent; it primes Capability__Detector and shares deps into
# Sequence__Runner.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import traceback
import uuid

from fastapi                                                                            import HTTPException
from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Sink_Config        import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Screenshot__Format                import Enum__Screenshot__Format
from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Batch__Request import Schema__Screenshot__Batch__Request
from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Batch__Response import Schema__Screenshot__Batch__Response
from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Request        import Schema__Screenshot__Request
from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Response       import Schema__Screenshot__Response
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Click__Request       import Schema__Browser__Click__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Fill__Request        import Schema__Browser__Fill__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Get_Content__Request import Schema__Browser__Get_Content__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Get_Url__Request     import Schema__Browser__Get_Url__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Navigate__Request    import Schema__Browser__Navigate__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__One_Shot__Response   import Schema__Browser__One_Shot__Response
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Screenshot__Request  import Schema__Browser__Screenshot__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Screenshot__Result   import Schema__Browser__Screenshot__Result
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config               import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                    import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type                    import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                  import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                      import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id     import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Page__Content       import Safe_Str__Page__Content
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config             import Schema__Sequence__Config
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request            import Schema__Sequence__Request
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Response           import Schema__Sequence__Response
from sgraph_ai_service_playwright.schemas.service.Schema__Health                        import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities         import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                 import Schema__Service__Info
from sgraph_ai_service_playwright.metrics.Metrics__Collector                            import Metrics__Collector
from sgraph_ai_service_playwright.service.Browser__Launcher                             import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                          import Capability__Detector
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config               import Schema__Browser__Config
from sgraph_ai_service_playwright.service.Credentials__Loader                           import Credentials__Loader
from sgraph_ai_service_playwright.service.JS__Expression__Allowlist                     import JS__Expression__Allowlist
from sgraph_ai_service_playwright.service.Request__Validator                            import Request__Validator
from sgraph_ai_service_playwright.service.Sequence__Runner                              import Sequence__Runner


class Playwright__Service(Type_Safe):

    capability_detector : Capability__Detector
    browser_launcher    : Browser__Launcher
    metrics_collector   : Metrics__Collector
    request_validator   : Request__Validator
    credentials_loader  : Credentials__Loader
    sequence_runner     : Sequence__Runner

    def setup(self) -> 'Playwright__Service':
        if self.capability_detector.detected_target is None:
            self.capability_detector.detect()
        self.sequence_runner.capability_detector = self.capability_detector
        self.sequence_runner.request_validator   = self.request_validator
        self.sequence_runner.browser_launcher    = self.browser_launcher
        self.sequence_runner.credentials_loader  = self.credentials_loader
        return self

    def _screenshot_runner(self) -> Sequence__Runner:                               # Dedicated runner for the screenshot surface — JS allowlist bypassed (each call is an isolated ephemeral session)
        validator = Request__Validator(js_allowlist=JS__Expression__Allowlist(allow_all=True))
        runner    = Sequence__Runner(capability_detector = self.capability_detector  ,
                                     request_validator   = validator                 ,
                                     browser_launcher    = self.browser_launcher     ,
                                     credentials_loader  = self.credentials_loader   )
        return runner

    # ─── Health surface ───────────────────────────────────────────────────────

    def get_service_info(self) -> Schema__Service__Info:
        self.setup()
        return self.capability_detector.service_info()

    def get_capabilities(self) -> Schema__Service__Capabilities:
        self.setup()
        return self.capability_detector.capabilities()

    def get_health(self) -> Schema__Health:
        checks  = [self.browser_launcher   .healthcheck()        ,
                   self.capability_detector.connectivity_check() ]
        healthy = all(c.healthy for c in checks)
        return Schema__Health(healthy = healthy ,
                              checks  = checks  )

    # ─── Sequence surface (unchanged URL) ─────────────────────────────────────

    def _run_sequence(self, request: Schema__Sequence__Request) -> Schema__Sequence__Response:
        return self._run_sequence_via(request, self.sequence_runner)

    def _run_sequence_via(self, request: Schema__Sequence__Request, runner: Sequence__Runner) -> Schema__Sequence__Response:
        """Dispatch a sequence through the given runner.

        Playwright's sync API raises if called from inside an asyncio event loop
        (Lambda / Lambda Web Adapter runs the ASGI app inside asyncio.run()). Detect this and
        dispatch to a fresh ThreadPoolExecutor thread that has no running loop.
        On EC2 / local the try block raises RuntimeError immediately and we call
        execute() directly — zero overhead on the fast path.
        """
        import asyncio
        try:
            asyncio.get_running_loop()
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:                          # Fresh thread has no running event loop
                return pool.submit(runner.execute, request).result()
        except RuntimeError:
            return runner.execute(request)                                           # No loop running — EC2 / local, call directly

    def execute_sequence(self, request: Schema__Sequence__Request) -> Schema__Sequence__Response:
        self.setup()
        return self._run_sequence(request)

    # ─── Simple screenshot surface (/screenshot, /screenshot/batch) ─────────────

    def screenshot_simple(self, request: Schema__Screenshot__Request) -> Schema__Screenshot__Response:
        try:
            self.setup()
            steps = [self.build_navigate_step(request.url, None, None)]
            if request.javascript:
                js = str(request.javascript)
                if js:
                    steps.append(dict(action=Enum__Step__Action.EVALUATE.value, expression=js))
            if request.click:
                sel = str(request.click)
                if sel:
                    steps.append(dict(action=Enum__Step__Action.CLICK.value, selector=sel))
            if request.format == Enum__Screenshot__Format.HTML:
                steps.append(dict(action=Enum__Step__Action.GET_CONTENT.value, inline_in_response=True))
                capture_config = Schema__Capture__Config()
            else:
                steps.append(dict(action=Enum__Step__Action.SCREENSHOT.value, full_page=bool(request.full_page)))
                capture_config = Schema__Capture__Config(screenshot=Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE))
            seq_request  = self.build_sequence_request(steps=steps, browser_config=None, capture_config=capture_config)
            seq_response = self._run_sequence_via(seq_request, self._screenshot_runner())
            self.raise_on_sequence_failure(seq_response)
            if request.format == Enum__Screenshot__Format.HTML:
                html = next((str(r.content) for r in seq_response.step_results
                             if r.action == Enum__Step__Action.GET_CONTENT and getattr(r, 'content', None)), '')
                return Schema__Screenshot__Response(url        = request.url                      ,
                                                     html       = Safe_Str__Page__Content(html)   ,
                                                     duration_ms= seq_response.total_duration_ms  ,
                                                     trace_id   = seq_response.trace_id           )
            for artefact in seq_response.artefacts:
                if artefact.artefact_type == Enum__Artefact__Type.SCREENSHOT and artefact.inline_b64 is not None:
                    return Schema__Screenshot__Response(url           = request.url                     ,
                                                         screenshot_b64= str(artefact.inline_b64)       ,
                                                         duration_ms   = seq_response.total_duration_ms ,
                                                         trace_id      = seq_response.trace_id          )
            raise HTTPException(500, 'Screenshot artefact missing from sequence response')
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(502, self.error_detail('screenshot_simple', error))

    def screenshot_batch(self, request: Schema__Screenshot__Batch__Request) -> Schema__Screenshot__Batch__Response:
        try:
            self.setup()
            t_start = self.now_ms()
            if request.items:
                screenshots = [self.screenshot_simple(item) for item in request.items]
                return Schema__Screenshot__Batch__Response(screenshots = screenshots,
                                                            duration_ms = self.now_ms() - t_start)
            if request.steps:
                return self._screenshot_steps(request.steps, request.screenshot_per_step)
            return Schema__Screenshot__Batch__Response()
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(502, self.error_detail('screenshot_batch', error))

    def _screenshot_steps(self, steps, screenshot_per_step: bool) -> Schema__Screenshot__Batch__Response:
        seq_steps = []
        n         = len(steps)
        for i, step in enumerate(steps):
            seq_steps.append(self.build_navigate_step(step.url, None, None))
            if step.javascript:
                js = str(step.javascript)
                if js:
                    seq_steps.append(dict(action=Enum__Step__Action.EVALUATE.value, expression=js))
            if step.click:
                sel = str(step.click)
                if sel:
                    seq_steps.append(dict(action=Enum__Step__Action.CLICK.value, selector=sel))
            if screenshot_per_step or i == n - 1:
                seq_steps.append(dict(action=Enum__Step__Action.SCREENSHOT.value, full_page=False))
        capture_config = Schema__Capture__Config(screenshot=Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE))
        seq_request    = self.build_sequence_request(steps=seq_steps, browser_config=None, capture_config=capture_config)
        seq_response   = self._run_sequence_via(seq_request, self._screenshot_runner())
        self.raise_on_sequence_failure(seq_response)
        screenshots = [Schema__Screenshot__Response(screenshot_b64=str(a.inline_b64),
                                                     duration_ms   =seq_response.total_duration_ms)
                       for a in seq_response.artefacts
                       if a.artefact_type == Enum__Artefact__Type.SCREENSHOT and a.inline_b64 is not None]
        return Schema__Screenshot__Batch__Response(screenshots = screenshots,
                                                    duration_ms = seq_response.total_duration_ms)

    def now_ms(self) -> int:
        import time
        return int(time.time() * 1000)

    # ─── One-shot /browser/* surface (v0.1.24) ────────────────────────────────
    # Each method builds a tiny throwaway sequence, runs it through
    # Sequence__Runner (fresh Chromium per call + guaranteed teardown), and
    # extracts the one result the caller asked for.

    def _with_viewport(self, browser_config, viewport):                                # Merge top-level viewport shorthand into browser_config
        if viewport is None:
            return browser_config
        cfg = browser_config if browser_config is not None else Schema__Browser__Config()
        cfg.viewport = viewport
        return cfg

    def browser_navigate(self, request: Schema__Browser__Navigate__Request) -> Schema__Browser__One_Shot__Response:
        steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms),
                  dict(action = Enum__Step__Action.GET_URL.value)]
        return self.run_one_shot(steps, self._with_viewport(request.browser_config, request.viewport), request.url, request.timeout_ms, endpoint='navigate')

    def browser_click(self, request: Schema__Browser__Click__Request) -> Schema__Browser__One_Shot__Response:
        steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms),
                  dict(action = Enum__Step__Action.CLICK.value, selector = str(request.selector)),
                  dict(action = Enum__Step__Action.GET_URL.value)]
        return self.run_one_shot(steps, request.browser_config, request.url, request.timeout_ms, endpoint='click')

    def browser_fill(self, request: Schema__Browser__Fill__Request) -> Schema__Browser__One_Shot__Response:
        steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms),
                  dict(action = Enum__Step__Action.FILL.value, selector = str(request.selector), value = str(request.value)),
                  dict(action = Enum__Step__Action.GET_URL.value)]
        return self.run_one_shot(steps, request.browser_config, request.url, request.timeout_ms, endpoint='fill')

    def browser_get_content(self, request: Schema__Browser__Get_Content__Request) -> Schema__Browser__One_Shot__Response:
        steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms)]
        self.maybe_append_click(steps, request.click)
        steps.append(dict(action = Enum__Step__Action.GET_URL.value))
        steps.append(dict(action = Enum__Step__Action.GET_CONTENT.value, inline_in_response = True))
        return self.run_one_shot(steps, request.browser_config, request.url, request.timeout_ms, endpoint='get-content')

    def browser_get_url(self, request: Schema__Browser__Get_Url__Request) -> Schema__Browser__One_Shot__Response:
        steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms)]
        self.maybe_append_click(steps, request.click)
        steps.append(dict(action = Enum__Step__Action.GET_URL.value))
        return self.run_one_shot(steps, request.browser_config, request.url, request.timeout_ms, endpoint='get-url')

    def browser_screenshot(self, request: Schema__Browser__Screenshot__Request) -> Schema__Browser__Screenshot__Result:
        try:
            self.setup()
            steps = [self.build_navigate_step(request.url, request.wait_until, request.timeout_ms)]
            self.maybe_append_click(steps, request.click)
            shot_step = dict(action = Enum__Step__Action.SCREENSHOT.value, full_page = bool(request.full_page))
            if request.selector:
                shot_step['selector'] = str(request.selector)                       # Element-only shot overrides full_page in Step__Executor
            steps.append(shot_step)

            capture_config = Schema__Capture__Config(screenshot = Schema__Artefact__Sink_Config(enabled = True                         ,
                                                                                                 sink    = Enum__Artefact__Sink.INLINE))
            seq_request  = self.build_sequence_request(steps=steps, browser_config=self._with_viewport(request.browser_config, request.viewport), capture_config=capture_config, timeout_ms=request.timeout_ms)
            seq_response = self._run_sequence(seq_request)
            self.raise_on_sequence_failure(seq_response)

            for artefact in seq_response.artefacts:
                if artefact.artefact_type == Enum__Artefact__Type.SCREENSHOT and artefact.inline_b64 is not None:
                    png_bytes = base64.b64decode(str(artefact.inline_b64))
                    result    = Schema__Browser__Screenshot__Result(png_bytes = png_bytes            ,
                                                                     timings   = seq_response.timings )
                    self.metrics_collector.record_timings(seq_response.timings, 'screenshot', '2xx')
                    return result
            raise HTTPException(500, 'Screenshot artefact missing from sequence response')
        except HTTPException:
            self.metrics_collector.record_timings(None, 'screenshot', '5xx')
            raise
        except Exception as error:
            self.metrics_collector.record_timings(None, 'screenshot', '5xx')
            raise HTTPException(502, self.error_detail('browser_screenshot', error))

    # ─── One-shot plumbing ────────────────────────────────────────────────────

    def run_one_shot(self, steps: list, browser_config, url, timeout_ms,
                     endpoint: str = 'unknown') -> Schema__Browser__One_Shot__Response:
        try:
            self.setup()
            seq_request  = self.build_sequence_request(steps=steps, browser_config=browser_config, capture_config=Schema__Capture__Config(), timeout_ms=timeout_ms)
            seq_response = self._run_sequence(seq_request)
            self.raise_on_sequence_failure(seq_response)

            final_url : Safe_Str__Url = Safe_Str__Url(str(url))                      # Fallback if GET_URL somehow missing
            html      : str           = None
            for result in seq_response.step_results:
                if result.action == Enum__Step__Action.GET_URL and getattr(result, 'url', None):
                    final_url = Safe_Str__Url(str(result.url))
                if result.action == Enum__Step__Action.GET_CONTENT and getattr(result, 'content', None) is not None:
                    html = str(result.content)

            response = Schema__Browser__One_Shot__Response(url         = url                                          ,
                                                            final_url   = final_url                                    ,
                                                            html        = Safe_Str__Page__Content(html) if html is not None else None,
                                                            trace_id    = seq_response.trace_id                        ,
                                                            duration_ms = seq_response.total_duration_ms               ,
                                                            timings     = seq_response.timings                         )
            self.metrics_collector.record_timings(seq_response.timings, endpoint, '2xx')
            return response
        except HTTPException:
            self.metrics_collector.record_timings(None, endpoint, '5xx')
            raise
        except Exception as error:
            self.metrics_collector.record_timings(None, endpoint, '5xx')
            raise HTTPException(502, self.error_detail('browser_one_shot', error))

    def build_navigate_step(self, url, wait_until, timeout_ms) -> dict:
        from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State import Enum__Wait__State
        wait = (wait_until or Enum__Wait__State.LOAD).value
        step = dict(action = Enum__Step__Action.NAVIGATE.value, url = str(url), wait_until = wait)
        if timeout_ms is not None and int(timeout_ms) > 0:
            step['timeout_ms'] = int(timeout_ms)
        return step

    def maybe_append_click(self, steps: list, click_selector) -> None:              # Swagger/Pydantic bridge can auto-materialise Safe_Str__Selector to empty — only queue on truthy value
        if not click_selector:
            return
        selector = str(click_selector)
        if not selector:
            return
        steps.append(dict(action = Enum__Step__Action.CLICK.value, selector = selector))

    def build_sequence_request(self                                                ,
                                steps          : list                              ,
                                browser_config                                     ,
                                capture_config : Schema__Capture__Config           ,
                                timeout_ms                                         = None
                           ) -> Schema__Sequence__Request:
        if timeout_ms is not None and int(timeout_ms) > 0:                          # Swagger renders integer defaults as 0 — treat 0 as "unset"
            for step in steps:
                step.setdefault('timeout_ms', int(timeout_ms))
        return Schema__Sequence__Request(browser_config  = browser_config                                  ,
                                          capture_config  = capture_config                                  ,
                                          sequence_config = Schema__Sequence__Config(halt_on_error=True)    ,
                                          steps           = steps                                           )

    def raise_on_sequence_failure(self, seq_response: Schema__Sequence__Response) -> None:
        if seq_response.status == Enum__Sequence__Status.COMPLETED:
            return
        failed = next((r for r in seq_response.step_results if r.error_message), None)
        if failed is not None:
            action = getattr(failed, 'action', None)
            action = action.value if action is not None and hasattr(action, 'value') else str(action)
            step_index = getattr(failed, 'step_index', None)
            detail = f'step[{step_index}] action={action} error={failed.error_message}'
        else:
            detail = f'sequence status={seq_response.status.value} (no per-step error_message)'
        raise HTTPException(502, f'Browser one-shot failed: {detail}')

    def error_detail(self, where: str, error: Exception) -> str:                    # Format unexpected exceptions with a compact traceback — otherwise osbot-fast-api's wrapper squashes to just "{Type}: {msg}"
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        tb_text  = ''.join(tb_lines)[-1800:]
        return f'{where} failed: {type(error).__name__}: {error}\n{tb_text}'

    # ─── Utility ──────────────────────────────────────────────────────────────

    def generate_trace_id(self) -> str:
        return uuid.uuid4().hex[:8]
