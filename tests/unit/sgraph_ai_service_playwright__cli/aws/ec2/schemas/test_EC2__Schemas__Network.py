# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2 Network Schemas
# Construction + defaults for Schema__EC2__VPC, Schema__EC2__Subnet,
# Schema__EC2__Internet_Gateway, Schema__EC2__Route, Schema__EC2__Route_Table,
# Schema__EC2__Route_Table_Association. Pure-data schemas — no behaviour.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Internet_Gateway       import Schema__EC2__Internet_Gateway
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Route                  import Schema__EC2__Route
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Route_Table            import Schema__EC2__Route_Table
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Route_Table_Association import Schema__EC2__Route_Table_Association
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Subnet                 import Schema__EC2__Subnet
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__VPC                    import Schema__EC2__VPC


class Test__Schema__EC2__VPC:

    def test_1__default_construction(self):
        v = Schema__EC2__VPC()
        assert str(v.vpc_id)     == ''
        assert str(v.cidr_block) == ''
        assert v.is_default      is False
        assert v.state           == ''
        assert dict(v.tags)      == {}

    def test_2__round_trip_fields(self):
        v = Schema__EC2__VPC(vpc_id='vpc-12345678', cidr_block='10.0.0.0/16',
                              is_default=True, state='available',
                              dhcp_options_id='dopt-12345',
                              instance_tenancy='default')
        assert str(v.vpc_id)           == 'vpc-12345678'
        assert str(v.cidr_block)       == '10.0.0.0/16'
        assert v.is_default            is True
        assert v.state                 == 'available'
        assert v.dhcp_options_id       == 'dopt-12345'
        assert v.instance_tenancy      == 'default'

    def test_3__tags_dict_assignment(self):
        v = Schema__EC2__VPC(vpc_id='vpc-12345678', cidr_block='10.0.0.0/16')
        v.tags['Name'] = 'main'
        v.tags['Env']  = 'prod'
        assert str(v.tags['Name']) == 'main'
        assert str(v.tags['Env'])  == 'prod'


class Test__Schema__EC2__Subnet:

    def test_1__default_construction(self):
        s = Schema__EC2__Subnet()
        assert str(s.subnet_id)             == ''
        assert s.available_ip_count         == 0
        assert s.map_public_ip_on_launch    is False

    def test_2__round_trip_fields(self):
        s = Schema__EC2__Subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-12345678',
                                 cidr_block='10.0.5.0/24', availability_zone='eu-west-2a',
                                 availability_zone_id='euw2-az1',
                                 available_ip_count=251, map_public_ip_on_launch=True,
                                 state='available')
        assert str(s.subnet_id)            == 'subnet-aaaaaaaa'
        assert str(s.vpc_id)               == 'vpc-12345678'
        assert str(s.availability_zone)    == 'eu-west-2a'
        assert s.availability_zone_id      == 'euw2-az1'
        assert s.available_ip_count        == 251
        assert s.map_public_ip_on_launch   is True
        assert s.state                     == 'available'


class Test__Schema__EC2__Internet_Gateway:

    def test_1__default_construction(self):
        i = Schema__EC2__Internet_Gateway()
        assert str(i.igw_id) == ''
        assert str(i.vpc_id) == ''
        assert i.state       == ''

    def test_2__detached_form(self):
        i = Schema__EC2__Internet_Gateway(igw_id='igw-12345678', vpc_id='', state='')
        assert str(i.igw_id) == 'igw-12345678'
        assert str(i.vpc_id) == ''

    def test_3__attached_form(self):
        i = Schema__EC2__Internet_Gateway(igw_id='igw-12345678', vpc_id='vpc-12345678',
                                            state='available')
        assert str(i.vpc_id) == 'vpc-12345678'
        assert i.state       == 'available'


class Test__Schema__EC2__Route:

    def test_1__default_construction(self):
        r = Schema__EC2__Route()
        assert r.destination_cidr == ''
        assert r.gateway_id       == ''

    def test_2__local_route(self):
        r = Schema__EC2__Route(destination_cidr='10.0.0.0/16',
                                gateway_id='local', state='active',
                                origin='CreateRouteTable')
        assert r.gateway_id == 'local'
        assert r.origin     == 'CreateRouteTable'

    def test_3__igw_route(self):
        r = Schema__EC2__Route(destination_cidr='0.0.0.0/0',
                                gateway_id='igw-12345678', state='active',
                                origin='CreateRoute')
        assert r.gateway_id == 'igw-12345678'


class Test__Schema__EC2__Route_Table_Association:

    def test_1__default_construction(self):
        a = Schema__EC2__Route_Table_Association()
        assert a.association_id == ''
        assert a.main           is False

    def test_2__main_table(self):
        a = Schema__EC2__Route_Table_Association(association_id='rtbassoc-12345678',
                                                   route_table_id='rtb-12345678',
                                                   main=True)
        assert a.main is True

    def test_3__subnet_association(self):
        a = Schema__EC2__Route_Table_Association(association_id='rtbassoc-12345678',
                                                   route_table_id='rtb-12345678',
                                                   subnet_id='subnet-aaaaaaaa',
                                                   main=False)
        assert str(a.subnet_id) == 'subnet-aaaaaaaa'
        assert a.main           is False


class Test__Schema__EC2__Route_Table:

    def test_1__default_construction(self):
        rt = Schema__EC2__Route_Table()
        assert str(rt.route_table_id) == ''
        assert list(rt.routes)        == []
        assert list(rt.associations)  == []

    def test_2__routes_collection_appendable(self):
        rt = Schema__EC2__Route_Table(route_table_id='rtb-12345678',
                                       vpc_id='vpc-12345678')
        rt.routes.append(Schema__EC2__Route(destination_cidr='10.0.0.0/16',
                                              gateway_id='local'))
        assert len(rt.routes) == 1

    def test_3__associations_collection_appendable(self):
        rt = Schema__EC2__Route_Table(route_table_id='rtb-12345678',
                                       vpc_id='vpc-12345678')
        rt.associations.append(Schema__EC2__Route_Table_Association(
            association_id='rtbassoc-12345678',
            route_table_id='rtb-12345678',
            subnet_id='subnet-aaaaaaaa'))
        assert len(rt.associations) == 1
