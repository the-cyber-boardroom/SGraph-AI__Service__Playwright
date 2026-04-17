# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Enumeration Types
#
# Every Enum__* in this project subclasses (str, Enum) and defines __str__ to
# return the underlying value. We verify:
#   1. Value round-trip — Enum(value) → member → str() → value
#   2. str(member) equals the underlying string
#   3. Member count matches the spec
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink          import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type          import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name           import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Provider       import Enum__Browser__Provider
from sgraph_ai_service_playwright.schemas.enums.Enum__Content__Format         import Enum__Content__Format
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target      import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.enums.Enum__Evaluate__Return_Type   import Enum__Evaluate__Return_Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Keyboard__Key           import Enum__Keyboard__Key
from sgraph_ai_service_playwright.schemas.enums.Enum__Mouse__Button           import Enum__Mouse__Button
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status        import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action            import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status            import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Video__Codec            import Enum__Video__Codec
from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State             import Enum__Wait__State


def _assert_roundtrip(enum_cls, expected_values):                                   # Round-trip every member and verify value set
    for value in expected_values:
        member = enum_cls(value)
        assert str(member)   == value
        assert member.value  == value
    actual_values = {m.value for m in enum_cls}
    assert actual_values == set(expected_values)


class test_Enum__Browser__Name(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Browser__Name, ['chromium', 'firefox', 'webkit'])


class test_Enum__Browser__Provider(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Browser__Provider, ['local_subprocess', 'cdp_connect', 'browserless'])


class test_Enum__Deployment__Target(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Deployment__Target, ['laptop', 'ci', 'claude_web', 'container', 'lambda'])


class test_Enum__Sequence__Status(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Sequence__Status, ['pending', 'running', 'completed', 'failed', 'partial'])


class test_Enum__Step__Status(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Step__Status, ['pending', 'running', 'passed', 'failed', 'skipped'])


class test_Enum__Step__Action(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Step__Action, [
            'navigate'      , 'click'         , 'fill'         , 'press'          ,
            'select'        , 'hover'         , 'scroll'       , 'wait_for'       ,
            'screenshot'    , 'video_start'   , 'video_stop'   , 'evaluate'       ,
            'dispatch_event', 'set_viewport'  , 'get_content'  , 'get_url'        ,
        ])

    def test__has_sixteen_actions(self):                                            # Spec: 16 action verbs
        assert len(list(Enum__Step__Action)) == 16


class test_Enum__Wait__State(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Wait__State, ['load', 'domcontentloaded', 'networkidle'])


class test_Enum__Mouse__Button(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Mouse__Button, ['left', 'right', 'middle'])


class test_Enum__Evaluate__Return_Type(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Evaluate__Return_Type, ['json', 'string', 'number', 'boolean'])


class test_Enum__Content__Format(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Content__Format, ['html', 'text'])


class test_Enum__Artefact__Sink(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Artefact__Sink, ['vault', 'inline', 's3', 'local_file'])


class test_Enum__Artefact__Type(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Artefact__Type, [
            'screenshot', 'video', 'pdf', 'har', 'trace',
            'console_log', 'network_log', 'page_content',
        ])


class test_Enum__Video__Codec(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Video__Codec, ['webm', 'mp4'])


class test_Enum__Keyboard__Key(TestCase):
    def test__roundtrip(self):
        _assert_roundtrip(Enum__Keyboard__Key, [
            'Enter'    , 'Tab'       , 'Escape'    , 'Backspace' ,
            'Delete'   , 'ArrowUp'   , 'ArrowDown' , 'ArrowLeft' , 'ArrowRight',
            'Control+a', 'Control+c' , 'Control+v' ,
        ])
