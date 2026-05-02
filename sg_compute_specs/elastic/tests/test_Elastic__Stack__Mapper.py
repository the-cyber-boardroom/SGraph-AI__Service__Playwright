# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: tests for Elastic__AWS__Client stack mapper
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.elastic.enums.Enum__Elastic__State                            import Enum__Elastic__State
from sg_compute_specs.elastic.schemas.Schema__Elastic__Info                         import Schema__Elastic__Info
from sg_compute_specs.elastic.service.Elastic__AWS__Client                          import (Elastic__AWS__Client,
                                                                                             TAG_ALLOWED_IP_KEY ,
                                                                                             TAG_STACK_NAME_KEY )


SAMPLE_DETAILS = {
    'InstanceId'      : 'i-0abc1234567890def',
    'ImageId'         : 'ami-0123456789abcdef0',
    'InstanceType'    : 'm6i.xlarge',
    'State'           : {'Name': 'running'},
    'PublicIpAddress' : '54.1.2.3',
    'LaunchTime'      : '2026-05-01T12:00:00+00:00',
    'SecurityGroups'  : [{'GroupId': 'sg-0123456789abcdef0'}],
    'Tags'            : [
        {'Key': 'Name'             , 'Value': 'elastic-cool-newton'},
        {'Key': TAG_STACK_NAME_KEY , 'Value': 'cool-newton'        },
        {'Key': TAG_ALLOWED_IP_KEY , 'Value': '10.0.0.1'           },
    ],
    '__region'        : 'eu-west-2',
}


class test_Elastic__Stack__Mapper(TestCase):

    def setUp(self):
        self.client = Elastic__AWS__Client()

    def test_build_instance_info__returns_schema_elastic_info(self):
        info = self.client.build_instance_info(SAMPLE_DETAILS)
        assert isinstance(info, Schema__Elastic__Info)

    def test_build_instance_info__stack_name(self):
        info = self.client.build_instance_info(SAMPLE_DETAILS)
        assert str(info.stack_name) == 'cool-newton'

    def test_build_instance_info__state_running(self):
        info = self.client.build_instance_info(SAMPLE_DETAILS)
        assert info.state == Enum__Elastic__State.RUNNING

    def test_build_instance_info__state_terminated(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'terminated'}}
        info    = self.client.build_instance_info(details)
        assert info.state == Enum__Elastic__State.TERMINATED

    def test_build_instance_info__state_shutting_down_maps_to_terminating(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'shutting-down'}}
        info    = self.client.build_instance_info(details)
        assert info.state == Enum__Elastic__State.TERMINATING

    def test_build_instance_info__kibana_url_uses_https(self):
        info = self.client.build_instance_info(SAMPLE_DETAILS)
        assert info.kibana_url == 'https://54.1.2.3/'

    def test_build_instance_info__empty_state_returns_unknown(self):
        details = {**SAMPLE_DETAILS, 'State': {}}
        info    = self.client.build_instance_info(details)
        assert info.state == Enum__Elastic__State.UNKNOWN

    def test_build_instance_info__no_public_ip_yields_empty_kibana_url(self):
        details = {**SAMPLE_DETAILS, 'PublicIpAddress': ''}
        info    = self.client.build_instance_info(details)
        assert info.kibana_url == ''
