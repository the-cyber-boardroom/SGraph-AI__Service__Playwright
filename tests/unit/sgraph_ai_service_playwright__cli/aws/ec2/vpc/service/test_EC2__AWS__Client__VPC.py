# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client VPC methods (list_vpcs, describe_vpc)
# In-memory backed; covers seeded + empty + substring filter, by-id resolution,
# field parsing including tags / state / is_default, missing VPC returns None.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__VPC import Schema__EC2__VPC
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_vpcs:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        vpcs   = client.list_vpcs()
        assert list(vpcs) == []

    def test_2__list_all_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.seed_vpc(vpc_id='vpc-22222222')
        vpcs = client.list_vpcs()
        assert len(vpcs) == 2

    def test_3__returns_schema_ec2_vpc_objects(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        vpcs = client.list_vpcs()
        assert isinstance(vpcs[0], Schema__EC2__VPC)

    def test_4__vpc_id_substring_filter_matches(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-aaaaaaaa')
        client.seed_vpc(vpc_id='vpc-bbbbbbbb')
        vpcs = client.list_vpcs(vpc_id_substring='aaaa')
        assert len(vpcs) == 1
        assert str(vpcs[0].vpc_id) == 'vpc-aaaaaaaa'

    def test_5__vpc_id_substring_filter_no_match(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-aaaaaaaa')
        vpcs = client.list_vpcs(vpc_id_substring='zzzz')
        assert len(vpcs) == 0

    def test_6__tag_filter_passes_through(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', tags={'Name': 'main'})
        client.seed_vpc(vpc_id='vpc-22222222', tags={'Name': 'other'})
        vpcs = client.list_vpcs(tag_filter=[{'Name': 'tag:Name', 'Values': ['main']}])
        assert len(vpcs) == 1
        assert str(vpcs[0].vpc_id) == 'vpc-11111111'

    def test_7__fields_parsed_correctly(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.0.0.0/16',
                        is_default=True, state='available',
                        dhcp_options_id='dopt-12345', instance_tenancy='dedicated',
                        tags={'Name': 'main', 'Env': 'prod'})
        vpcs = client.list_vpcs()
        v    = vpcs[0]
        assert str(v.vpc_id)            == 'vpc-11111111'
        assert str(v.cidr_block)        == '10.0.0.0/16'
        assert v.is_default             is True
        assert v.state                  == 'available'
        assert v.dhcp_options_id        == 'dopt-12345'
        assert v.instance_tenancy       == 'dedicated'
        assert str(v.tags['Name'])      == 'main'
        assert str(v.tags['Env'])       == 'prod'


class Test__EC2__AWS__Client__describe_vpc:

    def test_1__returns_schema_for_known_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.1.0.0/16')
        vpc = client.describe_vpc('vpc-11111111')
        assert vpc is not None
        assert isinstance(vpc, Schema__EC2__VPC)
        assert str(vpc.vpc_id)     == 'vpc-11111111'
        assert str(vpc.cidr_block) == '10.1.0.0/16'

    def test_2__returns_none_for_unknown_id(self):
        client = EC2__AWS__Client__In_Memory()
        vpc    = client.describe_vpc('vpc-deadbeef')
        assert vpc is None

    def test_3__is_default_false_when_not_default(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', is_default=False)
        vpc = client.describe_vpc('vpc-11111111')
        assert vpc is not None
        assert vpc.is_default is False

    def test_4__tags_round_trip(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', tags={'Owner': 'team-a', 'Stack': 'v1'})
        vpc = client.describe_vpc('vpc-11111111')
        assert vpc is not None
        assert str(vpc.tags['Owner']) == 'team-a'
        assert str(vpc.tags['Stack']) == 'v1'
