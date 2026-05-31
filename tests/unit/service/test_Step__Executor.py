# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Step__Executor (Phase 2.9 first-pass)
#
# Drives the executor with a Fake_Page test double that records every call
# (no mocks, no pytest patching). This lets us verify the full first-pass
# dispatch surface without a real browser:
#   • NAVIGATE / CLICK / FILL / SCREENSHOT / GET_CONTENT / GET_URL pass through
#     to the right page method with the right kwargs.
#   • Exceptions are caught and surface as FAILED results with duration + error.
#   • SCREENSHOT routes bytes through Artefact__Writer.capture_screenshot.
#   • GET_CONTENT embeds the content when inline_in_response, else captures via sink.
#   • WAIT_FOR / PRESS / SELECT / HOVER / SCROLL / SET_VIEWPORT / DISPATCH_EVENT
#     pass through to the right page method; exceptions surface as per-step FAILED.
#   • An unmapped action returns a FAILED result rather than raising.
#
# Real Chromium integration lives in tests/integration/service/test_Step__Executor.py.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import Any, Dict, List, Tuple
from unittest                                                                                   import TestCase

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Sink_Config                import Schema__Artefact__Sink_Config
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                       import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Sink                             import Enum__Artefact__Sink
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Type                             import Enum__Artefact__Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                            import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                      import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                               import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Error__Type                          import Enum__Step__Error__Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                               import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                         import Step_Id
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Content              import Schema__Step__Result__Get_Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url                  import Schema__Step__Result__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                               import Schema__Step__Base
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Click                              import Schema__Step__Click
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Fill                               import Schema__Step__Fill
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Content                        import Schema__Step__Get_Content
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Url                            import Schema__Step__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Evaluate                           import Schema__Step__Evaluate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Hover                              import Schema__Step__Hover
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                           import Schema__Step__Navigate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Screenshot                         import Schema__Step__Screenshot
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Wait_For                           import Schema__Step__Wait_For
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Press                              import Schema__Step__Press
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Select                             import Schema__Step__Select
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Scroll                             import Schema__Step__Scroll
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Set_Viewport                       import Schema__Step__Set_Viewport
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Dispatch_Event                     import Schema__Step__Dispatch_Event
from sg_compute_specs.playwright.core.schemas.enums.Enum__Keyboard__Key                              import Enum__Keyboard__Key
from sg_compute_specs.playwright.core.service.Artefact__Writer                                       import Artefact__Writer
from sg_compute_specs.playwright.core.service.Step__Executor                                         import ACTION_HANDLERS, Step__Executor


# ── Fake page / locator ───────────────────────────────────────────────────────

class _Fake_Locator:                                                                    # Enough surface for first-pass executor handlers
    def __init__(self, page, selector):
        self.page     = page
        self.selector = selector

    def screenshot(self, **kwargs):
        self.page.calls.append(('locator.screenshot', self.selector, kwargs))
        return self.page.screenshot_element_bytes

    def inner_html(self, **kwargs):
        self.page.calls.append(('locator.inner_html', self.selector, kwargs))
        return self.page.inner_html_value

    def inner_text(self, **kwargs):
        self.page.calls.append(('locator.inner_text', self.selector, kwargs))
        return self.page.inner_text_value

    def press_sequentially(self, text, **kwargs):
        self.page.calls.append(('locator.press_sequentially', self.selector, text, kwargs))

    def scroll_into_view_if_needed(self, **kwargs):
        self.page.calls.append(('locator.scroll_into_view_if_needed', self.selector, kwargs))

    def evaluate(self, expression, **kwargs):                                        # Φ3 — get_html selector branch uses locator.evaluate('el => el.outerHTML', …)
        self.page.calls.append(('locator.evaluate', self.selector, expression, kwargs))
        return f'<{self.selector.strip("#.")}>fake-outerhtml</{self.selector.strip("#.")}>'


class _Fake_Keyboard:
    def __init__(self, page):
        self.page = page

    def press(self, key, **kwargs):
        self.page.calls.append(('keyboard.press', key, kwargs))


class _Fake_Mouse:
    def __init__(self, page):
        self.page = page

    def wheel(self, x, y):
        self.page.calls.append(('mouse.wheel', x, y))


