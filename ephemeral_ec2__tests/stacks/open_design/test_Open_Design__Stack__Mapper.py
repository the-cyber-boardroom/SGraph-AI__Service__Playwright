# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — Open_Design__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from unittest import TestCase

from ephemeral_ec2.stacks.open_design.service.Open_Design__Stack__Mapper import Open_Design__Stack__Mapper
from ephemeral_ec2.stacks.open_design.schemas.Schema__Open_Design__Info  import Schema__Open_Design__Info

FIXTURE = {
    'InstanceId'       : 'i-0abc123def456',
    'InstanceType'     : 't3.large',
    'ImageId'          : 'ami-0deadbeef',
    'PublicIpAddress'  : '3.8.100.200',
    'PrivateIpAddress' : '10.0.1.50',
    'State'            : {'Name': 'running'},
    'LaunchTime'       : datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
    'SecurityGroups'   : [{'GroupId': 'sg-0aabbcc', 'GroupName': 'test-od-sg'}],
    'Tags'             : [
        {'Key': 'Name',          'Value': 'od-quiet-fermi'},
        {'Key': 'StackName',     'Value': 'quiet-fermi'},
        {'Key': 'StackType',     'Value': 'open-design'},
        {'Key': 'CallerIP',      'Value': '1.2.3.4'},
        {'Key': 'OllamaBaseUrl', 'Value': 'http://10.0.0.5:11434'},
    ],
}


class test_Open_Design__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Open_Design__Stack__Mapper()
        self.info   = self.mapper.to_info(FIXTURE, 'eu-west-2')

    def test_returns_schema_type(self):
        assert isinstance(self.info, Schema__Open_Design__Info)

    def test_instance_fields(self):
        assert self.info.instance_id   == 'i-0abc123def456'
        assert self.info.instance_type == 't3.large'
        assert self.info.ami_id        == 'ami-0deadbeef'

    def test_ip_fields(self):
        assert self.info.public_ip  == '3.8.100.200'
        assert self.info.private_ip == '10.0.1.50'

    def test_state(self):
        assert self.info.state == 'running'

    def test_stack_name_from_tag(self):
        assert self.info.stack_name == 'quiet-fermi'

    def test_caller_ip_from_tag(self):
        assert self.info.caller_ip == '1.2.3.4'

    def test_security_group_id(self):
        assert self.info.security_group_id == 'sg-0aabbcc'

    def test_region(self):
        assert self.info.region == 'eu-west-2'

    def test_viewer_url_contains_public_ip(self):
        assert self.info.viewer_url == 'https://3.8.100.200/'

    def test_has_ollama_true_when_tag_present(self):
        assert self.info.has_ollama is True

    def test_has_ollama_false_when_tag_absent(self):
        fixture_no_ollama = dict(FIXTURE)
        fixture_no_ollama['Tags'] = [t for t in FIXTURE['Tags'] if t['Key'] != 'OllamaBaseUrl']
        info = self.mapper.to_info(fixture_no_ollama, 'eu-west-2')
        assert info.has_ollama is False

    def test_uptime_seconds_positive(self):
        assert self.info.uptime_seconds > 0

    def test_no_public_ip_gives_empty_viewer_url(self):
        fixture_no_ip = dict(FIXTURE)
        fixture_no_ip.pop('PublicIpAddress', None)
        info = self.mapper.to_info(fixture_no_ip, 'eu-west-2')
        assert info.viewer_url == ''
