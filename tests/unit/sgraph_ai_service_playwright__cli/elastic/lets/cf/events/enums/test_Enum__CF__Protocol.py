# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__Protocol
# CloudFront emits lowercase wire values (http/https); we keep them lowercase
# so the parser doesn't need to translate.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Protocol import Enum__CF__Protocol


class test_Enum__CF__Protocol(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__CF__Protocol}
        assert names == {'HTTP', 'HTTPS', 'WS', 'WSS', 'OTHER'}

    def test_wire_form_lowercase(self):                                             # CF emits "http" / "https" lowercase — must match
        assert str(Enum__CF__Protocol.HTTP)  == 'http'
        assert str(Enum__CF__Protocol.HTTPS) == 'https'

    def test_lookup_by_value(self):
        assert Enum__CF__Protocol('https') == Enum__CF__Protocol.HTTPS