class _Fake_Page:
    url = 'https://example.com/current'
    screenshot_bytes         : bytes = b'\x89PNG\r\n\x1a\nFULL_PAGE'
    screenshot_element_bytes : bytes = b'\x89PNG\r\n\x1a\nELEMENT'
    content_value            : str   = '<html><body>hello</body></html>'
    inner_html_value         : str   = '<span>inner</span>'
    inner_text_value         : str   = 'inner text'
    evaluate_return_value            = 'Example Domain'                              # FR-5a — what page.evaluate() returns; per-test override

    def __init__(self, *, raise_on: str = None):
        self.calls    = []
        self.raise_on = raise_on                                                        # Name of method that should raise (for failure-path tests)
        self.keyboard = _Fake_Keyboard(self)
        self.mouse    = _Fake_Mouse(self)

    def _maybe_raise(self, name):
        if self.raise_on == name:
            raise RuntimeError(f'{name} blew up')

    def wait_for_selector(self, selector, **kwargs):
        self.calls.append(('wait_for_selector', selector, kwargs))
        self._maybe_raise('wait_for_selector')

    def wait_for_url(self, url, **kwargs):
        self.calls.append(('wait_for_url', url, kwargs))

    def wait_for_load_state(self, state=None, **kwargs):
        self.calls.append(('wait_for_load_state', state, kwargs))

    def press(self, selector, key, **kwargs):
        self.calls.append(('press', selector, key, kwargs))

    def select_option(self, selector, values, **kwargs):
        self.calls.append(('select_option', selector, values, kwargs))

    def hover(self, selector, **kwargs):
        self.calls.append(('hover', selector, kwargs))

    def set_viewport_size(self, viewport):
        self.calls.append(('set_viewport_size', viewport))

    def dispatch_event(self, selector, event_type, **kwargs):
        self.calls.append(('dispatch_event', selector, event_type, kwargs))

    def goto(self, url, **kwargs):
        self.calls.append(('goto', url, kwargs))
        self._maybe_raise('goto')

    def click(self, selector, **kwargs):
        self.calls.append(('click', selector, kwargs))
        self._maybe_raise('click')

    def fill(self, selector, value, **kwargs):
        self.calls.append(('fill', selector, value, kwargs))
        self._maybe_raise('fill')

    def screenshot(self, **kwargs):
        self.calls.append(('screenshot', kwargs))
        self._maybe_raise('screenshot')
        return self.screenshot_bytes

    def locator(self, selector):
        return _Fake_Locator(self, selector)

    def content(self):
        self.calls.append(('content',))
        return self.content_value

    dom_tree_return_value = {'tag': 'body', 'id': None, 'class': None,               # Φ3 — what page.evaluate(DOM_TREE_JS, args) returns; per-test override
                             'role': None, 'accessible_name': 'fake', 'rect': {'x':0,'y':0,'w':1,'h':1},
                             'visible': True, 'child_count': 0, 'children': []}

    def evaluate(self, expression, *args):                                            # Variadic: page.evaluate accepts (expr, args) and (expr); fake handles both
        self.calls.append(('evaluate', expression, args))
        if args and isinstance(args[0], dict) and 'rootSelector' in args[0]:          # Φ3 — DOM_TREE_JS invocation; return the canned tree
            return self.dom_tree_return_value
        return self.evaluate_return_value                                             # FR-5a — return value surfaced; tests set evaluate_return_value

    def wait_for_timeout(self, duration_ms):                                          # Φ2 — FR-4 plain wait verb
        self.calls.append(('wait_for_timeout', duration_ms))
        self._maybe_raise('wait_for_timeout')

    def get_by_text(self, text):                                                     # Φ2 — FR-1a wait_for: text routes through page.get_by_text(...).wait_for(...)
        return _Fake_Text_Locator(self, text)

    def wait_for_function(self, expression, **kwargs):                               # Φ3 — FR-1c wait_for: function
        self.calls.append(('wait_for_function', expression, kwargs))
        self._maybe_raise('wait_for_function')

    pdf_bytes : bytes = b'%PDF-1.4 fake pdf body'

    def pdf(self, **kwargs):                                                         # Φ3 — FR-5d get_pdf
        self.calls.append(('pdf', kwargs))
        self._maybe_raise('pdf')
        return self.pdf_bytes

    # Φ3 — get_a11y_tree uses CDP (page.accessibility removed in Playwright 1.49+).
    # Executor calls page.context.new_cdp_session(page) → client.send('Accessibility.getFullAXTree')
    @property
    def context(self):
        return _Fake_Context(self)


class _Fake_Context:
    def __init__(self, page):
        self.page = page

    def new_cdp_session(self, page):
        self.page.calls.append(('context.new_cdp_session', id(page)))
        return _Fake_CDP_Session(self.page)


