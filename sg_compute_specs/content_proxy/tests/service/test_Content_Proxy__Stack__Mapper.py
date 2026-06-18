# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: stack mapper tests (pure, no AWS)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Stack__State          import Enum__Content_Proxy__Stack__State
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.service.Content_Proxy__Stack__Mapper             import Content_Proxy__Stack__Mapper


def _details(state='running', mode='vault_web', tls='letsencrypt'):
    return {'InstanceId'     : 'i-0123456789abcdef0'        ,
            'PublicIpAddress': '18.1.2.3'        ,
            'State'          : {'Name': state}   ,
            'SecurityGroups' : [{'GroupId': 'sg-1'}],
            'Tags'           : [{'Key': 'StackName', 'Value': 'cp-demo'},
                                {'Key': 'cp:mode',   'Value': mode},
                                {'Key': 'cp:tls',    'Value': tls}]}


class test_Content_Proxy__Stack__Mapper(TestCase):

    def test_maps_core_fields(self):
        info = Content_Proxy__Stack__Mapper().to_info(_details(), 'eu-west-2')
        assert str(info.stack_name)  == 'cp-demo'
        assert str(info.instance_id) == 'i-0123456789abcdef0'
        assert str(info.public_ip)   == '18.1.2.3'
        assert str(info.region)      == 'eu-west-2'
        assert info.state == Enum__Content_Proxy__Stack__State.RUNNING
        assert info.mode  == Enum__Content_Proxy__Mode.VAULT_WEB
        assert info.tls   == Enum__Content_Proxy__Tls.LETSENCRYPT

    def test_unknown_state_and_missing_tags_default(self):
        info = Content_Proxy__Stack__Mapper().to_info(
            {'InstanceId': 'i-0aaaaaaaaaaaaaaaa', 'State': {'Name': 'weird'}, 'Tags': []}, 'eu-west-2')
        assert info.state == Enum__Content_Proxy__Stack__State.UNKNOWN
        assert info.mode  == Enum__Content_Proxy__Mode.DIRECT_PROXY                  # default
        assert info.tls   == Enum__Content_Proxy__Tls.NONE                          # default
