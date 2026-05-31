# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Step__Executor
#
# THE ONLY class (alongside Browser__Launcher) permitted to import from
# playwright.sync_api. Responsibility: one `execute_{action}` method per
# Enum__Step__Action value, each taking a Playwright `Page`, a typed step
# schema, and the capture_config; returning a Schema__Step__Result__* with
# duration + status + any artefact refs.
#
# Implemented verbs: NAVIGATE, CLICK, FILL, SCREENSHOT, GET_CONTENT, GET_URL,
# EVALUATE, WAIT_FOR, PRESS, SELECT, HOVER, SCROLL, SET_VIEWPORT, DISPATCH_EVENT.
# Recording (video) is context-level via capture_config.video, not a per-step verb.
# Dispatch is table-driven (ACTION_HANDLERS); an unmapped verb returns a per-step
# FAILED result rather than raising — Sequence__Runner also wraps execution as a
# second guarantee that no single step can abort a whole sequence.
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

from typing                                                                                         import Any, List

from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Page__Content                   import Safe_Str__Page__Content
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                               import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                         import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Evaluate                    import Schema__Step__Result__Evaluate
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Content                 import Schema__Step__Result__Get_Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url                     import Schema__Step__Result__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Click                                 import Schema__Step__Click
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Fill                                  import Schema__Step__Fill
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Type                               import Enum__Artefact__Type
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_A11y_Tree                         import Schema__Step__Get_A11y_Tree
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Console_Tail                      import Schema__Step__Get_Console_Tail
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Content                           import Schema__Step__Get_Content
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Dom_Tree                          import Schema__Step__Get_Dom_Tree
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Html                              import Schema__Step__Get_Html
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Network_Failures                  import Schema__Step__Get_Network_Failures
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Pdf                               import Schema__Step__Get_Pdf
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Text                              import Schema__Step__Get_Text
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Url                               import Schema__Step__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Evaluate                              import Schema__Step__Evaluate
from sg_compute_specs.playwright.core.service.Page__Listeners__Buffer                                   import buffer_from_page
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                              import Schema__Step__Navigate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Screenshot                            import Schema__Step__Screenshot
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Wait                                  import Schema__Step__Wait
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Wait_For                              import Schema__Step__Wait_For
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Press                                 import Schema__Step__Press
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Select                                import Schema__Step__Select
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Hover                                 import Schema__Step__Hover
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Scroll                                import Schema__Step__Scroll
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Set_Viewport                          import Schema__Step__Set_Viewport
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Dispatch_Event                        import Schema__Step__Dispatch_Event
from sg_compute_specs.playwright.core.service.Step__Executor__Base                                       import ACTION_HANDLERS, Step__Executor__Base

__all__ = ['ACTION_HANDLERS', 'Step__Executor']                                         # ACTION_HANDLERS re-exported from the base for callers that import it from here


