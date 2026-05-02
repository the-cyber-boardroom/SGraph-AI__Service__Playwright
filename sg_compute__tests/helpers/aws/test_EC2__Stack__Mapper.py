# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — EC2__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

import datetime
from unittest import TestCase

from sg_compute.helpers.aws.EC2__Stack__Mapper import EC2__Stack__Mapper, tag_value, state_str

FIXTURE = {
    'InstanceId'       : 'i-0123456789abcdef0',
    'ImageId'          : 'ami-0abc1234',
    'InstanceType'     : 't3.large',
    'State'            : {'Name': 'running'},
    'PublicIpAddress'  : '54.1.2.3',
    'PrivateIpAddress' : '10.0.1.5',
    'LaunchTime'       : datetime.datetime(2026, 5, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
    'SecurityGroups'   : [{'GroupId': 'sg-0abc123', 'GroupName': 'quiet-fermi-sg'}],
    'Tags'             : [
        {'Key': 'StackName' , 'Value': 'quiet-fermi'  },
        {'Key': 'StackType' , 'Value': 'open-design'  },
        {'Key': 'CallerIP'  , 'Value': '99.1.2.3'     },
        {'Key': 'Purpose'   , 'Value': 'ephemeral-ec2'},
    ],
}


class test_EC2__Stack__Mapper(TestCase):

    def test_to_info__instance_id(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.instance_id == 'i-0123456789abcdef0'

    def test_to_info__stack_name_from_tag(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.stack_name == 'quiet-fermi'

    def test_to_info__state(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.state == 'running'

    def test_to_info__ips(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.public_ip  == '54.1.2.3'
        assert info.private_ip == '10.0.1.5'

    def test_to_info__sg_id(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.security_group_id == 'sg-0abc123'

    def test_to_info__uptime_positive(self):
        info = EC2__Stack__Mapper().to_info(FIXTURE, 'eu-west-2')
        assert info.uptime_seconds > 0

    def test_tag_value__missing_key_returns_empty(self):
        assert tag_value(FIXTURE, 'NonExistent') == ''

    def test_state_str__dict_form(self):
        assert state_str({'State': {'Name': 'pending'}}) == 'pending'

    def test_state_str__missing(self):
        assert state_str({}) == ''
