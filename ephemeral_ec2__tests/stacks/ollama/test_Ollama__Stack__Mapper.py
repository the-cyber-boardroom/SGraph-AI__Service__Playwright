# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — Ollama__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from unittest import TestCase

from ephemeral_ec2.stacks.ollama.service.Ollama__Stack__Mapper import Ollama__Stack__Mapper, gpu_count_for
from ephemeral_ec2.stacks.ollama.schemas.Schema__Ollama__Info  import Schema__Ollama__Info

FIXTURE = {
    'InstanceId'       : 'i-0gpu1234abcd',
    'InstanceType'     : 'g4dn.xlarge',
    'ImageId'          : 'ami-0beef',
    'PublicIpAddress'  : '3.8.200.100',
    'PrivateIpAddress' : '10.0.2.30',
    'State'            : {'Name': 'running'},
    'LaunchTime'       : datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc),
    'SecurityGroups'   : [{'GroupId': 'sg-0ffcc11', 'GroupName': 'test-ol-sg'}],
    'Tags'             : [
        {'Key': 'StackName',  'Value': 'swift-turing'},
        {'Key': 'StackType',  'Value': 'ollama'},
        {'Key': 'StackModel', 'Value': 'qwen2.5-coder:7b'},
        {'Key': 'CallerIP',   'Value': '5.5.5.5'},
    ],
}


class test_Ollama__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Ollama__Stack__Mapper()
        self.info   = self.mapper.to_info(FIXTURE, 'eu-west-2')

    def test_returns_schema_type(self):
        assert isinstance(self.info, Schema__Ollama__Info)

    def test_instance_fields(self):
        assert self.info.instance_id   == 'i-0gpu1234abcd'
        assert self.info.instance_type == 'g4dn.xlarge'
        assert self.info.ami_id        == 'ami-0beef'

    def test_ip_fields(self):
        assert self.info.public_ip  == '3.8.200.100'
        assert self.info.private_ip == '10.0.2.30'

    def test_state(self):
        assert self.info.state == 'running'

    def test_stack_name_from_tag(self):
        assert self.info.stack_name == 'swift-turing'

    def test_model_name_from_tag(self):
        assert self.info.model_name == 'qwen2.5-coder:7b'

    def test_security_group_id(self):
        assert self.info.security_group_id == 'sg-0ffcc11'

    def test_region(self):
        assert self.info.region == 'eu-west-2'

    def test_api_base_url_uses_private_ip(self):
        assert self.info.api_base_url == 'http://10.0.2.30:11434/v1'

    def test_uptime_seconds_positive(self):
        assert self.info.uptime_seconds > 0

    def test_gpu_count_for_g4dn(self):
        assert gpu_count_for('g4dn.xlarge') == 1

    def test_gpu_count_for_g5(self):
        assert gpu_count_for('g5.12xlarge') == 1

    def test_gpu_count_for_cpu_instance(self):
        assert gpu_count_for('c7i.4xlarge') == 0
        assert gpu_count_for('t3.large')    == 0

    def test_gpu_count_in_info(self):
        assert self.info.gpu_count == 1

    def test_no_private_ip_gives_empty_api_base_url(self):
        fixture_no_ip = dict(FIXTURE)
        fixture_no_ip.pop('PrivateIpAddress', None)
        info = self.mapper.to_info(fixture_no_ip, 'eu-west-2')
        assert info.api_base_url == ''
