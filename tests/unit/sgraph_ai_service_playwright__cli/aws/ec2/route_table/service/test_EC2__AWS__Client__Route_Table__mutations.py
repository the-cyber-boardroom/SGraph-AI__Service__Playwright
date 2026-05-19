# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client Route Table mutations
# create / delete / associate / disassociate / create_route / delete_route.
# Includes the ValueError contract on create_route (must specify exactly one target).
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Route_Table import Schema__EC2__Route_Table
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


def _client_with_vpc():
    c = EC2__AWS__Client__In_Memory()
    c.seed_vpc(vpc_id='vpc-11111111')
    return c


class Test__create_route_table:

    def test_1__returns_schema(self):
        c   = _client_with_vpc()
        rtb = c.create_route_table(vpc_id='vpc-11111111')
        assert isinstance(rtb, Schema__EC2__Route_Table)
        assert str(rtb.vpc_id) == 'vpc-11111111'

    def test_2__deterministic_id(self):
        c = _client_with_vpc()
        a = c.create_route_table(vpc_id='vpc-11111111')
        b = c.create_route_table(vpc_id='vpc-11111111')
        assert str(a.route_table_id) == 'rtb-00000001'
        assert str(b.route_table_id) == 'rtb-00000002'

    def test_3__tags_passed_through(self):
        c   = _client_with_vpc()
        rtb = c.create_route_table(vpc_id='vpc-11111111', tags={'Name': 'public'})
        assert str(rtb.tags['Name']) == 'public'


class Test__delete_route_table:

    def test_1__deletes_existing(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assert c.delete_route_table('rtb-11111111') is True
        assert c.describe_route_table('rtb-11111111') is None

    def test_2__returns_false_when_not_found(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.delete_route_table('rtb-deadbeef') is False

    def test_3__double_delete_idempotent(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assert c.delete_route_table('rtb-11111111') is True
        assert c.delete_route_table('rtb-11111111') is False


class Test__associate_disassociate_route_table:

    def test_1__associate_returns_id(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assoc = c.associate_route_table('rtb-11111111', 'subnet-aaaaaaaa')
        assert assoc.startswith('rtbassoc-')

    def test_2__associate_visible_via_describe(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        c.associate_route_table('rtb-11111111', 'subnet-aaaaaaaa')
        rtb = c.describe_route_table('rtb-11111111')
        assert len(rtb.associations) == 1
        assert str(rtb.associations[0].subnet_id) == 'subnet-aaaaaaaa'

    def test_3__disassociate_returns_true(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assoc = c.associate_route_table('rtb-11111111', 'subnet-aaaaaaaa')
        assert c.disassociate_route_table(assoc) is True

    def test_4__disassociate_unknown_returns_false(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assert c.disassociate_route_table('rtbassoc-deadbeef') is False


class Test__create_route:

    def test_1__exactly_one_target_required__zero(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        with pytest.raises(ValueError):
            c.create_route('rtb-11111111', destination_cidr='0.0.0.0/0')

    def test_2__exactly_one_target_required__multiple(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        with pytest.raises(ValueError):
            c.create_route('rtb-11111111', destination_cidr='0.0.0.0/0',
                            gateway_id='igw-11111111', nat_gateway_id='nat-22')

    def test_3__creates_route_via_igw(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        ok = c.create_route('rtb-11111111', destination_cidr='0.0.0.0/0',
                             gateway_id='igw-11111111')
        assert ok is True
        rtb = c.describe_route_table('rtb-11111111')
        assert any(str(r.destination_cidr) == '0.0.0.0/0' for r in rtb.routes)

    def test_4__creates_route_via_nat(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        c.create_route('rtb-11111111', destination_cidr='10.1.0.0/16',
                        nat_gateway_id='nat-11111111')
        rtb = c.describe_route_table('rtb-11111111')
        assert any(str(r.destination_cidr) == '10.1.0.0/16' for r in rtb.routes)

    def test_5__creates_route_via_eni(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        c.create_route('rtb-11111111', destination_cidr='10.2.0.0/16',
                        network_interface_id='eni-11111111')
        rtb = c.describe_route_table('rtb-11111111')
        cidrs = [str(r.destination_cidr) for r in rtb.routes]
        assert '10.2.0.0/16' in cidrs


class Test__delete_route:

    def test_1__removes_existing(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        c.create_route('rtb-11111111', destination_cidr='0.0.0.0/0',
                        gateway_id='igw-11111111')
        assert c.delete_route('rtb-11111111', destination_cidr='0.0.0.0/0') is True

    def test_2__missing_route_returns_false(self):
        c = _client_with_vpc()
        c.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assert c.delete_route('rtb-11111111', destination_cidr='0.0.0.0/0') is False

    def test_3__missing_rtb_returns_false(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.delete_route('rtb-deadbeef', destination_cidr='0.0.0.0/0') is False
