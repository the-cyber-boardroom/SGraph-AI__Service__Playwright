# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client Security Group mutations
# create_security_group, authorize_*_ingress/egress, revoke_*_ingress/egress.
# Covers duplicate→False, not-found→False, both CIDR and source-SG variants.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Security_Group import Schema__EC2__Security_Group
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__create_security_group:

    def test_1__returns_schema(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='web tier',
                                       vpc_id='vpc-11111111')
        assert isinstance(sg, Schema__EC2__Security_Group)
        assert str(sg.name)        == 'web'
        assert str(sg.vpc_id)      == 'vpc-11111111'
        assert str(sg.description) == 'web tier'

    def test_2__deterministic_id(self):
        c = EC2__AWS__Client__In_Memory()
        a = c.create_security_group(group_name='a', description='a', vpc_id='vpc-11111111')
        b = c.create_security_group(group_name='b', description='b', vpc_id='vpc-11111111')
        assert str(a.sg_id) == 'sg-00000001'
        assert str(b.sg_id) == 'sg-00000002'

    def test_3__tags_passed_through(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w',
                                       vpc_id='vpc-11111111',
                                       tags={'Name': 'web-sg'})
        # tags surface via describe_security_group response's underlying raw entry
        raw = c._security_groups_store[str(sg.sg_id)]
        assert {t['Key']: t['Value'] for t in raw['Tags']} == {'Name': 'web-sg'}


class Test__authorize_ingress:

    def test_1__adds_cidr_rule(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        added = c.authorize_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                                     cidr_blocks=['0.0.0.0/0'])
        assert added is True

    def test_2__adds_source_sg_rule(self):
        c   = EC2__AWS__Client__In_Memory()
        sg1 = c.create_security_group(group_name='a', description='a', vpc_id='vpc-1')
        sg2 = c.create_security_group(group_name='b', description='b', vpc_id='vpc-1')
        added = c.authorize_security_group_ingress(str(sg1.sg_id), 'tcp', 5432, 5432,
                                                     source_sg_ids=[str(sg2.sg_id)])
        assert added is True

    def test_3__duplicate_returns_false(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        c.authorize_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                             cidr_blocks=['0.0.0.0/0'])
        again = c.authorize_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                                     cidr_blocks=['0.0.0.0/0'])
        assert again is False

    def test_4__rule_visible_via_describe(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        c.authorize_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                             cidr_blocks=['0.0.0.0/0'])
        found = c.describe_security_group(str(sg.sg_id))
        assert any(int(r.from_port) == 80 and str(r.cidr_ipv4) == '0.0.0.0/0'
                   for r in found.ingress_rules)


class Test__authorize_egress:

    def test_1__adds_cidr_rule(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        added = c.authorize_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                                    cidr_blocks=['0.0.0.0/0'])
        assert added is True

    def test_2__duplicate_returns_false(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        c.authorize_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                             cidr_blocks=['0.0.0.0/0'])
        again = c.authorize_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                                    cidr_blocks=['0.0.0.0/0'])
        assert again is False


class Test__revoke_ingress:

    def test_1__removes_existing(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        c.authorize_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                             cidr_blocks=['0.0.0.0/0'])
        assert c.revoke_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                                  cidr_blocks=['0.0.0.0/0']) is True

    def test_2__missing_rule_returns_false(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        assert c.revoke_security_group_ingress(str(sg.sg_id), 'tcp', 80, 80,
                                                  cidr_blocks=['0.0.0.0/0']) is False

    def test_3__missing_sg_returns_false(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.revoke_security_group_ingress('sg-deadbeef', 'tcp', 80, 80,
                                                  cidr_blocks=['0.0.0.0/0']) is False


class Test__revoke_egress:

    def test_1__removes_existing(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        c.authorize_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                             cidr_blocks=['0.0.0.0/0'])
        assert c.revoke_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                                 cidr_blocks=['0.0.0.0/0']) is True

    def test_2__missing_rule_returns_false(self):
        c  = EC2__AWS__Client__In_Memory()
        sg = c.create_security_group(group_name='web', description='w', vpc_id='vpc-1')
        assert c.revoke_security_group_egress(str(sg.sg_id), 'tcp', 443, 443,
                                                 cidr_blocks=['0.0.0.0/0']) is False
