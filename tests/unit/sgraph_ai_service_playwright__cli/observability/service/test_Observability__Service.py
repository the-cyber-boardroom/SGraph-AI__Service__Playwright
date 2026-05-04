# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Observability__Service (list_stacks + get_stack_info)
# No mocks. Uses Observability__AWS__Client__In_Memory to feed deterministic
# AWS fixture data into the service.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Info                                         import List__Stack__Info
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status                                  import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP                                 import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch                          import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana                             import Schema__Stack__Component__Grafana
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Info                                           import Schema__Stack__Info
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__List                                           import Schema__Stack__List
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service                                        import Observability__Service

from tests.unit.sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client__In_Memory              import Observability__AWS__Client__In_Memory


REGION      = 'eu-west-2'
STACK_ONE   = 'sp-observe-1'
STACK_TWO   = 'sp-observe-2'
OS_ENDPOINT = 'search-xyz.eu-west-2.es.amazonaws.com'


def build_fixture_client() -> Observability__AWS__Client__In_Memory:
    amp = Schema__Stack__Component__AMP(workspace_id     = 'ws-111'                                ,
                                        alias            = STACK_ONE                               ,
                                        status           = Enum__Stack__Component__Status.ACTIVE   ,
                                        remote_write_url = 'https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-111/api/v1/remote_write')
    osd = Schema__Stack__Component__OpenSearch(domain_name    = STACK_ONE                          ,
                                               engine_version = 'OpenSearch_3.5'                   ,
                                               status         = Enum__Stack__Component__Status.ACTIVE,
                                               endpoint       = OS_ENDPOINT                        ,
                                               dashboards_url = f'https://{OS_ENDPOINT}/_dashboards',
                                               document_count = -1                                 )
    amg = Schema__Stack__Component__Grafana(workspace_id = 'g-222'                                 ,
                                            name         = STACK_TWO                               ,
                                            status       = Enum__Stack__Component__Status.CREATING ,
                                            endpoint     = ''                                      ,
                                            url          = ''                                      )
    return Observability__AWS__Client__In_Memory(fixture_amp        = {STACK_ONE: amp  }  ,
                                                 fixture_opensearch = {STACK_ONE: osd  }  ,
                                                 fixture_grafana    = {STACK_TWO: amg  }  ,
                                                 fixture_doc_counts = {OS_ENDPOINT: 1234})


class test_Observability__Service(TestCase):

    @classmethod
    def setUpClass(cls):                                                            # Build fixture once per class — list/info both reuse it
        cls.client  = build_fixture_client()
        cls.service = Observability__Service(aws_client = cls.client)

    def test__init__(self):
        with Observability__Service() as _:                                         # Construct without injection — aws_client auto-initialises
            assert type(_.aws_client) .__name__ == 'Observability__AWS__Client'
            assert _.opensearch_index            == 'sg-playwright-logs'

    def test_list_stacks(self):
        result = self.service.list_stacks(region=REGION)

        assert type(result)        is Schema__Stack__List
        assert type(result.stacks) is List__Stack__Info
        assert str(result.region)  == REGION
        assert len(result.stacks)  == 2                                             # Union of AMP/OS/AMG names — STACK_ONE and STACK_TWO

        names = [str(s.name) for s in result.stacks]
        assert names == sorted([STACK_ONE, STACK_TWO])                              # Deterministic ordering — sorted()

        stack_one = next(s for s in result.stacks if str(s.name) == STACK_ONE)
        assert type(stack_one)            is Schema__Stack__Info
        assert type(stack_one.amp)        is Schema__Stack__Component__AMP
        assert type(stack_one.opensearch) is Schema__Stack__Component__OpenSearch
        assert stack_one.grafana           is None                                  # No AMG for STACK_ONE in fixture

        stack_two = next(s for s in result.stacks if str(s.name) == STACK_TWO)
        assert stack_two.amp        is None                                         # No AMP / OS for STACK_TWO
        assert stack_two.opensearch is None
        assert type(stack_two.grafana) is Schema__Stack__Component__Grafana

    def test_list_stacks__empty_region(self):                                       # Service returns an empty list (not None) when no stacks exist
        empty_client  = Observability__AWS__Client__In_Memory(fixture_amp        = {},
                                                              fixture_opensearch = {},
                                                              fixture_grafana    = {},
                                                              fixture_doc_counts = {})
        empty_service = Observability__Service(aws_client = empty_client)
        result        = empty_service.list_stacks(region = REGION)

        assert type(result)       is Schema__Stack__List
        assert len(result.stacks) == 0

    def test_get_stack_info__with_opensearch(self):
        info = self.service.get_stack_info(name = STACK_ONE, region = REGION)

        assert type(info)                  is Schema__Stack__Info
        assert str(info.name)              == STACK_ONE
        assert str(info.region)            == REGION
        assert info.amp                   is not None
        assert info.opensearch            is not None
        assert info.opensearch.document_count == 1234                               # Topped up from aws_client.opensearch_document_count
        assert info.grafana               is None

    def test_get_stack_info__missing_stack(self):                                   # Asking for a non-existent name returns a Schema__Stack__Info with all components None
        info = self.service.get_stack_info(name = 'sp-no-such', region = REGION)

        assert type(info)     is Schema__Stack__Info
        assert info.amp        is None
        assert info.opensearch is None
        assert info.grafana    is None

    def test_get_stack_info__opensearch_without_endpoint(self):                     # When endpoint is empty the doc count stays at -1 (no round trip attempted)
        osd_pending = Schema__Stack__Component__OpenSearch(domain_name    = 'sp-pending'                        ,
                                                           engine_version = 'OpenSearch_3.5'                    ,
                                                           status         = Enum__Stack__Component__Status.CREATING,
                                                           endpoint       = ''                                  ,
                                                           dashboards_url = ''                                  ,
                                                           document_count = -1                                  )
        pending_client = Observability__AWS__Client__In_Memory(fixture_amp        = {}                         ,
                                                               fixture_opensearch = {'sp-pending': osd_pending} ,
                                                               fixture_grafana    = {}                         ,
                                                               fixture_doc_counts = {}                         )
        pending_service = Observability__Service(aws_client = pending_client)

        info = pending_service.get_stack_info(name = 'sp-pending', region = REGION)
        assert info.opensearch.document_count == -1

    def test_resolve_region__explicit_wins(self):
        assert str(self.service.resolve_region('eu-west-2')) == 'eu-west-2'
        assert str(self.service.resolve_region('us-east-1')) == 'us-east-1'
