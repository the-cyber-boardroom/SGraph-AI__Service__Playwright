# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Interceptor__Choice
# Three valid shapes per N5: NONE (default) / NAME / INLINE.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice


class test_Schema__Vnc__Interceptor__Choice(TestCase):

    def test__defaults_to_none(self):                                               # N5 default-off
        c = Schema__Vnc__Interceptor__Choice()
        assert c.kind                  == Enum__Vnc__Interceptor__Kind.NONE
        assert str(c.name)             == ''
        assert str(c.inline_source)    == ''

    def test__name_shape(self):
        c = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger')
        assert c.kind         == Enum__Vnc__Interceptor__Kind.NAME
        assert str(c.name)    == 'header_logger'

    def test__inline_shape_preserves_python_source(self):                           # Whitespace + indentation must survive (decorators, def, etc.)
        src = ('from mitmproxy import http\n\n'
               'def request(flow: http.HTTPFlow) -> None:\n'
               "    flow.request.headers['X-Sg-Marker'] = 'inline'\n")
        c   = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE, inline_source=src)
        assert c.kind                == Enum__Vnc__Interceptor__Kind.INLINE
        assert str(c.inline_source) == src

    def test__round_trip_via_json(self):
        original = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='flow_recorder')
        again    = Schema__Vnc__Interceptor__Choice.from_json(original.json())
        assert again.kind      == Enum__Vnc__Interceptor__Kind.NAME
        assert str(again.name) == 'flow_recorder'
