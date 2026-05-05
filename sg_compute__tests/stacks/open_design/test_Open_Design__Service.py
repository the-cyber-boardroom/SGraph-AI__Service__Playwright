# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Open_Design__Service
# Uses hand-rolled stub collaborators — no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from unittest import TestCase

from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Request  import Schema__Open_Design__Create__Request
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Response import Schema__Open_Design__Create__Response
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Delete__Response import Schema__Open_Design__Delete__Response
from sg_compute_specs.open_design.schemas.Schema__Open_Design__List             import Schema__Open_Design__List
from sg_compute.platforms.ec2.helpers.EC2__AMI__Helper               import EC2__AMI__Helper
from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper          import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__Launch__Helper            import EC2__Launch__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper                import EC2__SG__Helper
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder             import EC2__Tags__Builder
from sg_compute.platforms.ec2.networking.Caller__IP__Detector                   import Caller__IP__Detector
from sg_compute_specs.open_design.service.Open_Design__AWS__Client              import Open_Design__AWS__Client
from sg_compute_specs.open_design.service.Open_Design__Service                  import Open_Design__Service
from sg_compute_specs.open_design.service.Open_Design__Stack__Mapper            import Open_Design__Stack__Mapper
from sg_compute_specs.open_design.service.Open_Design__User_Data__Builder       import Open_Design__User_Data__Builder
from sg_compute.platforms.ec2.networking.Stack__Name__Generator                        import Stack__Name__Generator

FAKE_INSTANCE = {
    'InstanceId'       : 'i-0feeddeadbeef',
    'InstanceType'     : 't3.large',
    'ImageId'          : 'ami-0123456',
    'PublicIpAddress'  : '1.2.3.4',
    'PrivateIpAddress' : '10.0.0.1',
    'State'            : {'Name': 'running'},
    'LaunchTime'       : datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    'SecurityGroups'   : [{'GroupId': 'sg-0aabbcc', 'GroupName': 'test-sg'}],
    'Tags'             : [
        {'Key': 'StackName', 'Value': 'quiet-fermi'},
        {'Key': 'StackType', 'Value': 'open-design'},
        {'Key': 'CallerIP',  'Value': '5.6.7.8'},
    ],
}


class _FakeSG(EC2__SG__Helper):
    def ensure_security_group(self, region, stack_name, caller_ip, inbound_ports=None):
        return 'sg-fake'
    def delete_security_group(self, region, sg_id):
        return True


class _FakeAMI(EC2__AMI__Helper):
    def latest_al2023_ami(self, region):
        return 'ami-fake'


class _FakeLaunch(EC2__Launch__Helper):
    def run_instance(self, region, ami_id, sg_id, user_data, tags,
                     instance_type='t3.large', instance_profile='',
                     max_hours=0, key_name=''):
        return 'i-fake-instance'


class _FakeInstance(EC2__Instance__Helper):
    def __init__(self, instances=None):
        self._instances = instances or {}

    def list_by_stack_type(self, region, stack_type):
        return self._instances

    def find_by_stack_name(self, region, stack_name):
        for d in self._instances.values():
            for tag in d.get('Tags', []):
                if tag['Key'] == 'StackName' and tag['Value'] == stack_name:
                    return d
        return None

    def terminate(self, region, instance_id):
        return True


class _FakeTags(EC2__Tags__Builder):
    def build(self, stack_name, caller_ip, creator='', extra_tags=None):
        return [{'Key': 'StackName', 'Value': stack_name}]


class _FakeAWSClient(Open_Design__AWS__Client):
    def __init__(self, instances=None):
        object.__setattr__(self, 'sg'      , _FakeSG()             )
        object.__setattr__(self, 'ami'     , _FakeAMI()            )
        object.__setattr__(self, 'launch'  , _FakeLaunch()         )
        object.__setattr__(self, 'tags'    , _FakeTags()           )
        object.__setattr__(self, 'instance', _FakeInstance(instances))


