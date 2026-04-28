# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Prom__Stack__Create__Response
# Defaults + round-trip; defensive "no admin_password" check.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Response import Schema__Prom__Stack__Create__Response


class test_Schema__Prom__Stack__Create__Response(TestCase):

    def test__defaults(self):
        resp = Schema__Prom__Stack__Create__Response()
        assert str(resp.stack_name)     == ''
        assert resp.state               == Enum__Prom__Stack__State.PENDING
        assert resp.targets_count       == 0

    def test__never_includes_admin_password(self):                                  # P1: no built-in auth
        for field in Schema__Prom__Stack__Create__Response.__annotations__:
            assert 'password' not in field.lower(), f'{field} must not introduce a password field'

    def test__round_trip_via_json(self):
        resp = Schema__Prom__Stack__Create__Response(stack_name        = 'prom-quiet-fermi'             ,
                                                      aws_name_tag      = 'prometheus-quiet-fermi'       ,
                                                      instance_id       = 'i-0123456789abcdef0'          ,
                                                      region            = 'eu-west-2'                    ,
                                                      ami_id            = 'ami-0685f8dd865c8e389'        ,
                                                      instance_type     = 't3.medium'                    ,
                                                      security_group_id = 'sg-1234567890abcdef0'         ,
                                                      caller_ip         = '1.2.3.4'                      ,
                                                      public_ip         = '5.6.7.8'                      ,
                                                      prometheus_url    = 'http://5.6.7.8:9090/'         ,
                                                      targets_count     = 2                              ,
                                                      state             = Enum__Prom__Stack__State.RUNNING)
        again = Schema__Prom__Stack__Create__Response.from_json(resp.json())
        assert str(again.stack_name)        == 'prom-quiet-fermi'
        assert str(again.aws_name_tag)      == 'prometheus-quiet-fermi'             # Section prefix carried
        assert str(again.instance_id)       == 'i-0123456789abcdef0'
        assert str(again.public_ip)         == '5.6.7.8'                            # Dots preserved
        assert str(again.prometheus_url)    == 'http://5.6.7.8:9090/'               # Scheme + port preserved
        assert again.targets_count          == 2
        assert again.state                  == Enum__Prom__Stack__State.RUNNING
