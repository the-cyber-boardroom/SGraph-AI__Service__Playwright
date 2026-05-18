# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Enum__EC2__SG_Rule_Direction
# Value checks for the SG rule direction enum (INGRESS / EGRESS).
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__SG_Rule_Direction import Enum__EC2__SG_Rule_Direction


class Test__Enum__EC2__SG_Rule_Direction:

    def test_1__all_values_present(self):
        expected = {'ingress', 'egress'}
        actual   = {e.value for e in Enum__EC2__SG_Rule_Direction}
        assert expected == actual

    def test_2__string_coercion(self):
        assert str(Enum__EC2__SG_Rule_Direction.INGRESS) == 'ingress'
        assert str(Enum__EC2__SG_Rule_Direction.EGRESS)  == 'egress'

    def test_3__from_string(self):
        assert Enum__EC2__SG_Rule_Direction('ingress') == Enum__EC2__SG_Rule_Direction.INGRESS
        assert Enum__EC2__SG_Rule_Direction('egress')  == Enum__EC2__SG_Rule_Direction.EGRESS

    def test_4__invalid_raises(self):
        with pytest.raises(ValueError):
            Enum__EC2__SG_Rule_Direction('sideways')
