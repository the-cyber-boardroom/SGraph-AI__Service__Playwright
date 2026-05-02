# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: tests for Docker__Stack__Mapper
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.docker.enums.Enum__Docker__Stack__State                       import Enum__Docker__Stack__State
from sg_compute_specs.docker.schemas.Schema__Docker__Info                           import Schema__Docker__Info
from sg_compute_specs.docker.service.Docker__AWS__Client                            import TAG_STACK_NAME_KEY, TAG_ALLOWED_IP_KEY
from sg_compute_specs.docker.service.Docker__Stack__Mapper                          import Docker__Stack__Mapper


SAMPLE_DETAILS = {
    'InstanceId'  : 'i-0abc1234567890def',
    'ImageId'     : 'ami-0123456789abcdef0',
    'InstanceType': 't3.medium',
    'State'       : {'Name': 'running'},
    'PublicIpAddress': '54.1.2.3',
    'LaunchTime'  : '2026-05-01T12:00:00+00:00',
    'SecurityGroups': [{'GroupId': 'sg-0123456789abcdef0'}],
    'Tags'        : [
        {'Key': 'Name'           , 'Value': 'docker-fast-fermi'},
        {'Key': TAG_STACK_NAME_KEY, 'Value': 'fast-fermi'      },
        {'Key': TAG_ALLOWED_IP_KEY, 'Value': '10.0.0.1'        },
    ],
}


class test_Docker__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Docker__Stack__Mapper()

    def test_to_info__returns_schema_docker_info(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert isinstance(info, Schema__Docker__Info)

    def test_to_info__stack_name(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert str(info.stack_name) == 'fast-fermi'

    def test_to_info__instance_id(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert str(info.instance_id) == 'i-0abc1234567890def'

    def test_to_info__state_running(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.state == Enum__Docker__Stack__State.RUNNING

    def test_to_info__state_terminated(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'terminated'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__Docker__Stack__State.TERMINATED

    def test_to_info__state_shutting_down_maps_to_terminating(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'shutting-down'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__Docker__Stack__State.TERMINATING

    def test_to_info__allowed_ip(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert str(info.allowed_ip) == '10.0.0.1'

    def test_to_info__public_ip(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.public_ip == '54.1.2.3'

    def test_to_info__empty_details_returns_unknown_state(self):
        info = self.mapper.to_info({}, 'eu-west-2')
        assert info.state == Enum__Docker__Stack__State.UNKNOWN
