# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — TestClient integration tests for the observability routes
# Boots Fast_API__SP__CLI with an in-memory Observability__AWS__Client so no
# real AWS is hit. Verifies GET /observability/stacks, GET by name (404 path),
# and DELETE returns the per-component aggregate response.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                                                            import Ec2__Service
from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                                                          import Fast_API__SP__CLI
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status                                  import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP                                 import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch                          import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service                                        import Observability__Service

from tests.unit.sgraph_ai_service_playwright__cli.observability.service.Observability__AWS__Client__In_Memory              import Observability__AWS__Client__In_Memory


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'
API_KEY_NAME           = 'X-API-Key'
API_KEY_VALUE          = 'test-key-sp-cli-obs'

STACK_NAME  = 'sp-observe-1'
OS_ENDPOINT = 'search-xyz.eu-west-2.es.amazonaws.com'


def build_obs_client() -> Observability__AWS__Client__In_Memory:
    amp = Schema__Stack__Component__AMP(workspace_id     = 'ws-111'                                    ,
                                        alias            = STACK_NAME                                  ,
                                        status           = Enum__Stack__Component__Status.ACTIVE       ,
                                        remote_write_url = 'https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-111/api/v1/remote_write')
    osd = Schema__Stack__Component__OpenSearch(domain_name    = STACK_NAME                              ,
                                               engine_version = 'OpenSearch_3.5'                        ,
                                               status         = Enum__Stack__Component__Status.ACTIVE   ,
                                               endpoint       = OS_ENDPOINT                             ,
                                               dashboards_url = f'https://{OS_ENDPOINT}/_dashboards'    ,
                                               document_count = -1                                     )
    return Observability__AWS__Client__In_Memory(fixture_amp             = {STACK_NAME: amp}    ,
                                                 fixture_opensearch      = {STACK_NAME: osd}    ,
                                                 fixture_grafana         = {}                    ,
                                                 fixture_doc_counts      = {OS_ENDPOINT: 42}     ,
                                                 fixture_delete_failures = {}                    ,
                                                 fixture_delete_errors   = {}                    )


class test_Routes__Observability(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        cls.obs_service = Observability__Service(aws_client=build_obs_client())
        cls.fast_api    = Fast_API__SP__CLI(ec2_service           = Ec2__Service()   ,
                                            observability_service = cls.obs_service  ).setup()
        cls.client      = cls.fast_api.client()

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(ENV_VAR__API_KEY_VALUE, None)

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test_get_stacks__lists_known(self):
        response = self.client.get('/observability/stacks', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert len(body['stacks'])        == 1
        assert body['stacks'][0]['name']  == STACK_NAME
        assert body['stacks'][0]['amp']['workspace_id']  == 'ws-111'
        assert body['stacks'][0]['opensearch']['endpoint'] == OS_ENDPOINT

    def test_get_stack__populated_with_doc_count(self):
        response = self.client.get(f'/observability/stacks/{STACK_NAME}', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['name']                       == STACK_NAME
        assert body['opensearch']['document_count'] == 42                             # Topped up via aws_client.opensearch_document_count

    def test_get_stack__not_found(self):
        response = self.client.get('/observability/stacks/sp-no-such', headers=self._headers())
        assert response.status_code == 404

    def test_delete_stack__aggregates_results(self):                                  # 200 with per-component outcomes; no 404 for missing components (that's semantic data)
        response = self.client.delete(f'/observability/stacks/{STACK_NAME}', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['name']          == STACK_NAME
        assert len(body['results']) == 3                                              # One per kind (AMP + OS + AMG)
        kinds = {r['kind'] for r in body['results']}
        assert kinds == {'amp', 'opensearch', 'grafana'}

    def test_unauthenticated__is_rejected(self):
        response = self.client.get('/observability/stacks')
        assert response.status_code == 401