class _Fake_CDP_Session:
    a11y_tree = {'nodes': [{'nodeId': '1', 'role': {'value': 'WebArea'}, 'ignored': False, 'childIds': ['2']},
                           {'nodeId': '2', 'role': {'value': 'StaticText'}, 'ignored': True , 'childIds': []}]}

    def __init__(self, page):
        self.page = page

    def send(self, method, params=None):
        self.page.calls.append(('cdp.send', method, params))
        self.page._maybe_raise(f'cdp.{method}')
        if method == 'Accessibility.getFullAXTree':
            return self.a11y_tree
        return {}

    def detach(self):
        self.page.calls.append(('cdp.detach',))


class _Fake_Text_Locator:                                                            # Returned by page.get_by_text(...) — only needs .wait_for(...) for the FR-1a path
    def __init__(self, page, text):
        self.page = page
        self.text = text

    def wait_for(self, **kwargs):
        self.page.calls.append(('text.wait_for', self.text, kwargs))
        self.page._maybe_raise('text.wait_for')


# ── _InMemoryWriter: routes artefacts without real vault/S3 ──────────────────

class _InMemoryWriter(Artefact__Writer):                                                # Same pattern as test_Artefact__Writer
    pass                                                                                # capture_* + INLINE path works out-of-box; no overrides needed


def _capture_config_all_inline() -> Schema__Capture__Config:
    inline_on = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE)
    return Schema__Capture__Config(screenshot   = inline_on ,
                                   page_content = inline_on )


def _capture_config_all_off() -> Schema__Capture__Config:
    off = Schema__Artefact__Sink_Config(enabled=False, sink=Enum__Artefact__Sink.INLINE)
    return Schema__Capture__Config(screenshot=off, page_content=off)


def _executor() -> Step__Executor:
    return Step__Executor(artefact_writer=_InMemoryWriter())


# ── Tests ────────────────────────────────────────────────────────────────────

class test_class_shape(TestCase):

    def test__composes_artefact_writer_by_default(self):
        e = Step__Executor()
        assert isinstance(e.artefact_writer, Artefact__Writer)

    def test__every_dispatched_action_has_a_handler(self):                              # Drift guard: every action in the table maps to a real method
        for action, method_name in ACTION_HANDLERS.items():
            assert hasattr(Step__Executor, method_name), f'missing {method_name}'


