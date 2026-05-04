# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Prom__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info


class test_Schema__Prom__Stack__Info(TestCase):

    def test__defaults(self):
        info = Schema__Prom__Stack__Info()
        assert str(info.stack_name)     == ''
        assert info.state               == Enum__Prom__Stack__State.UNKNOWN
        assert info.uptime_seconds      == 0

    def test__round_trip_via_json(self):
        info = Schema__Prom__Stack__Info(stack_name        = 'prom-quiet-fermi'    ,
                                          aws_name_tag      = 'prometheus-quiet-fermi',
                                          instance_id       = 'i-0123456789abcdef0' ,
                                          region            = 'eu-west-2'           ,
                                          ami_id            = 'ami-0685f8dd865c8e389',
                                          instance_type     = 't3.medium'           ,
                                          security_group_id = 'sg-1234567890abcdef0',
                                          allowed_ip        = '1.2.3.4'             ,
                                          public_ip         = '5.6.7.8'             ,
                                          prometheus_url    = 'http://5.6.7.8:9090/',
                                          state             = Enum__Prom__Stack__State.READY,
                                          launch_time       = '2026-04-26T10:00:00Z',
                                          uptime_seconds    = 3600                  )
        again = Schema__Prom__Stack__Info.from_json(info.json())
        assert str(again.stack_name)     == 'prom-quiet-fermi'
        assert str(again.public_ip)      == '5.6.7.8'
        assert str(again.prometheus_url) == 'http://5.6.7.8:9090/'                  # Scheme + port preserved
        assert again.state               == Enum__Prom__Stack__State.READY
        assert again.uptime_seconds      == 3600

    def test__never_includes_admin_password(self):                                  # P1: no built-in auth — Info must not leak any password field
        for field in Schema__Prom__Stack__Info.__annotations__:
            assert 'password' not in field.lower(), f'{field} must not leak a password into Info'
