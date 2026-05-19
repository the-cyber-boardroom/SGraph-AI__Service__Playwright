# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client VPC mutations (create_vpc, delete_vpc, modify_vpc_attribute)
# In-memory backed; covers create/delete happy + idempotent paths, tag passthrough,
# DNS attribute toggles only touch the attributes explicitly set.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__VPC import Schema__EC2__VPC
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__create_vpc:

    def test_1__returns_vpc_schema(self):
        client = EC2__AWS__Client__In_Memory()
        vpc    = client.create_vpc(cidr='10.0.0.0/16')
        assert isinstance(vpc, Schema__EC2__VPC)
        assert str(vpc.cidr_block) == '10.0.0.0/16'
        assert str(vpc.vpc_id).startswith('vpc-')

    def test_2__deterministic_id_counter(self):
        client = EC2__AWS__Client__In_Memory()
        a = client.create_vpc(cidr='10.0.0.0/16')
        b = client.create_vpc(cidr='10.1.0.0/16')
        assert str(a.vpc_id) == 'vpc-00000001'
        assert str(b.vpc_id) == 'vpc-00000002'

    def test_3__persists_in_store_via_describe(self):
        client = EC2__AWS__Client__In_Memory()
        vpc    = client.create_vpc(cidr='10.0.0.0/16')
        found  = client.describe_vpc(str(vpc.vpc_id))
        assert found is not None
        assert str(found.vpc_id) == str(vpc.vpc_id)

    def test_4__tags_passed_through(self):
        client = EC2__AWS__Client__In_Memory()
        vpc    = client.create_vpc(cidr='10.0.0.0/16', tags={'Name': 'main', 'Env': 'prod'})
        assert str(vpc.tags['Name']) == 'main'
        assert str(vpc.tags['Env'])  == 'prod'

    def test_5__no_tags_emits_no_tag_specifications(self):
        client = EC2__AWS__Client__In_Memory()
        vpc    = client.create_vpc(cidr='10.0.0.0/16')
        assert dict(vpc.tags) == {}


class Test__delete_vpc:

    def test_1__deletes_existing(self):
        client = EC2__AWS__Client__In_Memory()
        vpc_id = client.seed_vpc(vpc_id='vpc-11111111')
        assert client.delete_vpc(vpc_id) is True
        assert client.describe_vpc(vpc_id) is None

    def test_2__returns_false_when_not_found(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.delete_vpc('vpc-deadbeef') is False

    def test_3__idempotent_double_delete(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        assert client.delete_vpc('vpc-11111111') is True
        assert client.delete_vpc('vpc-11111111') is False


class Test__modify_vpc_attribute:

    def test_1__sets_only_dns_support(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.modify_vpc_attribute('vpc-11111111', enable_dns_support=True)
        raw = client._vpcs_store['vpc-11111111']
        assert raw.get('EnableDnsSupport')   is True
        assert 'EnableDnsHostnames' not in raw

    def test_2__sets_only_dns_hostnames(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.modify_vpc_attribute('vpc-11111111', enable_dns_hostnames=True)
        raw = client._vpcs_store['vpc-11111111']
        assert raw.get('EnableDnsHostnames') is True
        assert 'EnableDnsSupport' not in raw

    def test_3__sets_both_when_both_given(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.modify_vpc_attribute('vpc-11111111',
                                     enable_dns_support  =True,
                                     enable_dns_hostnames=True)
        raw = client._vpcs_store['vpc-11111111']
        assert raw['EnableDnsSupport']   is True
        assert raw['EnableDnsHostnames'] is True

    def test_4__no_attrs_makes_no_call(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.modify_vpc_attribute('vpc-11111111')
        raw = client._vpcs_store['vpc-11111111']
        assert 'EnableDnsSupport'   not in raw
        assert 'EnableDnsHostnames' not in raw

    def test_5__can_disable(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.modify_vpc_attribute('vpc-11111111', enable_dns_support=False)
        raw = client._vpcs_store['vpc-11111111']
        assert raw['EnableDnsSupport'] is False