class test_execute_navigate(TestCase):

    def test__passes_url_wait_until_and_timeout_to_page_goto(self):
        page = _Fake_Page()
        step = Schema__Step__Navigate(url='https://example.com/login', timeout_ms=15_000)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert res.action == Enum__Step__Action.NAVIGATE
        assert res.artefacts == []
        kind, url, kwargs = page.calls[0]
        assert kind         == 'goto'
        assert url          == 'https://example.com/login'
        assert kwargs['wait_until'] == 'load'
        assert kwargs['timeout']    == 15_000

    def test__exception_maps_to_failed_result(self):
        page = _Fake_Page(raise_on='goto')
        step = Schema__Step__Navigate(url='https://example.com/')
        res  = _executor().execute(page, step, step_index=2, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.FAILED
        assert res.step_index == 2
        assert 'goto blew up' in str(res.error_message)


class test_execute_click(TestCase):

    def test__passes_all_fields_to_page_click(self):
        page = _Fake_Page()
        step = Schema__Step__Click(selector='#submit', delay_ms=25, force=True, click_count=2)
        res  = _executor().execute(page, step, step_index=1, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, kwargs = page.calls[0]
        assert kind                == 'click'
        assert selector            == '#submit'
        assert kwargs['click_count'] == 2
        assert kwargs['delay']       == 25
        assert kwargs['force']       is True


class test_execute_fill(TestCase):

    def test__clear_first_uses_page_fill(self):
        page = _Fake_Page()
        step = Schema__Step__Fill(selector='input[name=email]', value='hello world', clear_first=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, value, kwargs = page.calls[0]
        assert kind     == 'fill'
        assert selector == 'input[name=email]'
        assert value    == 'hello world'

    def test__no_clear_first_uses_press_sequentially(self):                             # Appends rather than replacing
        page = _Fake_Page()
        step = Schema__Step__Fill(selector='input', value='abc', clear_first=False)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, value, _ = page.calls[0]
        assert kind     == 'locator.press_sequentially'
        assert selector == 'input'
        assert value    == 'abc'


class test_execute_screenshot(TestCase):

    def test__full_page_routes_bytes_through_capture_screenshot(self):
        page = _Fake_Page()
        step = Schema__Step__Screenshot(full_page=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert len(res.artefacts) == 1
        ref = res.artefacts[0]
        assert ref.artefact_type == Enum__Artefact__Type.SCREENSHOT
        assert ref.sink          == Enum__Artefact__Sink.INLINE
        assert ref.inline_b64    is not None                                            # Encoded the full-page bytes

    def test__element_selector_uses_locator_screenshot(self):
        page = _Fake_Page()
        step = Schema__Step__Screenshot(selector='#hero')
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kinds = [c[0] for c in page.calls]
        assert 'locator.screenshot' in kinds
        assert 'screenshot'          not in kinds                                        # Element path skips page.screenshot

    def test__disabled_sink_returns_empty_artefacts(self):
        page = _Fake_Page()
        step = Schema__Step__Screenshot()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_off())
        assert res.status    == Enum__Step__Status.PASSED
        assert res.artefacts == []                                                      # Capture disabled → no ref


class test_execute_get_content(TestCase):

    def test__html_full_page_inline_in_response(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Content(content_format=Enum__Content__Format.HTML, inline_in_response=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert isinstance(res, Schema__Step__Result__Get_Content)
        assert res.status         == Enum__Step__Status.PASSED
        assert str(res.content)   == '<html><body>hello</body></html>'
        assert res.content_format == Enum__Content__Format.HTML
        assert res.artefacts      == []                                                  # inline_in_response → no sink write

    def test__text_with_selector_uses_locator_inner_text(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Content(selector='#main', content_format=Enum__Content__Format.TEXT)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status         == Enum__Step__Status.PASSED
        assert str(res.content)   == 'inner text'
        assert res.content_format == Enum__Content__Format.TEXT
        assert res.content_type   == 'text/plain'

    def test__non_inline_routes_through_capture_page_content(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Content(inline_in_response=False)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert len(res.artefacts) == 1
        assert res.artefacts[0].artefact_type == Enum__Artefact__Type.PAGE_CONTENT


class test_execute_get_url(TestCase):

    def test__returns_page_url(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Url()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert isinstance(res, Schema__Step__Result__Get_Url)
        assert res.status == Enum__Step__Status.PASSED
        assert str(res.url) == 'https://example.com/current'


class test_step_id_resolution(TestCase):

    def test__defaults_to_step_index_when_id_absent(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Url()                                                  # No id set → falls back to index
        res  = _executor().execute(page, step, step_index=7, capture_config=_capture_config_all_inline())
        assert str(res.step_id) == '7'

    def test__uses_caller_supplied_id_when_present(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Url(id=Step_Id('login'))
        res  = _executor().execute(page, step, step_index=2, capture_config=_capture_config_all_inline())
        assert str(res.step_id) == 'login'


class test_execute_wait_for(TestCase):

    def test__selector_visible_uses_wait_for_selector(self):
        page = _Fake_Page()
        step = Schema__Step__Wait_For(selector='main', visible=True, timeout_ms=8000)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, kwargs = page.calls[0]
        assert kind            == 'wait_for_selector'
        assert selector        == 'main'
        assert kwargs['state'] == 'visible'
        assert kwargs['timeout'] == 8000

    def test__attached_only_when_visible_false(self):
        page = _Fake_Page()
        step = Schema__Step__Wait_For(selector='#x', visible=False)
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert page.calls[0][2]['state'] == 'attached'

    def test__no_selector_falls_back_to_load_state(self):
        page = _Fake_Page()
        step = Schema__Step__Wait_For()
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert page.calls[0][0] == 'wait_for_load_state'

    def test__exception_maps_to_failed_result(self):
        page = _Fake_Page(raise_on='wait_for_selector')
        step = Schema__Step__Wait_For(selector='main')
        res  = _executor().execute(page, step, step_index=3, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.FAILED                                   # never raises — per-step FAILED
        assert 'blew up' in str(res.error_message)


class test_execute_press(TestCase):

    def test__with_selector_uses_page_press(self):
        page = _Fake_Page()
        step = Schema__Step__Press(selector='input', key=Enum__Keyboard__Key.ENTER)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, key, _ = page.calls[0]
        assert kind == 'press' and selector == 'input' and key == 'Enter'

    def test__without_selector_uses_keyboard_press(self):
        page = _Fake_Page()
        step = Schema__Step__Press(key=Enum__Keyboard__Key.TAB)
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert page.calls[0][0] == 'keyboard.press'
        assert page.calls[0][1] == 'Tab'


class test_execute_select_hover_scroll_viewport_dispatch(TestCase):

    def test__select_passes_values_list(self):
        page = _Fake_Page()
        step = Schema__Step__Select(selector='select', values=['a', 'b'])
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, values, _ = page.calls[0]
        assert kind == 'select_option' and values == ['a', 'b']

    def test__hover_uses_page_hover(self):
        page = _Fake_Page()
        step = Schema__Step__Hover(selector='.menu')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert page.calls[0][0] == 'hover' and page.calls[0][1] == '.menu'

    def test__scroll_page_uses_mouse_wheel(self):
        page = _Fake_Page()
        step = Schema__Step__Scroll(x=0, y=500)
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert page.calls[0] == ('mouse.wheel', 0, 500)

    def test__scroll_with_selector_scrolls_element_into_view(self):
        page = _Fake_Page()
        step = Schema__Step__Scroll(selector='#footer')
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert page.calls[0][0] == 'locator.scroll_into_view_if_needed'

    def test__set_viewport_passes_dimensions(self):
        page = _Fake_Page()
        step = Schema__Step__Set_Viewport()                                             # default viewport 1280x800
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kind, viewport = page.calls[0]
        assert kind == 'set_viewport_size'
        assert viewport == {'width': 1280, 'height': 800}

    def test__dispatch_event_passes_selector_and_event_type(self):
        page = _Fake_Page()
        step = Schema__Step__Dispatch_Event(selector='#btn', event_type='click')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kind, selector, event_type, _ = page.calls[0]
        assert kind == 'dispatch_event' and selector == '#btn' and event_type == 'click'


class test_dispatch_table(TestCase):

    def test__every_table_entry_resolves_to_a_real_method(self):
        for action, method_name in ACTION_HANDLERS.items():
            assert hasattr(Step__Executor, method_name), f'{action.value} → missing {method_name}'

    def test__unmapped_action_returns_failed_result_not_crash(self):                     # robustness: no verb may ever abort the sequence
        page = _Fake_Page()
        step = Schema__Step__Base(action=Enum__Step__Action.VIDEO_START)                 # intentionally not in ACTION_HANDLERS
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status     == Enum__Step__Status.FAILED
        assert res.error_type == Enum__Step__Error__Type.UNSUPPORTED_ACTION              # classified, not just free-text
        assert 'Unsupported action' in str(res.error_message)


class test_classify_error(TestCase):                                                     # error_type classifier — exhaustive over the enum's recognised classes

    def _classify(self, error):
        return _executor().classify_error(error)

    def test__timeout_by_class_name(self):
        class PlaywrightTimeoutError(Exception): pass
        assert self._classify(PlaywrightTimeoutError('boom')) == Enum__Step__Error__Type.TIMEOUT

    def test__timeout_by_message(self):
        assert self._classify(RuntimeError('Timeout 30000ms exceeded.')) == Enum__Step__Error__Type.TIMEOUT

    def test__not_implemented_maps_to_unsupported_action(self):
        assert self._classify(NotImplementedError('VIDEO')) == Enum__Step__Error__Type.UNSUPPORTED_ACTION

    def test__navigation_dns_failure(self):
        assert self._classify(RuntimeError('net::ERR_NAME_NOT_RESOLVED at https://nope.invalid/')) == Enum__Step__Error__Type.NAVIGATION_FAILED

    def test__evaluate_rejected_by_allowlist(self):
        assert self._classify(RuntimeError('JS expression not in trusted allowlist')) == Enum__Step__Error__Type.EVALUATE_REJECTED

    def test__selector_not_found(self):
        assert self._classify(RuntimeError('selector "#nope" did not match any element (no element)')) == Enum__Step__Error__Type.SELECTOR_NOT_FOUND

    def test__unknown_default(self):
        assert self._classify(RuntimeError('weird thing happened')) == Enum__Step__Error__Type.UNKNOWN

    def test__failed_result_populates_error_type(self):                                  # end-to-end through the result builder
        page = _Fake_Page(raise_on='wait_for_selector')
        step = Schema__Step__Wait_For(selector='main')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status     == Enum__Step__Status.FAILED
        assert res.error_type == Enum__Step__Error__Type.UNKNOWN                         # RuntimeError('… blew up') is not a recognised class


# ─── FR-5a — evaluate's return value is surfaced ─────────────────────────────────
class test_execute_evaluate(TestCase):

    def test__return_value_is_surfaced_as_string(self):
        page = _Fake_Page()
        page.evaluate_return_value = 'Example Domain'
        step = Schema__Step__Evaluate(expression='document.title')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status       == Enum__Step__Status.PASSED
        assert res.return_value == 'Example Domain'
        assert res.return_type  == Enum__Evaluate__Return_Type.STRING

    def test__classify_eval_return__bool(self):
        assert _executor().classify_eval_return(True)  == Enum__Evaluate__Return_Type.BOOLEAN
        assert _executor().classify_eval_return(False) == Enum__Evaluate__Return_Type.BOOLEAN

    def test__classify_eval_return__number(self):
        assert _executor().classify_eval_return(42)    == Enum__Evaluate__Return_Type.NUMBER
        assert _executor().classify_eval_return(3.14)  == Enum__Evaluate__Return_Type.NUMBER

    def test__classify_eval_return__string(self):
        assert _executor().classify_eval_return('hi')  == Enum__Evaluate__Return_Type.STRING

    def test__classify_eval_return__json_for_collections(self):
        assert _executor().classify_eval_return({'k': 1}) == Enum__Evaluate__Return_Type.JSON
        assert _executor().classify_eval_return([1, 2])   == Enum__Evaluate__Return_Type.JSON
        assert _executor().classify_eval_return(None)     == Enum__Evaluate__Return_Type.JSON

    def test__failure_path_returns_base_with_no_return_value(self):
        page = _Fake_Page()
        def _raise(expression):                                                          # override evaluate to raise
            raise RuntimeError('eval crashed')
        page.evaluate = _raise
        step = Schema__Step__Evaluate(expression='whatever')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status       == Enum__Step__Status.FAILED
        assert res.return_value is None
        assert res.return_type  is None


# ─── Φ2 — FR-4 plain wait verb ───────────────────────────────────────────────────
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Wait import Schema__Step__Wait


class test_execute_wait(TestCase):

    def test__sleeps_for_duration_ms(self):
        page = _Fake_Page()
        step = Schema__Step__Wait(duration_ms=250)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert ('wait_for_timeout', 250) in page.calls

    def test__zero_duration_is_a_no_op_that_still_passes(self):
        page = _Fake_Page()
        step = Schema__Step__Wait(duration_ms=0)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert ('wait_for_timeout', 0) in page.calls

    def test__exception_surfaces_as_failed(self):
        page = _Fake_Page(raise_on='wait_for_timeout')
        step = Schema__Step__Wait(duration_ms=100)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.FAILED


# ─── Φ2 — FR-1a wait_for: text + FR-1b wait_for: selector_gone ─────────────────
class test_wait_for_text_and_selector_gone(TestCase):

    def test__text_branch_routes_through_get_by_text(self):                          # FR-1a
        page = _Fake_Page()
        step = Schema__Step__Wait_For(text='Welcome back')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        text_calls = [c for c in page.calls if c[0] == 'text.wait_for']
        assert len(text_calls) == 1
        assert text_calls[0][1] == 'Welcome back'
        assert text_calls[0][2].get('state') == 'visible'

    def test__selector_gone_passes_state_detached(self):                             # FR-1b
        page = _Fake_Page()
        step = Schema__Step__Wait_For(selector='.spinner', selector_gone=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        selector_calls = [c for c in page.calls if c[0] == 'wait_for_selector']
        assert len(selector_calls) == 1
        assert selector_calls[0][1] == '.spinner'
        assert selector_calls[0][2].get('state') == 'detached'

    def test__selector_visible_default_still_works(self):                            # Regression — pre-Φ2 behaviour unchanged
        page = _Fake_Page()
        step = Schema__Step__Wait_For(selector='#login')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        selector_calls = [c for c in page.calls if c[0] == 'wait_for_selector']
        assert selector_calls[0][2].get('state') == 'visible'

    def test__text_takes_precedence_over_selector_only(self):                        # text wins; selector-only branch is NOT taken when text is also set
        page = _Fake_Page()
        step = Schema__Step__Wait_For(text='ok')
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kinds = [c[0] for c in page.calls]
        assert 'text.wait_for'      in kinds
        assert 'wait_for_selector'  not in kinds


# ─── Φ2 — FR-7 viewport shorthand on screenshot ──────────────────────────────────
from sg_compute_specs.playwright.core.schemas.browser.Schema__Viewport import Schema__Viewport


class test_screenshot_viewport_shorthand(TestCase):

    def test__sets_viewport_before_snapping(self):
        page = _Fake_Page()
        step = Schema__Step__Screenshot(full_page=False, viewport=Schema__Viewport(width=1024, height=768))
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kinds = [c[0] for c in page.calls]
        assert kinds.index('set_viewport_size') < kinds.index('screenshot')          # Order matters: viewport first, then screenshot
        viewport_call = next(c for c in page.calls if c[0] == 'set_viewport_size')
        assert viewport_call[1] == {'width': 1024, 'height': 768}

    def test__no_viewport_means_no_set_viewport_call(self):
        page = _Fake_Page()
        step = Schema__Step__Screenshot(full_page=False)
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kinds = [c[0] for c in page.calls]
        assert 'set_viewport_size' not in kinds


# ─── Φ3 — DOM-read verbs (FR-2) ──────────────────────────────────────────────────
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_A11y_Tree   import Schema__Step__Get_A11y_Tree
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Dom_Tree    import Schema__Step__Get_Dom_Tree
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Html        import Schema__Step__Get_Html
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Pdf         import Schema__Step__Get_Pdf
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Text        import Schema__Step__Get_Text


class test_execute_get_text(TestCase):

    def test__no_selector_uses_body_locator(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Text()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert str(res.text) == 'inner text'
        body_text_calls = [c for c in page.calls if c[0] == 'locator.inner_text' and c[1] == 'body']
        assert body_text_calls, f'expected locator(body).inner_text() call, got {page.calls}'

    def test__selector_scopes_to_subtree(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Text(selector='#article')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        scoped = [c for c in page.calls if c[0] == 'locator.inner_text' and c[1] == '#article']
        assert scoped

    def test__failure_path_returns_base_failed_with_no_text(self):
        page = _Fake_Page()
        page.locator = lambda sel: (_ for _ in ()).throw(RuntimeError('locator blew up'))    # force failure
        step = Schema__Step__Get_Text()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.FAILED
        assert res.text   is None


class test_execute_get_html(TestCase):

    def test__no_selector_uses_page_content(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Html()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status   == Enum__Step__Status.PASSED
        assert str(res.html) == '<html><body>hello</body></html>'                                # _Fake_Page.content_value
        assert ('content',) in page.calls

    def test__selector_uses_locator_evaluate_outerhtml(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Html(selector='#main')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        evals = [c for c in page.calls if c[0] == 'locator.evaluate']
        assert evals and evals[0][2] == 'el => el.outerHTML'                                     # Outer HTML JS expr — distinguishes from get_content's innerHTML


class test_execute_get_dom_tree(TestCase):

    def test__passes_root_selector_max_depth_args_to_js(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Dom_Tree(root_selector='#app', max_depth=5, include_invisible=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        evals = [c for c in page.calls if c[0] == 'evaluate']
        assert evals, 'expected page.evaluate(DOM_TREE_JS, args) call'
        args = evals[0][2][0]                                                                    # First positional arg after expression
        assert args == {'rootSelector': '#app', 'maxDepth': 5, 'includeInvisible': True}

    def test__returns_tree_in_dom_tree_field(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Dom_Tree()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.dom_tree is not None
        assert res.dom_tree['tag'] == 'body'


class test_execute_get_a11y_tree(TestCase):

    def test__returns_cdp_tree_in_accessibility_tree_field(self):
        page = _Fake_Page()
        step = Schema__Step__Get_A11y_Tree(interesting_only=False)                                 # No filtering — full CDP shape preserved
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert isinstance(res.accessibility_tree, dict)
        assert 'nodes' in res.accessibility_tree
        assert len(res.accessibility_tree['nodes']) == 2                                          # Both nodes from the fake survive

    def test__interesting_only_filters_out_ignored_nodes(self):
        page = _Fake_Page()
        step = Schema__Step__Get_A11y_Tree(interesting_only=True)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        nodes = res.accessibility_tree['nodes']
        assert len(nodes) == 1                                                                    # The ignored=True node is dropped
        assert nodes[0]['nodeId'] == '1'
        assert nodes[0]['ignored'] is False

    def test__cdp_session_is_detached_after_use(self):                                            # Hygiene — failing to detach leaks websocket connections
        page = _Fake_Page()
        step = Schema__Step__Get_A11y_Tree()
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kinds = [c[0] for c in page.calls]
        assert kinds.index('context.new_cdp_session') < kinds.index('cdp.send')
        assert 'cdp.detach' in kinds


class test_execute_get_pdf(TestCase):

    def test__routes_bytes_through_capture_pdf(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Pdf(format='Letter', landscape=True, print_background=False)
        cfg  = Schema__Capture__Config(pdf=Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE))
        res  = _executor().execute(page, step, step_index=0, capture_config=cfg)
        assert res.status == Enum__Step__Status.PASSED
        assert len(res.artefacts) == 1
        assert res.artefacts[0].artefact_type == Enum__Artefact__Type.PDF
        pdf_calls = [c for c in page.calls if c[0] == 'pdf']
        assert pdf_calls and pdf_calls[0][1] == {'format': 'Letter', 'landscape': True, 'print_background': False}


# ─── Φ3 — FR-1c wait_for: function ───────────────────────────────────────────────
class test_wait_for_function(TestCase):

    def test__function_branch_calls_wait_for_function(self):
        page = _Fake_Page()
        step = Schema__Step__Wait_For(function='() => window.__ready === true')
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        fn_calls = [c for c in page.calls if c[0] == 'wait_for_function']
        assert fn_calls and fn_calls[0][1] == '() => window.__ready === true'

    def test__function_takes_precedence_over_other_branches(self):                                 # If function + selector both set, function wins (most-specific predicate)
        page = _Fake_Page()
        step = Schema__Step__Wait_For(function='() => true', selector='#x', text='hi')
        _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        kinds = [c[0] for c in page.calls]
        assert 'wait_for_function' in kinds
        assert 'wait_for_selector' not in kinds
        assert 'text.wait_for'      not in kinds


# ─── Φ4 — FR-5c listener-buffer verbs + FR-1d network_idle_ms ───────────────────
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Console_Tail     import Schema__Step__Get_Console_Tail
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Network_Failures import Schema__Step__Get_Network_Failures
from sg_compute_specs.playwright.core.service.Page__Listeners__Buffer                  import (
    Page__Listeners__Buffer, PAGE_ATTR_NAME)


def _attach_fake_buffer(page, *,
                        console_events=(),
                        failed_events=(),
                        in_flight=0):
    buf = Page__Listeners__Buffer()
    buf.console_events.extend(list(console_events))
    buf.failed_events .extend(list(failed_events))
    if in_flight > 0:
        buf.in_flight_ids.update(range(in_flight))                                   # fake unique ids
    setattr(page, PAGE_ATTR_NAME, buf)
    return buf


class test_execute_get_console_tail(TestCase):

    def test__returns_tail_from_attached_buffer(self):
        page = _Fake_Page()
        _attach_fake_buffer(page, console_events=[
            {'type': 'log',   'text': 'first' , 'timestamp': 1},
            {'type': 'warn',  'text': 'second', 'timestamp': 2},
            {'type': 'error', 'text': 'third' , 'timestamp': 3},
        ])
        step = Schema__Step__Get_Console_Tail(lines=2)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        assert [e['text'] for e in res.console_log] == ['second', 'third']

    def test__no_buffer_attached_returns_empty_log(self):                            # Unit tests that bypass the runner — verb must not crash
        page = _Fake_Page()
        step = Schema__Step__Get_Console_Tail()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status      == Enum__Step__Status.PASSED
        assert res.console_log == []


class test_execute_get_network_failures(TestCase):

    def test__returns_failed_events_from_buffer(self):
        page = _Fake_Page()
        _attach_fake_buffer(page, failed_events=[
            {'url': 'https://blocked.example/x', 'method': 'GET', 'failure_text': 'BLOCKED'  , 'timestamp': 9},
        ])
        step = Schema__Step__Get_Network_Failures()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status            == Enum__Step__Status.PASSED
        assert len(res.network_failures) == 1
        assert res.network_failures[0]['url'] == 'https://blocked.example/x'

    def test__no_buffer_returns_empty_list(self):
        page = _Fake_Page()
        step = Schema__Step__Get_Network_Failures()
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status              == Enum__Step__Status.PASSED
        assert res.network_failures    == []


class test_wait_for_network_idle_ms(TestCase):                                       # FR-1d

    def test__returns_immediately_when_in_flight_is_zero_and_idle_window_satisfied(self):
        page = _Fake_Page()
        _attach_fake_buffer(page, in_flight=0)
        step = Schema__Step__Wait_For(network_idle_ms=10, timeout_ms=2000)            # 10ms quiet window — buffer is already quiet
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED

    def test__times_out_when_requests_stay_in_flight(self):
        page = _Fake_Page()
        _attach_fake_buffer(page, in_flight=3)                                        # Never drains
        step = Schema__Step__Wait_For(network_idle_ms=50, timeout_ms=200)             # 200ms timeout; buffer never goes quiet
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.FAILED
        assert 'network_idle_ms' in str(res.error_message)

    def test__falls_back_to_load_state_when_no_buffer_attached(self):                 # Without a buffer the executor falls back to Playwright's built-in networkidle
        page = _Fake_Page()
        step = Schema__Step__Wait_For(network_idle_ms=100, timeout_ms=1000)
        res  = _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
        assert res.status == Enum__Step__Status.PASSED
        kinds = [c[0] for c in page.calls]
        assert 'wait_for_load_state' in kinds                                         # Fell through to page.wait_for_load_state('networkidle', …)
