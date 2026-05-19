# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client Route Table methods (list_route_tables,
# describe_route_table). In-memory backed; covers vpc filter, route parsing
# (local + igw + nat), associations (subnet + main), missing → None.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Route_Table import Schema__EC2__Route_Table
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_route_tables:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        rtbs   = client.list_route_tables()
        assert list(rtbs) == []

    def test_2__list_all_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111')
        client.seed_route_table(rtb_id='rtb-22222222')
        rtbs = client.list_route_tables()
        assert len(rtbs) == 2

    def test_3__filter_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        client.seed_route_table(rtb_id='rtb-22222222', vpc_id='vpc-22222222')
        rtbs = client.list_route_tables(vpc_id='vpc-11111111')
        assert len(rtbs) == 1
        assert str(rtbs[0].route_table_id) == 'rtb-11111111'

    def test_4__returns_schema_objects(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111')
        rtbs = client.list_route_tables()
        assert isinstance(rtbs[0], Schema__EC2__Route_Table)

    def test_5__route_local_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 routes=[{'destination_cidr': '10.0.0.0/16',
                                          'gateway_id'      : 'local'}])
        rtb = client.list_route_tables()[0]
        assert len(rtb.routes) == 1
        assert rtb.routes[0].destination_cidr == '10.0.0.0/16'
        assert rtb.routes[0].gateway_id       == 'local'

    def test_6__route_to_igw_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 routes=[{'destination_cidr': '0.0.0.0/0',
                                          'gateway_id'      : 'igw-12345678'}])
        rtb = client.list_route_tables()[0]
        assert rtb.routes[0].gateway_id == 'igw-12345678'

    def test_7__route_to_nat_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 routes=[{'destination_cidr': '0.0.0.0/0',
                                          'gateway_id'      : 'nat-12345678'}])
        rtb = client.list_route_tables()[0]
        assert rtb.routes[0].gateway_id == 'nat-12345678'

    def test_8__association_subnet_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 associations=[{'association_id': 'rtbassoc-aaaaaaaa',
                                                'subnet_id'     : 'subnet-aaaaaaaa',
                                                'main'          : False}])
        rtb = client.list_route_tables()[0]
        assert len(rtb.associations) == 1
        assert str(rtb.associations[0].subnet_id) == 'subnet-aaaaaaaa'
        assert rtb.associations[0].main is False

    def test_9__association_main_flag(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 associations=[{'association_id': 'rtbassoc-aaaaaaaa',
                                                'subnet_id'     : '',
                                                'main'          : True}])
        rtb = client.list_route_tables()[0]
        assert rtb.associations[0].main is True

    def test_10__tags_round_trip(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 tags={'Name': 'public-rtb'})
        rtb = client.list_route_tables()[0]
        assert str(rtb.tags['Name']) == 'public-rtb'


class Test__EC2__AWS__Client__describe_route_table:

    def test_1__returns_schema_for_known_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        rtb = client.describe_route_table('rtb-11111111')
        assert rtb is not None
        assert isinstance(rtb, Schema__EC2__Route_Table)
        assert str(rtb.route_table_id) == 'rtb-11111111'

    def test_2__returns_none_for_unknown_id(self):
        client = EC2__AWS__Client__In_Memory()
        rtb    = client.describe_route_table('rtb-deadbeef')
        assert rtb is None

    def test_3__routes_and_associations_both_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(
            rtb_id='rtb-11111111', vpc_id='vpc-11111111',
            routes=[{'destination_cidr':'10.0.0.0/16', 'gateway_id':'local'},
                    {'destination_cidr':'0.0.0.0/0',   'gateway_id':'igw-aaaaaaaa'}],
            associations=[{'association_id':'rtbassoc-1', 'subnet_id':'subnet-aaaaaaaa'}])
        rtb = client.describe_route_table('rtb-11111111')
        assert rtb is not None
        assert len(rtb.routes)       == 2
        assert len(rtb.associations) == 1
