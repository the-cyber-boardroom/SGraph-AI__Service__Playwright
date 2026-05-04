# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Step__Executor
#
# THE ONLY class (alongside Browser__Launcher) permitted to import from
# playwright.sync_api. Responsibility: one `execute_{action}` method per
# Enum__Step__Action value, each taking a Playwright `Page`, a typed step
# schema, and the capture_config; returning a Schema__Step__Result__* with
# duration + status + any artefact refs.
#
# Phase 2.9 first pass: NAVIGATE, CLICK, FILL, SCREENSHOT, GET_CONTENT, GET_URL.
# The remaining ten actions raise NotImplementedError with a clear "Phase 2.11"
# message — signposted TODOs for the next Step__Executor expansion.
#
# Error handling: each execute_* catches exceptions, times the step, populates
# error_message, and returns a FAILED result rather than raising — Sequence__Runner
# wants a uniform result shape regardless of outcome. PlaywrightTimeoutError is
# re-interpreted as a FAILED status with a descriptive message (not SKIPPED).
#
# Screenshot capture goes through Artefact__Writer.capture_screenshot(); this
# class never writes directly to a sink (spec §10: Artefact__Writer is the only
# class that writes to sinks).
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                                         import Any, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Page__Content                   import Safe_Str__Page__Content
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Content__Format                               import Enum__Content__Format
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Content                 import Schema__Step__Result__Get_Content
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Url                     import Schema__Step__Result__Get_Url
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click                                 import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Fill                                  import Schema__Step__Fill
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Content                           import Schema__Step__Get_Content
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Url                               import Schema__Step__Get_Url
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Evaluate                              import Schema__Step__Evaluate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate                              import Schema__Step__Navigate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Screenshot                            import Schema__Step__Screenshot
from sgraph_ai_service_playwright.service.Artefact__Writer                                          import Artefact__Writer


DEFERRED_MESSAGE = 'Deferred to Phase 2.11 — not in the Phase 2.9 first-pass subset.'