class _FakeIPDetector(Caller__IP__Detector):
    def detect(self):
        return '9.9.9.9'


def _make_service(instances=None):
    svc = Open_Design__Service()
    svc.aws_client        = _FakeAWSClient(instances)
    svc.user_data_builder = Open_Design__User_Data__Builder()
    svc.mapper            = Open_Design__Stack__Mapper()
    svc.ip_detector       = _FakeIPDetector()
    svc.name_gen          = Stack__Name__Generator()
    return svc


class test_Open_Design__Service(TestCase):

    def test_create_stack__returns_create_response(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='my-stack', caller_ip='1.1.1.1',
            from_ami='ami-fixed', region='eu-west-2')
        resp = svc.create_stack(req)
        assert isinstance(resp, Schema__Open_Design__Create__Response)

    def test_create_stack__instance_id_in_response(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='my-stack', caller_ip='1.1.1.1',
            from_ami='ami-fixed', region='eu-west-2')
        resp = svc.create_stack(req)
        assert resp.stack_info.instance_id == 'i-fake-instance'

    def test_create_stack__auto_generates_stack_name(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            caller_ip='1.1.1.1', from_ami='ami-fixed', region='eu-west-2')
        resp = svc.create_stack(req)
        assert '-' in resp.stack_info.stack_name

    def test_create_stack__auto_detects_caller_ip(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='s', from_ami='ami-x', region='eu-west-2')
        resp = svc.create_stack(req)
        assert resp.stack_info.caller_ip == '9.9.9.9'

    def test_create_stack__has_ollama_false_without_url(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='s', caller_ip='1.1.1.1', from_ami='ami-x', region='eu-west-2')
        resp = svc.create_stack(req)
        assert resp.stack_info.has_ollama is False

    def test_create_stack__has_ollama_true_with_url(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='s', caller_ip='1.1.1.1', from_ami='ami-x',
            region='eu-west-2', ollama_base_url='http://10.0.0.5:11434')
        resp = svc.create_stack(req)
        assert resp.stack_info.has_ollama is True

    def test_create_stack__elapsed_ms_non_negative(self):
        svc  = _make_service()
        req  = Schema__Open_Design__Create__Request(
            stack_name='s', caller_ip='1.1.1.1', from_ami='ami-x', region='eu-west-2')
        resp = svc.create_stack(req)
        assert resp.elapsed_ms >= 0

    def test_list_stacks__empty(self):
        svc  = _make_service()
        result = svc.list_stacks('eu-west-2')
        assert isinstance(result, Schema__Open_Design__List)
        assert result.total  == 0
        assert result.stacks == []

    def test_list_stacks__one_instance(self):
        svc    = _make_service({'i-0feeddeadbeef': FAKE_INSTANCE})
        result = svc.list_stacks('eu-west-2')
        assert result.total  == 1
        assert result.stacks[0].instance_id == 'i-0feeddeadbeef'

    def test_get_stack_info__found(self):
        svc  = _make_service({'i-0feeddeadbeef': FAKE_INSTANCE})
        info = svc.get_stack_info('eu-west-2', 'quiet-fermi')
        assert info is not None
        assert info.instance_id == 'i-0feeddeadbeef'

    def test_get_stack_info__not_found(self):
        svc  = _make_service()
        info = svc.get_stack_info('eu-west-2', 'no-such-stack')
        assert info is None

    def test_delete_stack__found(self):
        svc  = _make_service({'i-0feeddeadbeef': FAKE_INSTANCE})
        resp = svc.delete_stack('eu-west-2', 'quiet-fermi')
        assert isinstance(resp, Schema__Open_Design__Delete__Response)
        assert resp.deleted    is True
        assert 'i-0feeddeadbeef' in resp.message

    def test_delete_stack__not_found(self):
        svc  = _make_service()
        resp = svc.delete_stack('eu-west-2', 'ghost-stack')
        assert resp.deleted  is False
        assert 'not found'   in resp.message
