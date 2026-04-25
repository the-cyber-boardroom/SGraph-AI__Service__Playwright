# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__LETS__Stage
# Pins the L/E/T/S vocabulary plus the explicit INDEX value.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Stage import Enum__LETS__Stage


class test_Enum__LETS__Stage(TestCase):

    def test_known_members(self):
        names = {m.name for m in Enum__LETS__Stage}
        assert names == {'LOAD', 'EXTRACT', 'TRANSFORM', 'SAVE', 'INDEX'}           # INDEX is explicit and not part of LETS-proper — Elastic is NOT source of truth

    def test_str_returns_lowercase_value(self):
        assert str(Enum__LETS__Stage.LOAD)      == 'load'
        assert str(Enum__LETS__Stage.EXTRACT)   == 'extract'
        assert str(Enum__LETS__Stage.TRANSFORM) == 'transform'
        assert str(Enum__LETS__Stage.SAVE)      == 'save'
        assert str(Enum__LETS__Stage.INDEX)     == 'index'
