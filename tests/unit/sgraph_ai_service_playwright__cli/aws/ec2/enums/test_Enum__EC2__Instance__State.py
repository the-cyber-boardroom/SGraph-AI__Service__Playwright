# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Enum__EC2__Instance__State
# Tests coverage of all enum values and string coercion.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State import Enum__EC2__Instance__State


class Test__Enum__EC2__Instance__State:

    def test_1__all_values_present(self):
        expected = {'pending', 'running', 'shutting-down', 'terminated', 'stopping', 'stopped', 'unknown'}
        actual   = {e.value for e in Enum__EC2__Instance__State}
        assert expected == actual

    def test_2__string_coercion(self):
        assert str(Enum__EC2__Instance__State.RUNNING)   == 'running'
        assert str(Enum__EC2__Instance__State.STOPPED)   == 'stopped'
        assert str(Enum__EC2__Instance__State.TERMINATED) == 'terminated'
        assert str(Enum__EC2__Instance__State.UNKNOWN)   == 'unknown'

    def test_3__from_string(self):
        assert Enum__EC2__Instance__State('running')       == Enum__EC2__Instance__State.RUNNING
        assert Enum__EC2__Instance__State('shutting-down') == Enum__EC2__Instance__State.SHUTTING_DOWN

    def test_4__invalid_raises(self):
        import pytest
        with pytest.raises(ValueError):
            Enum__EC2__Instance__State('invalid-state')
