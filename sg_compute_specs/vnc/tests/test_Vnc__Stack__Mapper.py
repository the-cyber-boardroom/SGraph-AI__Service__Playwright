# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: tests for Vnc__Stack__Mapper
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.enums.Enum__Vnc__Stack__State                             import Enum__Vnc__Stack__State
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Info                          import Schema__Vnc__Stack__Info
from sg_compute_specs.vnc.service.Vnc__AWS__Client                                  import (TAG_ALLOWED_IP_KEY   ,
                                                                                             TAG_INTERCEPTOR_KEY  ,
                                                                                             TAG_INTERCEPTOR_NONE ,
                                                                                             TAG_STACK_NAME_KEY   )
from sg_compute_specs.vnc.service.Vnc__Stack__Mapper                                import Vnc__Stack__Mapper


SAMPLE_DETAILS = {
    'InstanceId'     : 'i-0abc1234567890def',
    'ImageId'        : 'ami-0123456789abcdef0',
    'InstanceType'   : 't3.large',
    'State'          : {'Name': 'running'},
    'PublicIpAddress': '54.1.2.3',
    'LaunchTime'     : '2026-05-01T12:00:00+00:00',
    'SecurityGroups' : [{'GroupId': 'sg-0123456789abcdef0'}],
    'Tags'           : [
        {'Key': 'Name'              , 'Value': 'vnc-fast-fermi' },
        {'Key': TAG_STACK_NAME_KEY  , 'Value': 'fast-fermi'     },
        {'Key': TAG_ALLOWED_IP_KEY  , 'Value': '10.0.0.1'       },
        {'Key': TAG_INTERCEPTOR_KEY , 'Value': TAG_INTERCEPTOR_NONE},
    ],
}


class test_Vnc__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Vnc__Stack__Mapper()

    def test_to_info__returns_schema_vnc_stack_info(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert isinstance(info, Schema__Vnc__Stack__Info)

    def test_to_info__stack_name(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert str(info.stack_name) == 'fast-fermi'

    def test_to_info__state_running(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.state == Enum__Vnc__Stack__State.RUNNING

    def test_to_info__state_terminated(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'terminated'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__Vnc__Stack__State.TERMINATED

    def test_to_info__state_shutting_down_maps_to_terminating(self):
        details = {**SAMPLE_DETAILS, 'State': {'Name': 'shutting-down'}}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.state == Enum__Vnc__Stack__State.TERMINATING

    def test_to_info__viewer_url_constructed_from_public_ip(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.viewer_url == 'https://54.1.2.3/'

    def test_to_info__mitmweb_url_constructed_from_public_ip(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.mitmweb_url == 'https://54.1.2.3/mitmweb/'

    def test_to_info__interceptor_none_tag(self):
        info = self.mapper.to_info(SAMPLE_DETAILS, 'eu-west-2')
        assert info.interceptor_kind == Enum__Vnc__Interceptor__Kind.NONE
        assert info.interceptor_name == ''

    def test_to_info__interceptor_name_tag(self):
        details = {**SAMPLE_DETAILS, 'Tags': [
            *SAMPLE_DETAILS['Tags'][:-1],
            {'Key': TAG_INTERCEPTOR_KEY, 'Value': 'name:header_logger'},
        ]}
        info = self.mapper.to_info(details, 'eu-west-2')
        assert info.interceptor_kind == Enum__Vnc__Interceptor__Kind.NAME
        assert info.interceptor_name == 'header_logger'

    def test_to_info__interceptor_inline_tag(self):
        details = {**SAMPLE_DETAILS, 'Tags': [
            *SAMPLE_DETAILS['Tags'][:-1],
            {'Key': TAG_INTERCEPTOR_KEY, 'Value': 'inline'},
        ]}
        info = self.mapper.to_info(details, 'eu-west-2')
        assert info.interceptor_kind == Enum__Vnc__Interceptor__Kind.INLINE

    def test_to_info__empty_details_returns_unknown_state(self):
        info = self.mapper.to_info({}, 'eu-west-2')
        assert info.state == Enum__Vnc__Stack__State.UNKNOWN

    def test_to_info__no_public_ip_yields_empty_urls(self):
        details = {**SAMPLE_DETAILS, 'PublicIpAddress': ''}
        info    = self.mapper.to_info(details, 'eu-west-2')
        assert info.viewer_url  == ''
        assert info.mitmweb_url == ''
