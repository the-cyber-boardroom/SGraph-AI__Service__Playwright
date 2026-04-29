# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Stack__Create__Request
# Defaults + round-trip via .json() so route serialisation stays stable.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request


class test_Schema__Vnc__Stack__Create__Request(TestCase):

    def test__defaults(self):
        req = Schema__Vnc__Stack__Create__Request()
        assert str(req.stack_name)           == ''
        assert str(req.region)               == ''
        assert str(req.instance_type)        == ''
        assert str(req.from_ami)             == ''
        assert str(req.caller_ip)            == ''
        assert req.max_hours                 == 1
        assert str(req.operator_password)    == ''
        assert req.interceptor.kind          == Enum__Vnc__Interceptor__Kind.NONE   # N5 default-off

    def test__round_trip_via_json__name_interceptor(self):
        interceptor = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger')
        original = Schema__Vnc__Stack__Create__Request(stack_name        = 'vnc-quiet-fermi',
                                                        region            = 'eu-west-2',
                                                        instance_type     = 't3.medium',
                                                        caller_ip         = '1.2.3.4',
                                                        max_hours         = 4,
                                                        operator_password = 'AAAA-BBBB-1234-cdef',
                                                        interceptor       = interceptor)
        again = Schema__Vnc__Stack__Create__Request.from_json(original.json())
        assert str(again.stack_name)              == 'vnc-quiet-fermi'
        assert str(again.region)                  == 'eu-west-2'
        assert str(again.instance_type)           == 't3.medium'
        assert str(again.caller_ip)               == '1.2.3.4'
        assert again.max_hours                    == 4
        assert str(again.operator_password)       == 'AAAA-BBBB-1234-cdef'
        assert again.interceptor.kind             == Enum__Vnc__Interceptor__Kind.NAME
        assert str(again.interceptor.name)        == 'header_logger'
