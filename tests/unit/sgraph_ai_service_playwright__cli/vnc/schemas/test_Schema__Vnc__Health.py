# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Health
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health


class test_Schema__Vnc__Health(TestCase):

    def test__defaults_are_unreachable(self):
        h = Schema__Vnc__Health()
        assert h.nginx_ok    is False
        assert h.mitmweb_ok  is False
        assert h.flow_count  == -1
        assert h.state       == Enum__Vnc__Stack__State.UNKNOWN
        assert str(h.error)  == ''

    def test__round_trip_via_json(self):
        h = Schema__Vnc__Health(stack_name='vnc-prod', state=Enum__Vnc__Stack__State.READY,
                                 nginx_ok=True, mitmweb_ok=True, flow_count=42)
        again = Schema__Vnc__Health.from_json(h.json())
        assert str(again.stack_name)  == 'vnc-prod'
        assert again.state            == Enum__Vnc__Stack__State.READY
        assert again.nginx_ok         is True
        assert again.mitmweb_ok       is True
        assert again.flow_count       == 42
