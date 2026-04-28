# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__Lets__Workflow__Type
# Pins the three workflow type values and their string representations.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type import Enum__Lets__Workflow__Type


class test_Enum__Lets__Workflow__Type(TestCase):

    def test_values(self):
        assert Enum__Lets__Workflow__Type.CONSOLIDATE.value == 'consolidate'
        assert Enum__Lets__Workflow__Type.COMPRESS.value    == 'compress'
        assert Enum__Lets__Workflow__Type.EXPAND.value      == 'expand'
        assert Enum__Lets__Workflow__Type.UNKNOWN.value     == 'unknown'

    def test_str(self):
        assert str(Enum__Lets__Workflow__Type.CONSOLIDATE) == 'consolidate'
        assert str(Enum__Lets__Workflow__Type.UNKNOWN)     == 'unknown'
