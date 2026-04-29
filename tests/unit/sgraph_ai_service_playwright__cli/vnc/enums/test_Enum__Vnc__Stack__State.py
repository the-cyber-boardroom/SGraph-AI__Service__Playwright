# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Enum__Vnc__Stack__State
# Locks vocabulary + parity with elastic / opensearch / prometheus.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State


class test_Enum__Vnc__Stack__State(TestCase):

    def test__exhaustive_set(self):
        names = {m.name for m in Enum__Vnc__Stack__State}
        assert names == {'PENDING', 'RUNNING', 'READY', 'TERMINATING', 'TERMINATED', 'UNKNOWN'}

    def test__values_are_lowercase(self):
        for m in Enum__Vnc__Stack__State:
            assert m.value == m.name.lower()

    def test__str_returns_value(self):
        assert str(Enum__Vnc__Stack__State.READY) == 'ready'

    def test__shape_parity_with_other_sister_sections(self):
        from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State    import Enum__OS__Stack__State
        from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State  import Enum__Prom__Stack__State
        assert {m.name for m in Enum__Vnc__Stack__State} == {m.name for m in Enum__OS__Stack__State}
        assert {m.name for m in Enum__Vnc__Stack__State} == {m.name for m in Enum__Prom__Stack__State}
        assert {m.value for m in Enum__Vnc__Stack__State} == {m.value for m in Enum__OS__Stack__State}
