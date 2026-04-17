# ═══════════════════════════════════════════════════════════════════════════════
# test_Deploy__Playwright__Service__base — base class for deploy tests
#
# Follows the SGraph-AI__App__Send pattern: numbered test methods run
# sequentially. Each stage subclass sets `stage` and inherits the flow.
#
# Each stage (dev / main / prod) extends this base and runs three steps:
#   1. create_lambda        — build Lambda from the current ECR image
#   2. invoke /health/info  — event-style payload (no network)
#   3. invoke Function URL  — real HTTP round-trip to the deployed endpoint
#
# Gated on AWS credentials; skipped with a clear reason when unset so local
# runs still collect an item and exit 0.
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest
import requests

from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import Lambda__Docker__SGraph_AI__Service__Playwright


def _aws_creds_available() -> bool:
    return bool(os.environ.get('AWS_ACCESS_KEY_ID')) and bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))


def _auth_env_available() -> bool:
    return bool(os.environ.get('FAST_API__AUTH__API_KEY__NAME')) and bool(os.environ.get('FAST_API__AUTH__API_KEY__VALUE'))


class test_Deploy__Playwright__Service__base():                                         # NOT a TestCase — base only

    stage : str = None

    @classmethod
    def setUpClass(cls):
        if cls.stage is None:
            pytest.skip("Can't run when 'stage' class variable is not set")
        if not _aws_creds_available():
            pytest.skip('AWS credentials not set — deploy test requires real AWS access')
        if not _auth_env_available():
            pytest.skip('FAST_API__AUTH__API_KEY__NAME/VALUE not set — middleware is active on the Lambda')
        cls.lambda_docker = Lambda__Docker__SGraph_AI__Service__Playwright()
        cls.lambda_docker.setup()
        cls.api_key_name  = os.environ['FAST_API__AUTH__API_KEY__NAME' ]
        cls.api_key_value = os.environ['FAST_API__AUTH__API_KEY__VALUE']
        cls.auth_headers  = {cls.api_key_name: cls.api_key_value}

    def test_1__create_lambda(self):
        result = self.lambda_docker.create_lambda(delete_existing = True  ,
                                                   wait_for_active = True )
        assert result.get('create_result', {}).get('status') != 'error'

    def test_2__invoke__health_info(self):                                              # Lambda invoke carries the header inside the event
        payload = {'path'       : '/health/info',
                   'httpMethod' : 'GET'         ,
                   'headers'    : {self.api_key_name: self.api_key_value}}
        result  = self.lambda_docker.lambda_function().invoke(payload)
        body    = result.get('body', '')
        assert 'sg-playwright' in body

    def test_3__invoke__function_url(self):
        function_url = self.lambda_docker.function_url()
        if function_url:
            response = requests.get(f'{function_url}health/status', headers=self.auth_headers)
            assert response.status_code == 200
            assert 'healthy' in response.json()