class Step__Executor(Step__Executor__Base):                                             # Sync engine. Engine-neutral helpers live in Step__Executor__Base.

    # ─── Dispatcher ────────────────────────────────────────────────────────────

    def execute(self                                                  ,
                page            : Any                                 ,                 # playwright.sync_api.Page — opaque here
                step            : Schema__Step__Base                  ,
                step_index      : int                                 ,
                capture_config  : Schema__Capture__Config
           ) -> Schema__Step__Result__Base:

        started_ms = self.now_ms()
        handler    = self.handler_name(step)
        if handler is None:                                                             # Unknown / unsupported verb → clean per-step FAILED, never a crash
            return self.failed_result(step, step_index, started_ms,
                                      NotImplementedError(f'Unsupported action: {step.action.value}'))
        return getattr(self, handler)(page, step, step_index, capture_config)

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
            if step.viewport is not None:                                                       # FR-7 — set viewport before snapping (shorthand for a preceding set_viewport step)
                page.set_viewport_size({'width' : int(step.viewport.width) ,
                                        'height': int(step.viewport.height)})
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
                                                 url         = Safe_Str__Url__Permissive(url)    )    # Permissive: vault URLs etc. carry ':' in fragment — BUG-1
        except Exception as error:
            base = self.failed_result(step, step_index, started_ms, error)
            return Schema__Step__Result__Get_Url(step_id       = base.step_id       ,
                                                 step_index    = base.step_index    ,
                                                 action        = base.action        ,
                                                 status        = base.status        ,
                                                 duration_ms   = base.duration_ms   ,
                                                 error_message = base.error_message ,
                                                 error_type    = base.error_type    ,
                                                 artefacts     = base.artefacts     ,
                                                 url           = Safe_Str__Url__Permissive('http://error.invalid/'))

    def execute_evaluate(self, page, step: Schema__Step__Evaluate, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Evaluate:
        started_ms = self.now_ms()
        try:
            raw_value   = page.evaluate(str(step.expression))                                   # FR-5a — surface the return value (was discarded). Allowlist still applies upstream; only allow-listed reads reach here.
            return_type = self.classify_eval_return(raw_value)
            return Schema__Step__Result__Evaluate(step_id      = self.resolve_id(step, step_index) ,
                                                  step_index   = step_index                        ,
                                                  action       = step.action                       ,
                                                  status       = Enum__Step__Status.PASSED         ,
                                                  duration_ms  = self.now_ms() - started_ms        ,
                                                  artefacts    = []                                ,
                                                  return_value = raw_value                         ,    # JSON-serialisable (allowlist limits to constant reads → safe shapes)
                                                  return_type  = return_type                       )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)                          # Base result — return_value/return_type stay None (now lifted-to-base optional)

    def classify_eval_return(self, value) -> Enum__Evaluate__Return_Type:                           # FR-5a — map raw eval value → return-type enum the response carries
        if isinstance(value, bool):                                                                 # bool is a subclass of int — check first
            return Enum__Evaluate__Return_Type.BOOLEAN
        if isinstance(value, (int, float)):
            return Enum__Evaluate__Return_Type.NUMBER
        if isinstance(value, str):
            return Enum__Evaluate__Return_Type.STRING
        return Enum__Evaluate__Return_Type.JSON                                                     # dict / list / None / anything else → opaque JSON

    # ─── Interaction / wait handlers ───────────────────────────────────────────

    def execute_wait_for(self, page, step: Schema__Step__Wait_For, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if   step.function        is not None:                                      # FR-1c — wait for a JS predicate to return truthy. Allowlist already checked upstream in Request__Validator
                page.wait_for_function(str(step.function), timeout=int(step.timeout_ms))
            elif step.network_idle_ms is not None:                                      # FR-1d — wait until N ms have passed with no in-flight requests
                self._wait_for_network_idle(page, int(step.network_idle_ms), int(step.timeout_ms))
            elif step.text        is not None:                                          # FR-1a — wait for visible text. When `selector` is also set, scope to that subtree
                root   = page.locator(str(step.selector)) if step.selector is not None else page
                locator = root.get_by_text(str(step.text))
                locator.wait_for(state='visible', timeout=int(step.timeout_ms))
            elif step.selector    is not None:                                          # Wait for a selector — state depends on flags
                if   bool(step.selector_gone): state = 'detached'                       # FR-1b — wait until selector leaves the DOM
                elif bool(step.visible)      : state = 'visible'
                else                         : state = 'attached'
                page.wait_for_selector(str(step.selector), state=state, timeout=int(step.timeout_ms))
            elif step.url_pattern is not None:                                          # Wait for the URL to match
                page.wait_for_url(str(step.url_pattern), timeout=int(step.timeout_ms))
            elif step.state       is not None:                                          # Wait for a page load state (load / domcontentloaded / networkidle)
                page.wait_for_load_state(str(step.state), timeout=int(step.timeout_ms))
            else:
                page.wait_for_load_state(timeout=int(step.timeout_ms))                  # Default: wait for 'load'
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_wait(self, page, step: Schema__Step__Wait, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:  # FR-4 — plain fixed-duration pause (explicit, intentional; not the blind-wait anti-pattern that wait_for replaces)
        started_ms = self.now_ms()
        try:
            page.wait_for_timeout(int(step.duration_ms))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_press(self, page, step: Schema__Step__Press, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if step.selector is not None:
                page.press(str(step.selector), str(step.key), timeout=int(step.timeout_ms))
            else:
                page.keyboard.press(str(step.key))                                      # Press on the active element
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_select(self, page, step: Schema__Step__Select, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            values = [str(v) for v in step.values]                                      # Multi-select supported
            page.select_option(str(step.selector), values, timeout=int(step.timeout_ms))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_hover(self, page, step: Schema__Step__Hover, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            page.hover(str(step.selector), timeout=int(step.timeout_ms))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_scroll(self, page, step: Schema__Step__Scroll, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if step.selector is not None:                                               # Scroll a specific element into view
                page.locator(str(step.selector)).scroll_into_view_if_needed(timeout=int(step.timeout_ms))
            else:                                                                       # Scroll the viewport by (x, y) pixels
                page.mouse.wheel(int(step.x), int(step.y))
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_set_viewport(self, page, step: Schema__Step__Set_Viewport, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            page.set_viewport_size({'width' : int(step.viewport.width) ,
                                    'height': int(step.viewport.height)})
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_dispatch_event(self, page, step: Schema__Step__Dispatch_Event, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            event_init = {str(k): str(v) for k, v in step.event_init.items()} if step.event_init else None
            page.dispatch_event(str(step.selector), str(step.event_type),
                                event_init = event_init           ,
                                timeout    = int(step.timeout_ms) )
            return self.passed_result(step, step_index, started_ms)
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    # ─── Φ3 — DOM-read verbs (FR-2) + a11y (FR-5b) + PDF (FR-5d) ───────────────

    def execute_get_text(self, page, step: Schema__Step__Get_Text, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            locator = page.locator(str(step.selector)) if step.selector is not None else page.locator('body')
            text    = locator.inner_text(timeout=int(step.timeout_ms))

            artefacts : List[Schema__Artefact__Ref] = []
            if not step.inline_in_response:
                ref = self.artefact_writer.capture_page_content(text.encode('utf-8'), capture_config.page_content)
                artefacts = self.filter_refs([ref])

            return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                              step_index  = step_index                        ,
                                              action      = step.action                       ,
                                              status      = Enum__Step__Status.PASSED         ,
                                              duration_ms = self.now_ms() - started_ms        ,
                                              artefacts   = artefacts                         ,
                                              text        = Safe_Str__Page__Content(text)     )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_html(self, page, step: Schema__Step__Get_Html, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            if step.selector is not None:                                                       # outerHTML of the selector
                html = page.locator(str(step.selector)).evaluate('el => el.outerHTML', timeout=int(step.timeout_ms))
            else:
                html = page.content()                                                           # Full document — already includes <html>…</html>

            artefacts : List[Schema__Artefact__Ref] = []
            if not step.inline_in_response:
                ref = self.artefact_writer.capture_page_content(html.encode('utf-8'), capture_config.page_content)
                artefacts = self.filter_refs([ref])

            return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                              step_index  = step_index                        ,
                                              action      = step.action                       ,
                                              status      = Enum__Step__Status.PASSED         ,
                                              duration_ms = self.now_ms() - started_ms        ,
                                              artefacts   = artefacts                         ,
                                              html        = Safe_Str__Page__Content(html)     )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_dom_tree(self, page, step: Schema__Step__Get_Dom_Tree, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            args = {'rootSelector'    : str(step.root_selector) if step.root_selector is not None else None,
                    'maxDepth'        : int(step.max_depth)                                                ,
                    'includeInvisible': bool(step.include_invisible)                                       }
            tree = page.evaluate(self.DOM_TREE_JS, args)                                        # Built-in introspection — bypasses the JS allowlist (not user-supplied)
            return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                              step_index  = step_index                        ,
                                              action      = step.action                       ,
                                              status      = Enum__Step__Status.PASSED         ,
                                              duration_ms = self.now_ms() - started_ms        ,
                                              artefacts   = []                                ,
                                              dom_tree    = tree                              )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_a11y_tree(self, page, step: Schema__Step__Get_A11y_Tree, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            # page.accessibility was removed in Playwright 1.49+; CDP is the
            # replacement. `Accessibility.getFullAXTree` returns {nodes:[…]}
            # where each node has {nodeId, role, name, ignored, childIds, …}.
            # When interesting_only is True we drop ignored nodes (matches the
            # old API's pruning semantics).
            client = page.context.new_cdp_session(page)
            try:
                tree = client.send('Accessibility.getFullAXTree')
            finally:
                client.detach()
            if bool(step.interesting_only) and isinstance(tree, dict):
                tree = {**tree, 'nodes': [n for n in tree.get('nodes', []) if not n.get('ignored', False)]}
            # root_selector is intentionally not honoured yet — CDP scoping
            # requires queryAXTree with a backendNodeId; will land when the
            # probe-batch verb (Φ5) lifts the helper.
            return Schema__Step__Result__Base(step_id            = self.resolve_id(step, step_index) ,
                                              step_index         = step_index                        ,
                                              action             = step.action                       ,
                                              status             = Enum__Step__Status.PASSED         ,
                                              duration_ms        = self.now_ms() - started_ms        ,
                                              artefacts          = []                                ,
                                              accessibility_tree = tree if isinstance(tree, dict) else {})
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_pdf(self, page, step: Schema__Step__Get_Pdf, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            data = page.pdf(format           = str(step.format)             ,
                            landscape        = bool(step.landscape)         ,
                            print_background = bool(step.print_background)  )
            ref  = self.artefact_writer.capture_pdf(data, capture_config.pdf)
            return self.passed_result(step, step_index, started_ms, artefacts=self.filter_refs([ref]))
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    # ─── Φ4 — listener-buffer verbs (FR-5c) + universal idle predicate (FR-1d) ─

    def execute_get_console_tail(self, page, step: Schema__Step__Get_Console_Tail, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            buffer = buffer_from_page(page)                                                          # None when Sequence__Runner didn't attach one (unit tests bypass the runner)
            events = buffer.console_tail(int(step.lines)) if buffer is not None else []
            return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                              step_index  = step_index                        ,
                                              action      = step.action                       ,
                                              status      = Enum__Step__Status.PASSED         ,
                                              duration_ms = self.now_ms() - started_ms        ,
                                              artefacts   = []                                ,
                                              console_log = events                            )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def execute_get_network_failures(self, page, step: Schema__Step__Get_Network_Failures, step_index: int, capture_config: Schema__Capture__Config) -> Schema__Step__Result__Base:
        started_ms = self.now_ms()
        try:
            buffer  = buffer_from_page(page)
            events  = buffer.network_failures() if buffer is not None else []
            return Schema__Step__Result__Base(step_id          = self.resolve_id(step, step_index) ,
                                              step_index       = step_index                        ,
                                              action           = step.action                       ,
                                              status           = Enum__Step__Status.PASSED         ,
                                              duration_ms      = self.now_ms() - started_ms        ,
                                              artefacts        = []                                ,
                                              network_failures = events                            )
        except Exception as error:
            return self.failed_result(step, step_index, started_ms, error)

    def _wait_for_network_idle(self, page, idle_ms: int, timeout_ms: int) -> None:                  # FR-1d — block until the listener buffer reports no in-flight requests for `idle_ms` consecutive ms, bounded by timeout_ms
        import time
        buffer = buffer_from_page(page)
        if buffer is None:                                                                          # Without the buffer we can't enforce idle; fall back to Playwright's built-in networkidle (500ms hardcoded)
            page.wait_for_load_state('networkidle', timeout=int(timeout_ms))
            return
        deadline_ms = self.now_ms() + int(timeout_ms)
        quiet_since = self.now_ms() if buffer.in_flight_count() == 0 else None
        while self.now_ms() < deadline_ms:
            in_flight = buffer.in_flight_count()
            if in_flight == 0:
                if quiet_since is None:
                    quiet_since = self.now_ms()
                elif self.now_ms() - quiet_since >= int(idle_ms):
                    return                                                                          # Quiet long enough — success
            else:
                quiet_since = None                                                                  # Reset on any in-flight request
            time.sleep(0.05)                                                                        # 50ms poll — bounded CPU while waiting
        raise TimeoutError(f'wait_for: network_idle_ms={idle_ms} not reached within timeout_ms={timeout_ms} (in_flight={buffer.in_flight_count()})')

    # ─── Built-in JS for get_dom_tree (NOT user JS — bypasses the allowlist) ───
    # Compact, dependency-free DOM traversal. Returns the same shape every time
    # so downstream tooling can cache against it. Visibility check is cheap +
    # conservative: zero-rect / display:none / visibility:hidden / opacity:0 all
    # count as "not visible". `include_invisible` overrides the recursion filter
    # but the node's own `visible` field still reflects reality.
    DOM_TREE_JS = """
    (args) => {
      const { rootSelector, maxDepth, includeInvisible } = args;
      const root = rootSelector ? document.querySelector(rootSelector) : document.body;
      if (!root) return null;
      function isVisible(el) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') return false;
        return true;
      }
      function nodeData(el, depth) {
        const rect = el.getBoundingClientRect();
        const vis  = isVisible(el);
        const kids = [];
        if (depth < maxDepth) {
          for (const child of el.children) {
            if (!includeInvisible && !isVisible(child)) continue;
            kids.push(nodeData(child, depth + 1));
          }
        }
        const txt = (el.textContent || '').trim().slice(0, 80);
        return {
          tag             : el.tagName.toLowerCase(),
          id              : el.id || null,
          class           : el.className || null,
          role            : el.getAttribute('role'),
          accessible_name : el.getAttribute('aria-label') || txt || null,
          rect            : { x: rect.x|0, y: rect.y|0, w: rect.width|0, h: rect.height|0 },
          visible         : vis,
          child_count     : el.children.length,
          children        : kids
        };
      }
      return nodeData(root, 0);
    }
    """

    # ─── Result constructors, error classification, helpers ─────────────────────
    # All engine-neutral — inherited from Step__Executor__Base
    # (passed_result / failed_result / classify_error / resolve_id / filter_refs / now_ms).
