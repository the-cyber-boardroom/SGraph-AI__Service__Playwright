# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client Subnet methods (list_subnets, describe_subnet)
# In-memory backed; covers vpc / az filters, by-id resolution, missing → None,
# field parsing including AZ, available_ip_count, map_public_ip_on_launch, tags.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Subnet import Schema__EC2__Subnet
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_subnets:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        subs   = client.list_subnets()
        assert list(subs) == []

    def test_2__list_all_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb')
        subs = client.list_subnets()
        assert len(subs) == 2

    def test_3__filter_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', vpc_id='vpc-22222222')
        subs = client.list_subnets(vpc_id='vpc-11111111')
        assert len(subs) == 1
        assert str(subs[0].subnet_id) == 'subnet-aaaaaaaa'

    def test_4__filter_by_az(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', az='eu-west-2a')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', az='eu-west-2b')
        subs = client.list_subnets(az='eu-west-2a')
        assert len(subs) == 1
        assert str(subs[0].availability_zone) == 'eu-west-2a'

    def test_5__filter_by_vpc_and_az(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111', az='eu-west-2a')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', vpc_id='vpc-11111111', az='eu-west-2b')
        client.seed_subnet(subnet_id='subnet-cccccccc', vpc_id='vpc-22222222', az='eu-west-2a')
        subs = client.list_subnets(vpc_id='vpc-11111111', az='eu-west-2a')
        assert len(subs) == 1
        assert str(subs[0].subnet_id) == 'subnet-aaaaaaaa'

    def test_6__returns_schema_objects(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa')
        subs = client.list_subnets()
        assert isinstance(subs[0], Schema__EC2__Subnet)

    def test_7__fields_parsed_correctly(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                            cidr='10.0.5.0/24', az='eu-west-2a', az_id='euw2-az1',
                            available_ip_count=200, public=True, state='available',
                            tags={'Tier': 'public'})
        sub = client.list_subnets()[0]
        assert str(sub.subnet_id)              == 'subnet-aaaaaaaa'
        assert str(sub.vpc_id)                 == 'vpc-11111111'
        assert str(sub.cidr_block)             == '10.0.5.0/24'
        assert str(sub.availability_zone)      == 'eu-west-2a'
        assert sub.availability_zone_id        == 'euw2-az1'
        assert sub.available_ip_count          == 200
        assert sub.map_public_ip_on_launch     is True
        assert sub.state                       == 'available'
        assert str(sub.tags['Tier'])           == 'public'


class Test__EC2__AWS__Client__describe_subnet:

    def test_1__returns_schema_for_known_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', az='eu-west-2b')
        sub = client.describe_subnet('subnet-aaaaaaaa')
        assert sub is not None
        assert isinstance(sub, Schema__EC2__Subnet)
        assert str(sub.availability_zone) == 'eu-west-2b'

    def test_2__returns_none_for_unknown_id(self):
        client = EC2__AWS__Client__In_Memory()
        sub    = client.describe_subnet('subnet-deadbeef')
        assert sub is None

    def test_3__public_subnet_flag(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', public=True)
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', public=False)
        a = client.describe_subnet('subnet-aaaaaaaa')
        b = client.describe_subnet('subnet-bbbbbbbb')
        assert a.map_public_ip_on_launch is True
        assert b.map_public_ip_on_launch is False
