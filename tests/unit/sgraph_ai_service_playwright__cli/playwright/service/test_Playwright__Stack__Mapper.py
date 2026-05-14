# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__Stack__Mapper
# Pure mapper — no AWS calls. Exercises the boto3 detail dict → Info mapping
# including state decoding and sg:with-mitmproxy tag parsing.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client     import (TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY,
                                                                                               TAG_WITH_MITMPROXY_KEY)
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Mapper  import Playwright__Stack__Mapper


def _details(stack_name='playwright-quiet-fermi', state='running',
             public_ip='1.2.3.4', with_mitmproxy='false'):
    return {'InstanceId'     : 'i-0abc1234567890def'                                                       ,
            'ImageId'        : 'ami-0685f8dd865c8e389'                                                     ,
            'InstanceType'   : 't3.medium'                                                                 ,
            'PublicIpAddress': public_ip                                                                    ,
            'State'          : {'Name': state}                                                              ,
            'SecurityGroups' : [{'GroupId': 'sg-1234567890abcdef0'}]                                       ,
            'LaunchTime'     : '2026-05-14T10:00:00Z'                                                      ,
            'Tags'           : [{'Key': 'Name'                 , 'Value': f'playwright-{stack_name}'},
                                {'Key': TAG_STACK_NAME_KEY    , 'Value': stack_name               },
                                {'Key': TAG_ALLOWED_IP_KEY    , 'Value': '9.8.7.6'                },
                                {'Key': TAG_WITH_MITMPROXY_KEY, 'Value': with_mitmproxy           }]}


class test_Playwright__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Playwright__Stack__Mapper()

    def test__running_instance_maps_correctly(self):
        info = self.mapper.to_info(_details(), 'eu-west-2')
        assert str(info.stack_name)        == 'playwright-quiet-fermi'
        assert str(info.instance_id)       == 'i-0abc1234567890def'
        assert str(info.region)            == 'eu-west-2'
        assert str(info.ami_id)            == 'ami-0685f8dd865c8e389'
        assert str(info.instance_type)     == 't3.medium'
        assert str(info.security_group_id) == 'sg-1234567890abcdef0'
        assert str(info.allowed_ip)        == '9.8.7.6'
        assert str(info.public_ip)         == '1.2.3.4'
        assert str(info.playwright_url)    == 'http://1.2.3.4:8000'
        assert str(info.launch_time)       == '2026-05-14T10:00:00Z'
        assert info.state                  == Enum__Playwright__Stack__State.RUNNING

    def test__with_mitmproxy_tag_true(self):
        info = self.mapper.to_info(_details(with_mitmproxy='true'), 'eu-west-2')
        assert info.with_mitmproxy is True

    def test__with_mitmproxy_tag_false(self):
        info = self.mapper.to_info(_details(with_mitmproxy='false'), 'eu-west-2')
        assert info.with_mitmproxy is False

    def test__with_mitmproxy_tag_absent_defaults_to_false(self):
        d = _details()
        d['Tags'] = [t for t in d['Tags'] if t['Key'] != TAG_WITH_MITMPROXY_KEY]
        info = self.mapper.to_info(d, 'eu-west-2')
        assert info.with_mitmproxy is False

    def test__playwright_url_empty_when_no_public_ip(self):
        info = self.mapper.to_info(_details(public_ip=''), 'eu-west-2')
        assert str(info.playwright_url) == ''
        assert str(info.public_ip)      == ''

    # ── state mapping ─────────────────────────────────────────────────────────
    def test__state_pending(self):
        info = self.mapper.to_info(_details(state='pending'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.PENDING

    def test__state_running(self):
        info = self.mapper.to_info(_details(state='running'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.RUNNING

    def test__state_shutting_down_maps_to_terminating(self):
        info = self.mapper.to_info(_details(state='shutting-down'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.TERMINATING

    def test__state_stopped_maps_to_terminated(self):
        info = self.mapper.to_info(_details(state='stopped'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.TERMINATED

    def test__state_terminated(self):
        info = self.mapper.to_info(_details(state='terminated'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.TERMINATED

    def test__state_unknown_for_unmapped_value(self):
        info = self.mapper.to_info(_details(state='banana'), 'eu-west-2')
        assert info.state == Enum__Playwright__Stack__State.UNKNOWN
