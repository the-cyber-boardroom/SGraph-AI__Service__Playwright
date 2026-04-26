# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__CF__Bot__Category
# Four-bucket bot classifier output. UNKNOWN is the safe default when UA is
# empty; HUMAN means classifier explicitly cleared.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category import Enum__CF__Bot__Category


class test_Enum__CF__Bot__Category(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__CF__Bot__Category}
        assert names == {'HUMAN', 'BOT_KNOWN', 'BOT_GENERIC', 'UNKNOWN'}

    def test_lowercase_wire_form(self):                                             # Lowercase wire values match other internal-classifier conventions
        assert str(Enum__CF__Bot__Category.HUMAN)       == 'human'
        assert str(Enum__CF__Bot__Category.BOT_KNOWN)   == 'bot_known'
        assert str(Enum__CF__Bot__Category.BOT_GENERIC) == 'bot_generic'

    def test_lookup_by_value(self):
        assert Enum__CF__Bot__Category('human') == Enum__CF__Bot__Category.HUMAN
