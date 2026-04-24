# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — TestClient integration tests for Fast_API__SP__CLI
# Boots the real FastAPI app with an in-memory Ec2__Service subclass. Checks
# route wiring, path parameters, verb routing, HTTP status codes, and JSON
# response shapes — no real AWS. API-key middleware is active (same shape as
# production) — every request carries the X-API-Key header.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.ec2.enums.Enum__Instance__State                                                     import Enum__Instance__State
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Response                                           import Schema__Ec2__Create__Response
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Instance__Info                                             import Schema__Ec2__Instance__Info
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Preflight                                                  import Schema__Ec2__Preflight
from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                                                          import Fast_API__SP__CLI

from tests.unit.sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service__In_Memory                                      import Ec2__Service__In_Memory


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'
API_KEY_NAME           = 'X-API-Key'
API_KEY_VALUE          = 'test-key-sp-cli'

INSTANCE_ID = 'i-0abcdef1234567890'
DEPLOY_NAME = 'fierce-planck'
IP          = '18.175.230.125'


def build_create_fixture() -> Schema__Ec2__Create__Response:
    preflight = Schema__Ec2__Preflight(aws_account          = '745506449035'                                ,
                                       aws_region           = 'eu-west-2'                                    ,
                                       registry             = '745506449035.dkr.ecr.eu-west-2.amazonaws.com' ,
                                       playwright_image_uri = '745506449035.dkr.ecr.eu-west-2.amazonaws.com/sgraph_ai_service_playwright:latest',
                                       sidecar_image_uri    = '745506449035.dkr.ecr.eu-west-2.amazonaws.com/agent_mitmproxy:latest',
                                       api_key_name         = 'X-API-Key'                                    ,
                                       api_key_generated    = True                                           )
    return Schema__Ec2__Create__Response(instance_id          = INSTANCE_ID                              ,
                                         deploy_name          = DEPLOY_NAME                              ,
                                         stage                = 'dev'                                    ,
                                         creator              = 'test@example.com'                        ,
                                         ami_id               = 'ami-0685f8dd865c8e389'                    ,
                                         public_ip            = IP                                        ,
                                         playwright_url       = f'http://{IP}:8000'                       ,
                                         sidecar_admin_url    = f'http://{IP}:8001'                       ,
                                         browser_url          = f'https://{IP}:3000'                      ,
                                         playwright_image_uri = preflight.playwright_image_uri             ,
                                         sidecar_image_uri    = preflight.sidecar_image_uri                ,
                                         api_key_name         = 'X-API-Key'                                ,
                                         api_key_value        = 'XVI-YLPKzihoP-JPtHCK_zaoNK3_5znKH8dd3e_W0g',
                                         max_hours            = 1                                         ,
                                         preflight            = preflight                                 )


def build_info_fixture() -> Schema__Ec2__Instance__Info:
    return Schema__Ec2__Instance__Info(instance_id          = INSTANCE_ID                   ,
                                       deploy_name          = DEPLOY_NAME                   ,
                                       stage                = 'dev'                         ,
                                       creator              = 'test@example.com'             ,
                                       ami_id               = 'ami-0685f8dd865c8e389'         ,
                                       public_ip            = IP                             ,
                                       playwright_url       = f'http://{IP}:8000'            ,
                                       sidecar_admin_url    = f'http://{IP}:8001'            ,
                                       browser_url          = f'https://{IP}:3000'           ,
                                       api_key_name         = 'X-API-Key'                    ,
                                       api_key_value        = 'XVI-YLPKzihoP-JPtHCK_zaoNK3'   ,
                                       playwright_image_uri = '(stored in compose file on instance)',
                                       sidecar_image_uri    = '(stored in compose file on instance)',
                                       state                = Enum__Instance__State.RUNNING  )


class test_Fast_API__SP__CLI(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        info              = build_info_fixture()
        cls.in_memory     = Ec2__Service__In_Memory(fixture_create    = build_create_fixture()              ,
                                                    fixture_instances = {INSTANCE_ID: info, DEPLOY_NAME: info})
        cls.fast_api      = Fast_API__SP__CLI(ec2_service=cls.in_memory).setup()
        cls.client        = cls.fast_api.client()

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(ENV_VAR__API_KEY_VALUE, None)

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test_post_instances__create(self):
        response = self.client.post('/ec2/instances', headers=self._headers(),
                                                      json={'stage': 'dev', 'max_hours': 1})
        assert response.status_code == 200
        body = response.json()
        assert body['instance_id']                 == INSTANCE_ID
        assert body['deploy_name']                 == DEPLOY_NAME
        assert body['public_ip']                   == IP
        assert body['preflight']['aws_account']    == '745506449035'
        assert body['preflight']['api_key_generated'] is True
        assert body['api_key_value']                != ''                           # Returned once on create
        assert str(self.in_memory.last_create.stage) == 'dev'
        assert int(self.in_memory.last_create.max_hours) == 1

    def test_get_instances__list(self):                                             # GET /ec2/instances — sp list equivalent
        response = self.client.get('/ec2/instances', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['region']            == 'eu-west-2'
        assert len(body['instances'])    == 1
        assert body['instances'][0]['instance_id'] == INSTANCE_ID
        assert body['instances'][0]['deploy_name'] == DEPLOY_NAME

    def test_get_instances_target__by_deploy_name(self):
        response = self.client.get(f'/ec2/instances/{DEPLOY_NAME}', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['instance_id'] == INSTANCE_ID
        assert body['state']       == 'running'

    def test_get_instances_target__by_instance_id(self):
        response = self.client.get(f'/ec2/instances/{INSTANCE_ID}', headers=self._headers())
        assert response.status_code == 200
        assert response.json()['deploy_name'] == DEPLOY_NAME

    def test_get_instances_target__not_found(self):
        response = self.client.get('/ec2/instances/nosuch-thing', headers=self._headers())
        assert response.status_code == 404

    def test_delete_instances_target(self):
        response = self.client.delete(f'/ec2/instances/{DEPLOY_NAME}', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        assert body['terminated_instance_ids'] == [INSTANCE_ID]
        assert body['deploy_name']              == DEPLOY_NAME

    def test_delete_instances_target__not_found(self):
        response = self.client.delete('/ec2/instances/nosuch-thing', headers=self._headers())
        assert response.status_code == 404

    def test_post_instances__rejects_invalid_deploy_name(self):                     # Safe_Str__Deploy_Name regex rejects; exception handler converts ValueError -> 422
        response = self.client.post('/ec2/instances', headers=self._headers(),
                                                      json={'deploy_name': 'NOT_VALID!'})
        assert response.status_code == 422
        body = response.json()
        assert body['detail'][0]['type']      == 'type_safe_value_error'
        assert body['detail'][0]['primitive'] == 'Safe_Str__Deploy_Name'
        assert 'does not match required pattern' in body['detail'][0]['msg']
        assert 'Type-safe primitive rejected'    in body['hint']

    def test_unauthenticated__is_rejected(self):                                    # Sanity — no header = 401
        response = self.client.get(f'/ec2/instances/{DEPLOY_NAME}')
        assert response.status_code == 401
