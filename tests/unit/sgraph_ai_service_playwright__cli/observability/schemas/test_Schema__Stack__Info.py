# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from osbot_utils.testing.__                                                                                                import __
from osbot_utils.type_safe.Type_Safe                                                                                       import Type_Safe
from osbot_utils.utils.Objects                                                                                             import base_classes

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status                                  import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Endpoint                                    import Safe_Str__AWS__Endpoint
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region                                      import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__Stack__Name                                      import Safe_Str__Stack__Name
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP                                 import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch                          import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Info                                           import Schema__Stack__Info


class test_Schema__Stack__Info(TestCase):

    def test__init__(self):
        with Schema__Stack__Info(name='sp-observe-1', region='eu-west-2') as _:
            assert type(_)          is Schema__Stack__Info
            assert base_classes(_)[0] is Type_Safe
            assert type(_.name)     is Safe_Str__Stack__Name
            assert type(_.region)   is Safe_Str__AWS__Region
            assert _.amp           is None                                          # All components default to None
            assert _.opensearch    is None
            assert _.grafana       is None

    def test__with_components(self):
        amp = Schema__Stack__Component__AMP(workspace_id     = 'ws-abc123'      ,
                                            alias            = 'sp-observe-1'   ,
                                            status           = Enum__Stack__Component__Status.ACTIVE,
                                            remote_write_url = 'https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-abc123/api/v1/remote_write')
        osd = Schema__Stack__Component__OpenSearch(domain_name    = 'sp-observe-1'               ,
                                                   engine_version = 'OpenSearch_3.5'             ,
                                                   status         = Enum__Stack__Component__Status.ACTIVE,
                                                   endpoint       = 'search-xyz.eu-west-2.es.amazonaws.com',
                                                   dashboards_url = 'https://search-xyz.eu-west-2.es.amazonaws.com/_dashboards',
                                                   document_count = 42                            )
        with Schema__Stack__Info(name       = 'sp-observe-1' ,
                                 region     = 'eu-west-2'    ,
                                 amp        = amp            ,
                                 opensearch = osd            ) as _:
            assert type(_.amp)              is Schema__Stack__Component__AMP
            assert type(_.opensearch)       is Schema__Stack__Component__OpenSearch
            assert type(_.amp.status)       is Enum__Stack__Component__Status
            assert _.amp.status             == Enum__Stack__Component__Status.ACTIVE
            assert type(_.opensearch.endpoint) is Safe_Str__AWS__Endpoint

    def test__round_trip_json(self):
        amp = Schema__Stack__Component__AMP(workspace_id     = 'ws-abc123'      ,
                                            alias            = 'sp-observe-1'   ,
                                            status           = Enum__Stack__Component__Status.ACTIVE,
                                            remote_write_url = 'https://example/remote_write')
        with Schema__Stack__Info(name='sp-observe-1', region='eu-west-2', amp=amp) as original:
            json_data = original.json()
            restored  = Schema__Stack__Info.from_json(json_data)
            assert restored.obj() == original.obj()                                 # Full state preserved through serialisation
            assert type(restored.amp)        is Schema__Stack__Component__AMP
            assert restored.amp.status       == Enum__Stack__Component__Status.ACTIVE

    def test__obj_comprehensive(self):
        with Schema__Stack__Info(name='sp-observe-1', region='eu-west-2') as _:
            assert _.obj() == __(name       = 'sp-observe-1',
                                 region     = 'eu-west-2'   ,
                                 amp        = None          ,
                                 opensearch = None          ,
                                 grafana    = None          )
