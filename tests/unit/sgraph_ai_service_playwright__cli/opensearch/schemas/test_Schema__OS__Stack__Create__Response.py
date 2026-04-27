# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__OS__Stack__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Response import Schema__OS__Stack__Create__Response


class test_Schema__OS__Stack__Create__Response(TestCase):

    def test__defaults(self):
        resp = Schema__OS__Stack__Create__Response()
        assert str(resp.stack_name)        == ''
        assert resp.state                  == Enum__OS__Stack__State.PENDING
        assert str(resp.admin_username)    == 'admin'                                # Default — OpenSearch's built-in superuser
        assert str(resp.admin_password)    == ''

    def test__round_trip_via_json(self):
        resp = Schema__OS__Stack__Create__Response(
            stack_name        = 'os-quiet-fermi'                       ,
            aws_name_tag      = 'opensearch-quiet-fermi'               ,             # Always carries the section prefix
            instance_id       = 'i-0123456789abcdef0'                  ,
            region            = 'eu-west-2'                            ,
            ami_id            = 'ami-0685f8dd865c8e389'                ,
            instance_type     = 'm6i.large'                            ,
            security_group_id = 'sg-1234567890abcdef0'                 ,
            caller_ip         = '1.2.3.4'                              ,
            public_ip         = '5.6.7.8'                              ,
            dashboards_url    = 'https://5.6.7.8/'                     ,
            os_endpoint       = 'https://5.6.7.8:9200/'                ,
            admin_password    = 'AAAA-BBBB-1234-cdef'                  ,
            state             = Enum__OS__Stack__State.RUNNING         )
        again = Schema__OS__Stack__Create__Response.from_json(resp.json())
        assert str(again.stack_name)     == 'os-quiet-fermi'
        assert str(again.aws_name_tag)   == 'opensearch-quiet-fermi'
        assert str(again.instance_id)    == 'i-0123456789abcdef0'
        assert str(again.public_ip)      == '5.6.7.8'                                # Dots preserved
        assert str(again.dashboards_url) == 'https://5.6.7.8/'                       # Scheme preserved
        assert again.state               == Enum__OS__Stack__State.RUNNING
