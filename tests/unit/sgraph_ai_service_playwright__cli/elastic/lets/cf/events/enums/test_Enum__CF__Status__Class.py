# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__Status__Class
# Derived classifier — 5 named buckets + "other".
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class import Enum__CF__Status__Class


class test_Enum__CF__Status__Class(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__CF__Status__Class}
        assert names == {'INFORMATIONAL', 'SUCCESS', 'REDIRECTION',
                         'CLIENT_ERROR', 'SERVER_ERROR', 'OTHER'}

    def test_wire_values_short_form(self):                                          # "1xx" / "2xx" / etc — readable in dashboard panels
        assert str(Enum__CF__Status__Class.SUCCESS)       == '2xx'
        assert str(Enum__CF__Status__Class.CLIENT_ERROR)  == '4xx'
        assert str(Enum__CF__Status__Class.SERVER_ERROR)  == '5xx'

    def test_lookup_by_value(self):
        assert Enum__CF__Status__Class('5xx') == Enum__CF__Status__Class.SERVER_ERROR
