# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__EC2__SG_Rule
# Short round-trip + defaults for the SG rule schema.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__SG_Rule_Direction import Enum__EC2__SG_Rule_Direction
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id    import Safe_Str__EC2__SG_Id
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__SG_Rule       import Schema__EC2__SG_Rule


class Test__Schema__EC2__SG_Rule:

    def test_1__defaults(self):
        rule = Schema__EC2__SG_Rule()
        assert rule.ip_protocol      == ''
        assert rule.from_port        == -1
        assert rule.to_port          == -1
        assert rule.direction        == Enum__EC2__SG_Rule_Direction.INGRESS
        assert rule.cidr_ipv4        == ''
        assert rule.cidr_ipv6        == ''
        assert str(rule.referenced_sg_id) == ''
        assert rule.description      == ''

    def test_2__fields_accept_values(self):
        rule = Schema__EC2__SG_Rule(
            ip_protocol      = 'tcp',
            from_port        = 22,
            to_port          = 22,
            direction        = Enum__EC2__SG_Rule_Direction.INGRESS,
            cidr_ipv4        = '0.0.0.0/0',
            referenced_sg_id = Safe_Str__EC2__SG_Id('sg-12345678'),
            description      = 'ssh',
        )
        assert rule.ip_protocol  == 'tcp'
        assert rule.from_port    == 22
        assert rule.to_port      == 22
        assert rule.direction    == Enum__EC2__SG_Rule_Direction.INGRESS
        assert rule.cidr_ipv4    == '0.0.0.0/0'
        assert str(rule.referenced_sg_id) == 'sg-12345678'
        assert rule.description  == 'ssh'

    def test_3__egress_direction(self):
        rule = Schema__EC2__SG_Rule(direction=Enum__EC2__SG_Rule_Direction.EGRESS)
        assert rule.direction == Enum__EC2__SG_Rule_Direction.EGRESS
