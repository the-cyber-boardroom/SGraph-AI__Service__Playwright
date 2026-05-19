# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client Subnet mutations
# create_subnet, delete_subnet, modify_subnet_attribute (map_public_ip_on_launch).
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Subnet import Schema__EC2__Subnet
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


def _client_with_vpc():
    c = EC2__AWS__Client__In_Memory()
    c.seed_vpc(vpc_id='vpc-11111111')
    return c


class Test__create_subnet:

    def test_1__returns_subnet_schema(self):
        c   = _client_with_vpc()
        sub = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.1.0/24')
        assert isinstance(sub, Schema__EC2__Subnet)
        assert str(sub.cidr_block) == '10.0.1.0/24'
        assert str(sub.vpc_id)     == 'vpc-11111111'

    def test_2__deterministic_id(self):
        c = _client_with_vpc()
        a = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.1.0/24')
        b = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.2.0/24')
        assert str(a.subnet_id) == 'subnet-00000001'
        assert str(b.subnet_id) == 'subnet-00000002'

    def test_3__persists_in_store(self):
        c   = _client_with_vpc()
        sub = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.1.0/24')
        assert c.describe_subnet(str(sub.subnet_id)) is not None

    def test_4__az_passed_through(self):
        c   = _client_with_vpc()
        sub = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.1.0/24',
                               availability_zone='eu-west-2b')
        assert str(sub.availability_zone) == 'eu-west-2b'

    def test_5__tags_passed_through(self):
        c   = _client_with_vpc()
        sub = c.create_subnet(vpc_id='vpc-11111111', cidr='10.0.1.0/24',
                               tags={'Name': 'public-a'})
        assert str(sub.tags['Name']) == 'public-a'

    def test_6__missing_vpc_raises(self):
        c = EC2__AWS__Client__In_Memory()
        with pytest.raises(ClientError):
            c.create_subnet(vpc_id='vpc-deadbeef', cidr='10.0.1.0/24')


class Test__delete_subnet:

    def test_1__deletes_existing(self):
        c   = _client_with_vpc()
        sid = c.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        assert c.delete_subnet(sid) is True
        assert c.describe_subnet(sid) is None

    def test_2__returns_false_when_not_found(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.delete_subnet('subnet-deadbeef') is False

    def test_3__double_delete_idempotent(self):
        c = _client_with_vpc()
        c.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        assert c.delete_subnet('subnet-aaaaaaaa') is True
        assert c.delete_subnet('subnet-aaaaaaaa') is False


class Test__modify_subnet_attribute:

    def test_1__sets_map_public_ip_true(self):
        c = _client_with_vpc()
        c.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                       public=False)
        c.modify_subnet_attribute('subnet-aaaaaaaa', map_public_ip_on_launch=True)
        sub = c.describe_subnet('subnet-aaaaaaaa')
        assert sub.map_public_ip_on_launch is True

    def test_2__sets_map_public_ip_false(self):
        c = _client_with_vpc()
        c.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                       public=True)
        c.modify_subnet_attribute('subnet-aaaaaaaa', map_public_ip_on_launch=False)
        sub = c.describe_subnet('subnet-aaaaaaaa')
        assert sub.map_public_ip_on_launch is False

    def test_3__noop_when_no_attr_given(self):
        c = _client_with_vpc()
        c.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                       public=False)
        c.modify_subnet_attribute('subnet-aaaaaaaa')                            # no flag → no call
        sub = c.describe_subnet('subnet-aaaaaaaa')
        assert sub.map_public_ip_on_launch is False
