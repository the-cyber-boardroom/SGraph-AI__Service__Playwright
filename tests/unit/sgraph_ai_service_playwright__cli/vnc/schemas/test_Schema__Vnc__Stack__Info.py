# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info


class test_Schema__Vnc__Stack__Info(TestCase):

    def test__defaults(self):
        info = Schema__Vnc__Stack__Info()
        assert str(info.stack_name)        == ''
        assert info.state                  == Enum__Vnc__Stack__State.UNKNOWN
        assert info.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NONE
        assert info.uptime_seconds         == 0

    def test__round_trip_via_json(self):
        info = Schema__Vnc__Stack__Info(
            stack_name        = 'vnc-quiet-fermi'                ,
            aws_name_tag      = 'vnc-quiet-fermi'                ,
            instance_id       = 'i-0123456789abcdef0'            ,
            region            = 'eu-west-2'                      ,
            ami_id            = 'ami-0685f8dd865c8e389'          ,
            instance_type     = 't3.medium'                      ,
            security_group_id = 'sg-1234567890abcdef0'           ,
            allowed_ip        = '1.2.3.4'                        ,
            public_ip         = '5.6.7.8'                        ,
            viewer_url        = 'https://5.6.7.8/'               ,
            mitmweb_url       = 'https://5.6.7.8/mitmweb/'       ,
            interceptor_kind  = Enum__Vnc__Interceptor__Kind.NAME,
            interceptor_name  = 'flow_recorder'                  ,
            state             = Enum__Vnc__Stack__State.READY    ,
            launch_time       = '2026-04-29T10:00:00Z'           ,
            uptime_seconds    = 3600                             )
        again = Schema__Vnc__Stack__Info.from_json(info.json())
        assert str(again.stack_name)         == 'vnc-quiet-fermi'
        assert str(again.viewer_url)         == 'https://5.6.7.8/'
        assert str(again.mitmweb_url)        == 'https://5.6.7.8/mitmweb/'
        assert again.interceptor_kind        == Enum__Vnc__Interceptor__Kind.NAME
        assert str(again.interceptor_name)   == 'flow_recorder'
        assert again.state                   == Enum__Vnc__Stack__State.READY

    def test__never_includes_operator_password(self):                               # Defensive: password lives only on the create response
        for field in Schema__Vnc__Stack__Info.__annotations__:
            assert 'password' not in field.lower(), f'{field} must not leak operator_password into Info'
