# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Observability__Service.delete_stack
# Drives the in-memory AWS client through success, partial-missing, and
# forced-failure paths. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Component__Delete__Result                    import List__Stack__Component__Delete__Result
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Component__Delete__Outcome                                import Enum__Component__Delete__Outcome
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Kind                                    import Enum__Stack__Component__Kind
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status                                  import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP                                 import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana                             import Schema__Stack__Component__Grafana
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch                          import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Delete__Response                               import Schema__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service                                        import Observability__Service

from tests.unit.sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client__In_Memory              import Observability__AWS__Client__In_Memory


REGION    = 'eu-west-2'
STACK     = 'sp-observe-del'


def build_full_stack_client() -> Observability__AWS__Client__In_Memory:             # All three components present
    amp = Schema__Stack__Component__AMP(workspace_id     = 'ws-aaa111'                           ,
                                        alias            = STACK                                 ,
                                        status           = Enum__Stack__Component__Status.ACTIVE ,
                                        remote_write_url = 'https://example/remote_write'        )
    osd = Schema__Stack__Component__OpenSearch(domain_name    = STACK                                 ,
                                               engine_version = 'OpenSearch_3.5'                      ,
                                               status         = Enum__Stack__Component__Status.ACTIVE ,
                                               endpoint       = 'search-abc.eu-west-2.es.amazonaws.com',
                                               dashboards_url = 'https://search-abc.eu-west-2.es.amazonaws.com/_dashboards')
    amg = Schema__Stack__Component__Grafana(workspace_id = 'g-bbb222'                               ,
                                            name         = STACK                                    ,
                                            status       = Enum__Stack__Component__Status.ACTIVE    ,
                                            endpoint     = 'g-bbb222.grafana-workspace.eu-west-2.amazonaws.com',
                                            url          = 'https://g-bbb222.grafana-workspace.eu-west-2.amazonaws.com')
    return Observability__AWS__Client__In_Memory(fixture_amp             = {STACK: amp}  ,
                                                 fixture_opensearch      = {STACK: osd}  ,
                                                 fixture_grafana         = {STACK: amg}  ,
                                                 fixture_doc_counts      = {}            ,
                                                 fixture_delete_failures = {}            ,
                                                 fixture_delete_errors   = {}            )


class test_Observability__Service__delete_stack(TestCase):

    def test_delete_stack__all_components_deleted(self):
        client  = build_full_stack_client()
        service = Observability__Service(aws_client = client)

        response = service.delete_stack(name = STACK, region = REGION)

        assert type(response)         is Schema__Stack__Delete__Response
        assert type(response.results) is List__Stack__Component__Delete__Result
        assert str(response.name)     == STACK
        assert str(response.region)   == REGION
        assert len(response.results)  == 3                                          # One per component, always

        by_kind = {r.kind: r for r in response.results}
        assert by_kind[Enum__Stack__Component__Kind.AMP]       .outcome     == Enum__Component__Delete__Outcome.DELETED
        assert str(by_kind[Enum__Stack__Component__Kind.AMP]   .resource_id) == 'ws-aaa111'
        assert by_kind[Enum__Stack__Component__Kind.OPENSEARCH].outcome     == Enum__Component__Delete__Outcome.DELETED
        assert str(by_kind[Enum__Stack__Component__Kind.OPENSEARCH].resource_id) == STACK
        assert by_kind[Enum__Stack__Component__Kind.GRAFANA]   .outcome     == Enum__Component__Delete__Outcome.DELETED
        assert str(by_kind[Enum__Stack__Component__Kind.GRAFANA].resource_id) == 'g-bbb222'

    def test_delete_stack__all_missing(self):                                       # Empty region — every component reports NOT_FOUND
        empty_client = Observability__AWS__Client__In_Memory(fixture_amp             = {} ,
                                                              fixture_opensearch      = {} ,
                                                              fixture_grafana         = {} ,
                                                              fixture_doc_counts      = {} ,
                                                              fixture_delete_failures = {} ,
                                                              fixture_delete_errors   = {} )
        service = Observability__Service(aws_client = empty_client)

        response = service.delete_stack(name = STACK, region = REGION)

        assert len(response.results) == 3
        for result in response.results:
            assert result.outcome == Enum__Component__Delete__Outcome.NOT_FOUND
            assert str(result.resource_id) == ''
            assert str(result.error_message) == ''

    def test_delete_stack__partial_missing(self):                                   # AMP + OS present, AMG missing — mixed outcomes
        client = build_full_stack_client()
        del client.fixture_grafana[STACK]                                           # Force the Grafana lookup to miss
        service = Observability__Service(aws_client = client)

        response = service.delete_stack(name = STACK, region = REGION)
        by_kind  = {r.kind: r for r in response.results}
        assert by_kind[Enum__Stack__Component__Kind.AMP]       .outcome == Enum__Component__Delete__Outcome.DELETED
        assert by_kind[Enum__Stack__Component__Kind.OPENSEARCH].outcome == Enum__Component__Delete__Outcome.DELETED
        assert by_kind[Enum__Stack__Component__Kind.GRAFANA]   .outcome == Enum__Component__Delete__Outcome.NOT_FOUND

    def test_delete_stack__forced_failure(self):                                    # Simulate AWS returning an error on OpenSearch delete
        client  = build_full_stack_client()
        client.fixture_delete_failures = {Enum__Stack__Component__Kind.OPENSEARCH.value: [STACK]}
        client.fixture_delete_errors   = {Enum__Stack__Component__Kind.OPENSEARCH.value: {STACK: 'Domain is in a non-deletable state'}}
        service = Observability__Service(aws_client = client)

        response = service.delete_stack(name = STACK, region = REGION)
        by_kind  = {r.kind: r for r in response.results}
        assert by_kind[Enum__Stack__Component__Kind.AMP]       .outcome == Enum__Component__Delete__Outcome.DELETED
        assert by_kind[Enum__Stack__Component__Kind.OPENSEARCH].outcome == Enum__Component__Delete__Outcome.FAILED
        assert str(by_kind[Enum__Stack__Component__Kind.OPENSEARCH].error_message) == 'Domain is in a non-deletable state'
        assert by_kind[Enum__Stack__Component__Kind.GRAFANA]   .outcome == Enum__Component__Delete__Outcome.DELETED

    def test_delete_stack__round_trip_json(self):                                   # Response survives JSON serialisation (needed for FastAPI route)
        client   = build_full_stack_client()
        service  = Observability__Service(aws_client = client)
        response = service.delete_stack(name = STACK, region = REGION)

        json_data = response.json()
        restored  = Schema__Stack__Delete__Response.from_json(json_data)
        assert restored.obj() == response.obj()                                     # Full state preserved
