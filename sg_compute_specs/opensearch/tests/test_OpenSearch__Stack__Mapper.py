# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: tests for OpenSearch__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.opensearch.enums.Enum__OS__Stack__State                       import Enum__OS__Stack__State
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Info                    import Schema__OS__Stack__Info
from sg_compute_specs.opensearch.service.OpenSearch__AWS__Client                    import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY
from sg_compute_specs.opensearch.service.OpenSearch__Stack__Mapper                  import OpenSearch__Stack__Mapper


SAMPLE_DETAILS = {
    'InstanceId'      : 'i-0abc1234567890def',
    'ImageId'         : 'ami-0123456789abcdef0',
    'InstanceType'    : 't3.large',
    'State'           : {'Name': 'running'},
    'PublicIpAddress' : '54.1.2.3',
    'LaunchTime'      : '2026-05-01T12:00:00+00:00',
    'SecurityGroups'  : [{'GroupId': 'sg-0123456789abcdef0'}],
    'Tags'            : [
        {'Key': 'Name'             , 'Value': 'opensearch-cool-newton'},
        {'Key': TAG_STACK_NAME_KEY , 'Value': 'cool-newton'           },
        {'Key': TAG_ALLOWED_IP_KEY , 'Value': '10.0.0.1'             },
    ],
}


class test_OpenSearch__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = OpenSearch__Stack__Mapper()

    def test_to_info__returns_schema_os_stack_info(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert isinstance(info, Schema__OS__Stack__Info)

    def test_to_info__stack_name(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert str(info.stack_name) == 'cool-newton'

    def test_to_info__state_running(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.state == Enum__OS__Stack__State.RUNNING

    def test_to_info__state_terminated(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'terminated'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__OS__Stack__State.TERMINATED

    def test_to_info__state_shutting_down_maps_to_terminating(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'shutting-down'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__OS__Stack__State.TERMINATING

    def test_to_info__dashboards_url_uses_https(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.dashboards_url == 'https://54.1.2.3/'

    def test_to_info__os_endpoint_uses_port_9200(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.os_endpoint == 'https://54.1.2.3:9200/'

    def test_to_info__empty_details_returns_unknown_state(self):
        info = self.mapper.to_info({}, 'eu-west-2')
        assert info.state == Enum__OS__Stack__State.UNKNOWN

    def test_to_info__no_public_ip_yields_empty_urls(self):
        details = {**SAMPLE_DETAILS, 'PublicIpAddress': ''}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.dashboards_url == ''
        assert info.os_endpoint    == ''