class Step__Executor(Type_Safe):

    artefact_writer : Artefact__Writer

    # ─── Dispatcher ────────────────────────────────────────────────────────────

    def execute(self                                                  ,
                page            : Any                                 ,                 # playwright.sync_api.Page — opaque here
                step            : Schema__Step__Base                  ,
                step_index      : int                                 ,
                capture_config  : Schema__Capture__Config
           ) -> Schema__Step__Result__Base:

        action = step.action
        if   action == Enum__Step__Action.NAVIGATE    : return self.execute_navigate    (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.CLICK       : return self.execute_click       (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.FILL        : return self.execute_fill        (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.SCREENSHOT  : return self.execute_screenshot  (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.GET_CONTENT : return self.execute_get_content (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.GET_URL     : return self.execute_get_url     (page, step, step_index, capture_config)
        elif action == Enum__Step__Action.EVALUATE    : return self.execute_evaluate    (page, step, step_index, capture_config)
        raise NotImplementedError(f'Step__Executor.execute({action.value}): {DEFERRED_MESSAGE}')

    # ─── First-pass action handlers ────────────────────────────────────────────

    def execute_navigate(self, page, step: Schema__Step__Navigate, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            page.goto(str(step.url), wait_until=str(step.wait_until), timeout=int(step.timeout_ms))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_click(self, page, step: Schema__Step__Click, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            page.click(str(step.selector)                     ,
                       button      = str(step.button)         ,
                       click_count = int(step.click_count)    ,
                       delay       = int(step.delay_ms)       ,
                       force       = bool(step.force)         ,
                       timeout     = int(step.timeout_ms)     )
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_fill(self, page, step: Schema__Step__Fill, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if step.clear_first:                                                        # Playwright `fill` clears by default; explicit for symmetry with Schema flag
                page.fill(str(step.selector), str(step.value), timeout=int(step.timeout_ms))
            else:
                page.locator(str(step.selector)).press_sequentially(str(step.value), timeout=int(step.timeout_ms))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_screenshot(self, page, step: Schema__Step__Screenshot, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if step.selector is not None:
                data = page.locator(str(step.selector)).screenshot(timeout=int(step.timeout_ms))
            else:
                data = page.screenshot(full_page=bool(step.full_page), timeout=int(step.timeout_ms))
            ref  = self.artefact_writer.capture_screenshot(data, capture_config.screenshot)
            return self.passed_result(step, step_index, started_ms, artefacts=self.filter_refs([ref]))
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_content(self, page, step: Schema__Step__Get_Content, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Get_Content:
        started_ms = self.now_ms()
        try:
            if step.content_format == Enum__Content__Format.TEXT:                       # innerText (rendered text)
                if step.selector is not None : content = page.locator(str(step.selector)).inner_text(timeout=int(step.timeout_ms))
                else                         : content = page.locator('body').inner_text(timeout=int(step.timeout_ms))
                content_type = 'text/plain'
            else:                                                                       # HTML (innerHTML or full page content)
                if step.selector is not None : content = page.locator(str(step.selector)).inner_html(timeout=int(step.timeout_ms))
                else                         : content = page.content()
                content_type = 'text/html'

            artefacts : List[Schema__Artefact__Ref] = []
            if not step.inline_in_response:                                             # Route through sink rather than embedding in response
                ref = self.artefact_writer.capture_page_content(content.encode('utf-8'), capture_config.page_content)
                artefacts = self.filter_refs([ref])

            duration_ms = self.now_ms() - started_ms
            return Schema__Step__Result__Get_Content(step_id        = self.resolve_id(step, step_index)       ,
                                                     step_index     = step_index                              ,
                                                     action         = step.action                             ,
                                                     status         = Enum__Step__Status.PASSED               ,
                                                     duration_ms    = duration_ms                             ,
                                                     artefacts      = artefacts                               ,
                                                     content        = Safe_Str__Page__Content(content)        ,     # 10 MB cap — real pages routinely blow the 64 KB Safe_Str__Text__Dangerous default
                                                     content_format = step.content_format                     ,
                                                     content_type   = content_type                            )
        except Exception as error:
            base = self.failed_result(step, step_index, started_ms, error)
            return Schema__Step__Result__Get_Content(step_id        = base.step_id                            ,
                                                     step_index     = base.step_index                         ,
                                                     action         = base.action                             ,
                                                     status         = base.status                             ,
                                                     duration_ms    = base.duration_ms                        ,
                                                     error_message  = base.error_message                      ,
                                                     artefacts      = base.artefacts                          ,
                                                     content        = Safe_Str__Page__Content('')             ,
                                                     content_format = step.content_format                     ,
                                                     content_type   = 'text/html'                             )

    def execute_get_url(self, page, step: Schema__Step__Get_Url, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Get_Url:
        started_ms = self.now_ms()
        try:
            url = page.url
            return Schema__Step__Result__Get_Url(step_id     = self.resolve_id(step, step_index) ,
                                                 step_index  = step_index                        ,
                                                 action      = step.action                       ,
                                                 status      = Enum__Step__Status.PASSED         ,
                                                 duration_ms = self.now_ms() - started_ms        ,
                                                 url         = Safe_Str__Url(url)                )
        except Exception as error:
            base = self.failed_result(step, step_index, started_ms, error)
            return Schema__Step__Result__Get_Url(step_id       = base.step_id       ,
                                                 step_index    = base.step_index    ,
                                                 action        = base.action        ,
                                                 status        = base.status        ,
                                                 duration_ms   = base.duration_ms   ,
                                                 error_message = base.error_message ,
                                                 artefacts     = base.artefacts     ,
                                                 url           = Safe_Str__Url('http://error.invalid/'))

    def execute_evaluate(self, page, step: Schema__Step__Evaluate, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            page.evaluate(str(step.expression))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    # ─── Deferred action handlers — Phase 2.11 ─────────────────────────────────

    def execute_press         (self, page, step, step_index, capture_config): raise NotImplementedError(f'PRESS: {DEFERRED_MESSAGE}')
    def execute_select        (self, page, step, step_index, capture_config): raise NotImplementedError(f'SELECT: {DEFERRED_MESSAGE}')
    def execute_hover         (self, page, step, step_index, capture_config): raise NotImplementedError(f'HOVER: {DEFERRED_MESSAGE}')
    def execute_scroll        (self, page, step, step_index, capture_config): raise NotImplementedError(f'SCROLL: {DEFERRED_MESSAGE}')
    def execute_wait_for      (self, page, step, step_index, capture_config): raise NotImplementedError(f'WAIT_FOR: {DEFERRED_MESSAGE}')
    def execute_video_start   (self, page, step, step_index, capture_config): raise NotImplementedError(f'VIDEO_START: {DEFERRED_MESSAGE} (context-level API)')
    def execute_video_stop    (self, page, step, step_index, capture_config): raise NotImplementedError(f'VIDEO_STOP: {DEFERRED_MESSAGE} (context-level API)')
    def execute_dispatch_event(self, page, step, step_index, capture_config): raise NotImplementedError(f'DISPATCH_EVENT: {DEFERRED_MESSAGE}')
    def execute_set_viewport  (self, page, step, step_index, capture_config): raise NotImplementedError(f'SET_VIEWPORT: {DEFERRED_MESSAGE}')

    # ─── Result constructors ───────────────────────────────────────────────────

    def passed_result(self                                          ,
                      step       : Schema__Step__Base               ,
                      step_index : int                              ,
                      started_ms : int                              ,
                      artefacts  : List[Schema__Artefact__Ref] = None
                 ) -> Schema__Step__Result__Base:
        return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                          step_index  = step_index                        ,
                                          action      = step.action                       ,
                                          status      = Enum__Step__Status.PASSED         ,
                                          duration_ms = self.now_ms() - started_ms        ,
                                          artefacts   = artefacts or []                   )

    def failed_result(self                                          ,
                      step       : Schema__Step__Base               ,
                      step_index : int                              ,
                      started_ms : int                              ,
                      error      : Exception
                 ) -> Schema__Step__Result__Base:
        return Schema__Step__Result__Base(step_id       = self.resolve_id(step, step_index) ,
                                          step_index    = step_index                        ,
                                          action        = step.action                       ,
                                          status        = Enum__Step__Status.FAILED         ,
                                          duration_ms   = self.now_ms() - started_ms        ,
                                          error_message = Safe_Str__Text(str(error)[:1000]) ,
                                          artefacts     = []                                )

    def resolve_id(self, step: Schema__Step__Base, step_index: int) -> Step_Id:         # Fall back to the ordinal when caller didn't provide id
        return step.id if step.id is not None else Step_Id(str(step_index))

    def filter_refs(self, refs: List[Schema__Artefact__Ref]) -> List[Schema__Artefact__Ref]:
        return [r for r in refs if r is not None]                                       # Drop None refs (sink_config.enabled=False)

    def now_ms(self) -> int:                                                            # Single wall-clock seam — tests subclass to freeze time
        return int(time.time() * 1000)
