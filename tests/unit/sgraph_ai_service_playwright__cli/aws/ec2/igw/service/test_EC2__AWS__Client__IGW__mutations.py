# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client IGW mutations
# create_internet_gateway, delete_internet_gateway, attach, detach.
# Covers idempotent attach (Resource.AlreadyAssociated → no-op) and detach (False
# when already detached or IGW not found).
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Internet_Gateway import Schema__EC2__Internet_Gateway
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__create_internet_gateway:

    def test_1__returns_schema(self):
        c   = EC2__AWS__Client__In_Memory()
        igw = c.create_internet_gateway()
        assert isinstance(igw, Schema__EC2__Internet_Gateway)
        assert str(igw.igw_id).startswith('igw-')
        assert str(igw.vpc_id) == ''                                            # newly-created IGWs are detached

    def test_2__deterministic_id(self):
        c = EC2__AWS__Client__In_Memory()
        a = c.create_internet_gateway()
        b = c.create_internet_gateway()
        assert str(a.igw_id) == 'igw-00000001'
        assert str(b.igw_id) == 'igw-00000002'

    def test_3__tags_passed_through(self):
        c   = EC2__AWS__Client__In_Memory()
        igw = c.create_internet_gateway(tags={'Name': 'main-igw'})
        assert str(igw.tags['Name']) == 'main-igw'


class Test__delete_internet_gateway:

    def test_1__deletes_existing(self):
        c     = EC2__AWS__Client__In_Memory()
        igw_id = c.seed_igw(igw_id='igw-11111111')
        assert c.delete_internet_gateway(igw_id) is True
        assert c.describe_internet_gateway(igw_id) is None

    def test_2__returns_false_when_not_found(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.delete_internet_gateway('igw-deadbeef') is False

    def test_3__double_delete_idempotent(self):
        c = EC2__AWS__Client__In_Memory()
        c.seed_igw(igw_id='igw-11111111')
        assert c.delete_internet_gateway('igw-11111111') is True
        assert c.delete_internet_gateway('igw-11111111') is False


class Test__attach_internet_gateway:

    def test_1__attaches_to_vpc(self):
        c = EC2__AWS__Client__In_Memory()
        c.seed_igw(igw_id='igw-11111111')
        c.attach_internet_gateway('igw-11111111', 'vpc-aaaaaaaa')
        igw = c.describe_internet_gateway('igw-11111111')
        assert str(igw.vpc_id) == 'vpc-aaaaaaaa'

    def test_2__already_attached_is_noop(self):
        c = EC2__AWS__Client__In_Memory()
        c.seed_igw(igw_id='igw-11111111', vpc_id='vpc-aaaaaaaa')
        c.attach_internet_gateway('igw-11111111', 'vpc-aaaaaaaa')                # AlreadyAssociated → swallowed
        igw = c.describe_internet_gateway('igw-11111111')
        assert str(igw.vpc_id) == 'vpc-aaaaaaaa'


class Test__detach_internet_gateway:

    def test_1__detaches_attached(self):
        c = EC2__AWS__Client__In_Memory()
        c.seed_igw(igw_id='igw-11111111', vpc_id='vpc-aaaaaaaa')
        assert c.detach_internet_gateway('igw-11111111', 'vpc-aaaaaaaa') is True
        igw = c.describe_internet_gateway('igw-11111111')
        assert str(igw.vpc_id) == ''

    def test_2__detach_not_attached_returns_false(self):
        c = EC2__AWS__Client__In_Memory()
        c.seed_igw(igw_id='igw-11111111')
        assert c.detach_internet_gateway('igw-11111111', 'vpc-aaaaaaaa') is False

    def test_3__detach_missing_igw_returns_false(self):
        c = EC2__AWS__Client__In_Memory()
        assert c.detach_internet_gateway('igw-deadbeef', 'vpc-aaaaaaaa') is False
