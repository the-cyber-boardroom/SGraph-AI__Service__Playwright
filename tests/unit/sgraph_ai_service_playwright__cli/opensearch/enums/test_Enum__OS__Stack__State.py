# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Enum__OS__Stack__State
# Lifecycle vocabulary lock-in. Mirrors Enum__Elastic__State.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State              import Enum__OS__Stack__State


class test_Enum__OS__Stack__State(TestCase):

    def test__exhaustive_member_set(self):
        assert {m.name for m in Enum__OS__Stack__State} == {
            'PENDING', 'RUNNING', 'READY', 'TERMINATING', 'TERMINATED', 'UNKNOWN'}

    def test__values_are_lowercase_strings(self):
        for member in Enum__OS__Stack__State:
            assert member.value.islower()
            assert isinstance(member.value, str)

    def test__str_returns_value(self):                                              # Custom __str__ — used by JSON serialisation in Type_Safe schemas
        assert str(Enum__OS__Stack__State.READY) == 'ready'

    def test__shape_matches_elastic(self):                                          # Both sister sections share the same lifecycle vocabulary
        from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State    import Enum__Elastic__State
        assert {m.name for m in Enum__OS__Stack__State} == {m.name for m in Enum__Elastic__State}
        assert {m.value for m in Enum__OS__Stack__State} == {m.value for m in Enum__Elastic__State}
