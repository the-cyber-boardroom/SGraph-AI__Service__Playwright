# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__Method
# Pins the eight HTTP methods + OTHER, and the str-roundtrip Type_Safe relies on.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method import Enum__CF__Method


class test_Enum__CF__Method(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__CF__Method}
        assert names == {'GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH', 'OTHER'}

    def test_str_returns_value(self):
        assert str(Enum__CF__Method.GET) == 'GET'
        assert str(Enum__CF__Method.OTHER) == 'OTHER'

    def test_lookup_by_value(self):
        assert Enum__CF__Method('GET') == Enum__CF__Method.GET
