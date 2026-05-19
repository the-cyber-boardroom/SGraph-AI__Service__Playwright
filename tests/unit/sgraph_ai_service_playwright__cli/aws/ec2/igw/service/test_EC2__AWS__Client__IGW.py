# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client IGW methods (list_internet_gateways,
# describe_internet_gateway). In-memory backed; covers attached/detached IGWs,
# vpc filter, by-id resolution, missing → None, tags.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Internet_Gateway import Schema__EC2__Internet_Gateway
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_internet_gateways:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        igws   = client.list_internet_gateways()
        assert list(igws) == []

    def test_2__list_all_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        client.seed_igw(igw_id='igw-22222222')                                  # detached
        igws = client.list_internet_gateways()
        assert len(igws) == 2

    def test_3__filter_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        client.seed_igw(igw_id='igw-22222222', vpc_id='vpc-22222222')
        igws = client.list_internet_gateways(vpc_id='vpc-11111111')
        assert len(igws) == 1
        assert str(igws[0].igw_id) == 'igw-11111111'

    def test_4__detached_igw_excluded_when_vpc_filter_set(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        client.seed_igw(igw_id='igw-22222222')                                  # detached
        igws = client.list_internet_gateways(vpc_id='vpc-11111111')
        assert len(igws) == 1

    def test_5__returns_schema_objects(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        igws = client.list_internet_gateways()
        assert isinstance(igws[0], Schema__EC2__Internet_Gateway)

    def test_6__attached_igw_parses_vpc_id_and_state(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111',
                        state='available', tags={'Name': 'main-gw'})
        igws = client.list_internet_gateways()
        i    = igws[0]
        assert str(i.igw_id)        == 'igw-11111111'
        assert str(i.vpc_id)        == 'vpc-11111111'
        assert i.state              == 'available'
        assert str(i.tags['Name'])  == 'main-gw'

    def test_7__detached_igw_has_empty_vpc_and_state(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        igws = client.list_internet_gateways()
        i    = igws[0]
        assert str(i.vpc_id) == ''
        assert i.state       == ''


class Test__EC2__AWS__Client__describe_internet_gateway:

    def test_1__returns_schema_for_known_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        igw = client.describe_internet_gateway('igw-11111111')
        assert igw is not None
        assert isinstance(igw, Schema__EC2__Internet_Gateway)
        assert str(igw.vpc_id) == 'vpc-11111111'

    def test_2__returns_none_for_unknown_id(self):
        client = EC2__AWS__Client__In_Memory()
        igw    = client.describe_internet_gateway('igw-deadbeef')
        assert igw is None

    def test_3__describe_detached_igw(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        igw = client.describe_internet_gateway('igw-11111111')
        assert igw is not None
        assert str(igw.vpc_id) == ''
