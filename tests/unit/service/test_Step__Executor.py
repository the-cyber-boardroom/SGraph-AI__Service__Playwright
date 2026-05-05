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
#   • Deferred actions raise NotImplementedError with a clear "Phase 2.11" marker.
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
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                               import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                               import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                         import Step_Id
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Content              import Schema__Step__Result__Get_Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url                  import Schema__Step__Result__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                               import Schema__Step__Base
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Click                              import Schema__Step__Click
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Fill                               import Schema__Step__Fill
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Content                        import Schema__Step__Get_Content
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Url                            import Schema__Step__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Hover                              import Schema__Step__Hover
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                           import Schema__Step__Navigate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Screenshot                         import Schema__Step__Screenshot
from sg_compute_specs.playwright.core.service.Artefact__Writer                                       import Artefact__Writer
from sg_compute_specs.playwright.core.service.Step__Executor                                         import DEFERRED_MESSAGE, Step__Executor


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


class _Fake_Page:
    url = 'https://example.com/current'
    screenshot_bytes         : bytes = b'\x89PNG\r\n\x1a\nFULL_PAGE'
    screenshot_element_bytes : bytes = b'\x89PNG\r\n\x1a\nELEMENT'
    content_value            : str   = '<html><body>hello</body></html>'
    inner_html_value         : str   = '<span>inner</span>'
    inner_text_value         : str   = 'inner text'

    def __init__(self, *, raise_on: str = None):
        self.calls    = []
        self.raise_on = raise_on                                                        # Name of method that should raise (for failure-path tests)

    def _maybe_raise(self, name):
        if self.raise_on == name:
            raise RuntimeError(f'{name} blew up')

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

    def test__execute_surface_has_one_method_per_action(self):                          # Drift guard: every Enum__Step__Action has an execute_* handler
        for action in Enum__Step__Action:
            method_name = f'execute_{action.value}'
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


class test_deferred_actions(TestCase):

    def test__hover_raises_phase_2_11_marker(self):
        page = _Fake_Page()
        step = Schema__Step__Hover(selector='.menu')
        try:
            _executor().execute(page, step, step_index=0, capture_config=_capture_config_all_inline())
            raise AssertionError('expected NotImplementedError')
        except NotImplementedError as error:
            assert 'Phase 2.11' in str(error)

    def test__deferred_message_marks_phase(self):
        assert 'Phase 2.11' in DEFERRED_MESSAGE
