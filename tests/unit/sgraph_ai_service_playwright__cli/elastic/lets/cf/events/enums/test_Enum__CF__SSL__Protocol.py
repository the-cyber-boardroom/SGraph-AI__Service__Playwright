# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__SSL__Protocol
# Wire values use dotted form ("TLSv1.3"), Python member names use underscore.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__SSL__Protocol import Enum__CF__SSL__Protocol


class test_Enum__CF__SSL__Protocol(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__CF__SSL__Protocol}
        assert names == {'TLSv1_0', 'TLSv1_1', 'TLSv1_2', 'TLSv1_3', 'OTHER'}

    def test_dotted_wire_form(self):                                                # CF emits "TLSv1.3" with the dot — must round-trip
        assert str(Enum__CF__SSL__Protocol.TLSv1_3) == 'TLSv1.3'

    def test_lookup_by_value(self):
        assert Enum__CF__SSL__Protocol('TLSv1.3') == Enum__CF__SSL__Protocol.TLSv1_3
