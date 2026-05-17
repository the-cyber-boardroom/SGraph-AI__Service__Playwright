# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client (in-memory)
# Unit tests for list / describe / tag / start / stop / terminate / create.
# No mocks. No patches. Uses EC2__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State  import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id  import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Create__Request     import Schema__EC2__Create__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client:

    def test_1__list_empty(self):
        client    = EC2__AWS__Client__In_Memory()
        instances = client.list_instances()
        assert len(instances) == 0

    def test_2__list_returns_seeded_instance(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='test-alpha', state='running')
        result = client.list_instances()
        assert len(result) == 1
        inst = result[0]
        assert str(inst.instance_id) == iid
        assert inst.name == 'test-alpha'
        assert inst.state == Enum__EC2__Instance__State.RUNNING

    def test_3__list_filter_by_state(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_instance(name='running-1', state='running')
        client.seed_instance(name='stopped-1', state='stopped')
        running = client.list_instances(state='running')
        stopped = client.list_instances(state='stopped')
        assert len(running) == 1
        assert running[0].name == 'running-1'
        assert len(stopped) == 1
        assert stopped[0].name == 'stopped-1'

    def test_4__describe_existing(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='alpha', public_ip='1.2.3.4')
        detail = client.describe_instance(iid)
        assert detail is not None
        assert str(detail.instance_id) == iid
        assert detail.name             == 'alpha'
        assert detail.public_ip        == '1.2.3.4'

    def test_5__describe_missing_returns_none(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.describe_instance('i-doesnotexist') is None

    def test_6__create_instance(self):
        client  = EC2__AWS__Client__In_Memory()
        request = Schema__EC2__Create__Request(
            name          = 'my-test-instance',
            instance_type = Safe_Str__EC2__Instance__Type('t3.micro'),
            ami_id        = Safe_Str__EC2__AMI_Id('ami-12345678'),
            key_pair      = 'my-key',
        )
        iid = client.create_instance(request)
        assert iid is not None
        assert iid.startswith('i-')
        instances = client.list_instances()
        assert len(instances) == 1
        assert str(instances[0].instance_id) == iid

    def test_7__start_stop_instance(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(state='stopped')
        client.start_instance(iid)
        detail = client.describe_instance(iid)
        assert detail.state == Enum__EC2__Instance__State.RUNNING
        client.stop_instance(iid)
        detail2 = client.describe_instance(iid)
        assert detail2.state == Enum__EC2__Instance__State.STOPPED

    def test_8__terminate_instance(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(state='running')
        client.terminate_instance(iid)
        detail = client.describe_instance(iid)
        assert detail.state == Enum__EC2__Instance__State.TERMINATED

    def test_9__add_and_remove_tags(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='tagged')
        client.add_tags(iid, {'env': 'test', 'owner': 'ci'})
        tags = client.get_instance_tags(iid)
        assert tags.get('env')   == 'test'
        assert tags.get('owner') == 'ci'
        client.remove_tags(iid, ['env'])
        tags2 = client.get_instance_tags(iid)
        assert 'env'   not in tags2
        assert 'owner' in tags2

    def test_10__list_instance_types(self):
        client = EC2__AWS__Client__In_Memory()
        types  = client.list_instance_types()
        assert isinstance(types, list)
        assert len(types) >= 1                                                 # in-memory fake returns fixed list

    def test_11__list_instance_types_family_filter(self):
        client = EC2__AWS__Client__In_Memory()
        types  = client.list_instance_types(family='t3')
        assert all('t3' in t for t in types)
