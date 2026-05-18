# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__EC2__Security_Group
# Short round-trip + defaults for the full security-group schema.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__ENI_Id         import Safe_Str__EC2__ENI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id    import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id          import Safe_Str__EC2__SG_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id         import Safe_Str__EC2__VPC_Id
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Security_Group      import Schema__EC2__Security_Group


class Test__Schema__EC2__Security_Group:

    def test_1__defaults_are_empty(self):
        sg = Schema__EC2__Security_Group()
        assert str(sg.sg_id)        == ''
        assert str(sg.name)         == ''
        assert str(sg.vpc_id)       == ''
        assert sg.description       == ''
        assert sg.owner_id          == ''
        assert list(sg.ingress_rules)         == []
        assert list(sg.egress_rules)          == []
        assert list(sg.attached_eni_ids)      == []
        assert list(sg.attached_instance_ids) == []

    def test_2__fields_accept_primitives(self):
        sg = Schema__EC2__Security_Group(
            sg_id       = Safe_Str__EC2__SG_Id('sg-12345678'),
            name        = 'web',
            vpc_id      = Safe_Str__EC2__VPC_Id('vpc-12345678'),
            description = 'web tier',
            owner_id    = '123456789012',
        )
        assert str(sg.sg_id)  == 'sg-12345678'
        assert str(sg.name)   == 'web'
        assert str(sg.vpc_id) == 'vpc-12345678'

    def test_3__attached_lists_appendable(self):
        sg = Schema__EC2__Security_Group(sg_id=Safe_Str__EC2__SG_Id('sg-12345678'))
        sg.attached_eni_ids.append(Safe_Str__EC2__ENI_Id('eni-12345678'))
        sg.attached_instance_ids.append(Safe_Str__EC2__Instance_Id('i-12345678'))
        assert str(sg.attached_eni_ids[0])      == 'eni-12345678'
        assert str(sg.attached_instance_ids[0]) == 'i-12345678'
