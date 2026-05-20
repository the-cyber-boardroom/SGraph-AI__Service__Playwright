# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for sg_edge enums
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Backend__Type import Enum__SG_Edge__Backend__Type
from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Fleet__State  import Enum__SG_Edge__Fleet__State


class test_Enum__SG_Edge__Backend__Type(TestCase):

    def test_values_match_wire_tokens(self):
        assert Enum__SG_Edge__Backend__Type.EC2.value     == 'ec2'
        assert Enum__SG_Edge__Backend__Type.FARGATE.value == 'fargate'

    def test_str_returns_value(self):                                            # used directly in TXT wire string
        assert str(Enum__SG_Edge__Backend__Type.EC2)     == 'ec2'
        assert str(Enum__SG_Edge__Backend__Type.FARGATE) == 'fargate'

    def test_constructed_from_token(self):
        assert Enum__SG_Edge__Backend__Type('ec2') == Enum__SG_Edge__Backend__Type.EC2


class test_Enum__SG_Edge__Fleet__State(TestCase):

    def test_covers_state_machine(self):
        values = {s.value for s in Enum__SG_Edge__Fleet__State}
        assert values == {'zero', 'booting', 'active', 'scaling', 'draining'}

    def test_str_returns_value(self):
        assert str(Enum__SG_Edge__Fleet__State.ZERO) == 'zero'
