# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Step Schemas (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                      import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Keyboard__Key                        import Enum__Keyboard__Key
from sg_compute_specs.playwright.core.schemas.enums.Enum__Mouse__Button                        import Enum__Mouse__Button
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                         import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Video__Codec                         import Enum__Video__Codec
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                          import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                         import Schema__Step__Base
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Click                        import Schema__Step__Click
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Dispatch_Event               import Schema__Step__Dispatch_Event
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Evaluate                     import Schema__Step__Evaluate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Fill                         import Schema__Step__Fill
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Content                  import Schema__Step__Get_Content
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Url                      import Schema__Step__Get_Url
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Hover                        import Schema__Step__Hover
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                     import Schema__Step__Navigate
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Press                        import Schema__Step__Press
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Screenshot                   import Schema__Step__Screenshot
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Scroll                       import Schema__Step__Scroll
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Select                       import Schema__Step__Select
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Set_Viewport                 import Schema__Step__Set_Viewport
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Video__Start                 import Schema__Step__Video__Start
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Video__Stop                  import Schema__Step__Video__Stop
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Wait_For                     import Schema__Step__Wait_For


class test_Schema__Step__Base(TestCase):

    def test__defaults(self):
        step = Schema__Step__Base()
        assert step.continue_on_error is False
        assert step.timeout_ms        == 30_000


class test_Step_Action_Discriminators(TestCase):                                    # Every subclass must hard-pin its action

    def test__navigate(self):
        assert Schema__Step__Navigate      (url='https://x').action == Enum__Step__Action.NAVIGATE

    def test__click(self):
        step = Schema__Step__Click(selector='#b')
        assert step.action      == Enum__Step__Action.CLICK
        assert step.button      == Enum__Mouse__Button.LEFT
        assert step.click_count == 1
        assert step.force       is False

    def test__fill(self):
        step = Schema__Step__Fill(selector='#i', value='hello')
        assert step.action      == Enum__Step__Action.FILL
        assert step.clear_first is True

    def test__press(self):
        step = Schema__Step__Press(key=Enum__Keyboard__Key.ENTER)
        assert step.action   == Enum__Step__Action.PRESS
        assert step.selector is None

    def test__select(self):
        assert Schema__Step__Select(selector='#d').action == Enum__Step__Action.SELECT

    def test__hover(self):
        assert Schema__Step__Hover(selector='#h').action == Enum__Step__Action.HOVER

    def test__scroll(self):
        step = Schema__Step__Scroll()
        assert step.action == Enum__Step__Action.SCROLL
        assert step.x      == 0
        assert step.y      == 0

    def test__wait_for(self):
        step = Schema__Step__Wait_For()
        assert step.action  == Enum__Step__Action.WAIT_FOR
        assert step.visible is True

    def test__screenshot(self):
        step = Schema__Step__Screenshot()
        assert step.action    == Enum__Step__Action.SCREENSHOT
        assert step.full_page is False

    def test__video_start(self):
        step = Schema__Step__Video__Start()
        assert step.action == Enum__Step__Action.VIDEO_START
        assert step.codec  == Enum__Video__Codec.WEBM

    def test__video_stop(self):
        assert Schema__Step__Video__Stop().action == Enum__Step__Action.VIDEO_STOP

    def test__evaluate(self):
        step = Schema__Step__Evaluate(expression='document.title')
        assert step.action      == Enum__Step__Action.EVALUATE
        assert step.return_type == Enum__Evaluate__Return_Type.JSON

    def test__dispatch_event(self):
        step = Schema__Step__Dispatch_Event(selector='#x', event_type='click')
        assert step.action == Enum__Step__Action.DISPATCH_EVENT

    def test__set_viewport(self):
        assert Schema__Step__Set_Viewport().action == Enum__Step__Action.SET_VIEWPORT

    def test__get_content(self):
        step = Schema__Step__Get_Content()
        assert step.action             == Enum__Step__Action.GET_CONTENT
        assert step.content_format     == Enum__Content__Format.HTML
        assert step.inline_in_response is True

    def test__get_url(self):
        assert Schema__Step__Get_Url().action == Enum__Step__Action.GET_URL


class test_Step_JSON_Round_Trip(TestCase):                                          # Typed → JSON → Typed preserves fields

    def test__navigate_round_trip(self):
        original = Schema__Step__Navigate(url='https://example.com',
                                          wait_until=Enum__Wait__State.NETWORK_IDLE)
        clone    = Schema__Step__Navigate.from_json(original.json())
        assert clone.json() == original.json()

    def test__click_round_trip(self):
        original = Schema__Step__Click(selector='#submit', click_count=2, force=True)
        clone    = Schema__Step__Click.from_json(original.json())
        assert clone.json() == original.json()
