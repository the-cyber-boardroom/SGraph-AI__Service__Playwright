# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: stack mapper tests (pure, no AWS)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Stack__State          import Enum__Content_Proxy__Stack__State
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.service.Content_Proxy__Stack__Mapper             import Content_Proxy__Stack__Mapper, TAG_TERMINATE_AT


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


class test_terminate_at_mapping(TestCase):

    def _details(self, tags):
        return {'InstanceId': 'i-0f5cbb6cd70983071', 'State': {'Name': 'running'},
                'Tags': [{'Key': k, 'Value': v} for k, v in tags.items()]}

    def test_terminate_at_tag_surfaces_time_left(self):                             # the deadman deadline → list/info time-left (the boot-script shutdown fires regardless; this makes it visible)
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(minutes=42)).strftime('%Y-%m-%dT%H:%M:%SZ')
        info = Content_Proxy__Stack__Mapper().to_info(self._details({'StackName': 'smart-darwin', TAG_TERMINATE_AT: future}), 'eu-west-2')
        assert str(info.terminate_at) == future
        assert 2400 <= int(info.time_remaining_sec) <= 2520                          # ~42 min, minus a few seconds

    def test_no_tag_leaves_time_left_blank(self):                                   # back-compat: pre-tag stacks show nothing, not a crash
        info = Content_Proxy__Stack__Mapper().to_info(self._details({'StackName': 'smart-darwin'}), 'eu-west-2')
        assert str(info.terminate_at) == ''
        assert int(info.time_remaining_sec) == 0
