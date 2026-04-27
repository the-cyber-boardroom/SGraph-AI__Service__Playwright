# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__OS__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info


class test_Schema__OS__Stack__Info(TestCase):

    def test__defaults(self):
        info = Schema__OS__Stack__Info()
        assert str(info.stack_name)     == ''
        assert info.state               == Enum__OS__Stack__State.UNKNOWN
        assert info.uptime_seconds      == 0

    def test__round_trip_via_json(self):
        info = Schema__OS__Stack__Info(
            stack_name        = 'os-quiet-fermi'                  ,
            aws_name_tag      = 'opensearch-quiet-fermi'          ,
            instance_id       = 'i-0123456789abcdef0'             ,
            region            = 'eu-west-2'                       ,
            ami_id            = 'ami-0685f8dd865c8e389'           ,
            instance_type     = 'm6i.large'                       ,
            security_group_id = 'sg-1234567890abcdef0'            ,
            allowed_ip        = '1.2.3.4'                         ,
            public_ip         = '5.6.7.8'                         ,
            dashboards_url    = 'https://5.6.7.8/'                ,
            os_endpoint       = 'https://5.6.7.8:9200/'           ,
            state             = Enum__OS__Stack__State.READY      ,
            launch_time       = '2026-04-26T10:00:00Z'            ,
            uptime_seconds    = 3600                              )
        again = Schema__OS__Stack__Info.from_json(info.json())
        assert str(again.stack_name)        == 'os-quiet-fermi'
        assert str(again.public_ip)         == '5.6.7.8'
        assert str(again.os_endpoint)       == 'https://5.6.7.8:9200/'               # Scheme + port preserved
        assert again.state                  == Enum__OS__Stack__State.READY
        assert again.uptime_seconds         == 3600

    def test__never_includes_admin_password(self):                                  # Defensive: password lives only on the create response
        for field in Schema__OS__Stack__Info.__annotations__:
            assert 'password' not in field.lower(), f'{field} must not leak admin_password into Info'
