# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Stack__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Response import Schema__Vnc__Stack__Create__Response


class test_Schema__Vnc__Stack__Create__Response(TestCase):

    def test__defaults(self):
        resp = Schema__Vnc__Stack__Create__Response()
        assert str(resp.stack_name)           == ''
        assert resp.state                     == Enum__Vnc__Stack__State.PENDING
        assert resp.interceptor_kind          == Enum__Vnc__Interceptor__Kind.NONE
        assert str(resp.operator_username)    == 'operator'
        assert str(resp.operator_password)    == ''

    def test__round_trip_via_json(self):
        resp = Schema__Vnc__Stack__Create__Response(
            stack_name        = 'vnc-quiet-fermi'                       ,
            aws_name_tag      = 'vnc-quiet-fermi'                       ,
            instance_id       = 'i-0123456789abcdef0'                   ,
            region            = 'eu-west-2'                             ,
            ami_id            = 'ami-0685f8dd865c8e389'                 ,
            instance_type     = 't3.medium'                             ,
            security_group_id = 'sg-1234567890abcdef0'                  ,
            caller_ip         = '1.2.3.4'                               ,
            public_ip         = '5.6.7.8'                               ,
            viewer_url        = 'https://5.6.7.8/'                      ,
            mitmweb_url       = 'https://5.6.7.8/mitmweb/'              ,
            operator_password = 'AAAA-BBBB-1234-cdef'                   ,
            interceptor_kind  = Enum__Vnc__Interceptor__Kind.NAME       ,
            interceptor_name  = 'header_logger'                         ,
            state             = Enum__Vnc__Stack__State.RUNNING         )
        again = Schema__Vnc__Stack__Create__Response.from_json(resp.json())
        assert str(again.stack_name)        == 'vnc-quiet-fermi'
        assert str(again.aws_name_tag)      == 'vnc-quiet-fermi'                    # No double prefix even with same form
        assert str(again.viewer_url)        == 'https://5.6.7.8/'
        assert str(again.mitmweb_url)       == 'https://5.6.7.8/mitmweb/'
        assert again.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NAME
        assert str(again.interceptor_name)  == 'header_logger'
        assert again.state                  == Enum__Vnc__Stack__State.RUNNING
