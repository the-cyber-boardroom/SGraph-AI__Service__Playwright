# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Stack__Mapper
# Pure mapper — zero AWS calls. Locks the N5 interceptor-tag decoding.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import (TAG_ALLOWED_IP_KEY    ,
                                                                                              TAG_INTERCEPTOR_KEY   ,
                                                                                              TAG_STACK_NAME_KEY    )
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper               import Vnc__Stack__Mapper


def _details(stack_name='vnc-quiet-fermi', allowed_ip='1.2.3.4', state='running', public_ip='5.6.7.8',
             interceptor='none', name_tag='vnc-quiet-fermi'):
    return {
        'InstanceId'     : 'i-0123456789abcdef0'                                        ,
        'ImageId'        : 'ami-0685f8dd865c8e389'                                      ,
        'InstanceType'   : 't3.medium'                                                  ,
        'PublicIpAddress': public_ip                                                     ,
        'State'          : {'Name': state}                                               ,
        'SecurityGroups' : [{'GroupId': 'sg-1234567890abcdef0'}]                         ,
        'LaunchTime'     : '2026-04-29 10:00:00+00:00'                                   ,
        'Tags'           : [{'Key': 'Name'              , 'Value': name_tag           },
                            {'Key': TAG_STACK_NAME_KEY  , 'Value': stack_name         },
                            {'Key': TAG_ALLOWED_IP_KEY  , 'Value': allowed_ip         },
                            {'Key': TAG_INTERCEPTOR_KEY , 'Value': interceptor        }],
    }


class test_Vnc__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Vnc__Stack__Mapper()

    def test_to_info__happy_path(self):
        info = self.mapper.to_info(_details(), 'eu-west-2')
        assert str(info.stack_name)        == 'vnc-quiet-fermi'
        assert str(info.viewer_url)        == 'https://5.6.7.8/'
        assert str(info.mitmweb_url)       == 'https://5.6.7.8/mitmweb/'
        assert info.state                  == Enum__Vnc__Stack__State.RUNNING

    def test_to_info__no_public_ip_yields_empty_urls(self):
        info = self.mapper.to_info(_details(public_ip=''), 'eu-west-2')
        assert str(info.viewer_url)  == ''
        assert str(info.mitmweb_url) == ''

    def test_to_info__interceptor_none(self):
        info = self.mapper.to_info(_details(interceptor='none'), 'eu-west-2')
        assert info.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NONE
        assert str(info.interceptor_name)  == ''

    def test_to_info__interceptor_name(self):                                        # 'name:header_logger' → NAME + 'header_logger'
        info = self.mapper.to_info(_details(interceptor='name:header_logger'), 'eu-west-2')
        assert info.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NAME
        assert str(info.interceptor_name)  == 'header_logger'

    def test_to_info__interceptor_inline(self):                                      # 'inline' → INLINE + 'inline'
        info = self.mapper.to_info(_details(interceptor='inline'), 'eu-west-2')
        assert info.interceptor_kind       == Enum__Vnc__Interceptor__Kind.INLINE
        assert str(info.interceptor_name)  == 'inline'

    def test_to_info__interceptor_unknown_marker_falls_through_to_none(self):        # Defensive
        info = self.mapper.to_info(_details(interceptor='cosmic-ray'), 'eu-west-2')
        assert info.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NONE

    def test_to_info__state_mapping(self):
        for raw, expected in (('pending'      , Enum__Vnc__Stack__State.PENDING    ),
                              ('running'      , Enum__Vnc__Stack__State.RUNNING    ),
                              ('shutting-down', Enum__Vnc__Stack__State.TERMINATING),
                              ('stopped'      , Enum__Vnc__Stack__State.TERMINATED ),
                              ('terminated'   , Enum__Vnc__Stack__State.TERMINATED )):
            info = self.mapper.to_info(_details(state=raw), 'eu-west-2')
            assert info.state == expected
