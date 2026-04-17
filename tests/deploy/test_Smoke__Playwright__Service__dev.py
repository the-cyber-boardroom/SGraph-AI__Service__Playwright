# ═══════════════════════════════════════════════════════════════════════════════
# Lambda smoke test (dev) — SG Playwright Service
#
# Post-deploy smoke against the deployed Function URL: /health/info, /health/status,
# /health/capabilities. Gated on AWS creds + a function URL being resolvable.
#
# API-key middleware is ENABLED on the Lambda (Serverless__Fast_API__Config default).
# Every request must carry the FAST_API__AUTH__API_KEY__NAME header with the
# configured value; an additional test asserts that an unauthenticated request
# is rejected with 401, which is what keeps the Function URL from being open to
# the world.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                           import TestCase

import pytest
import requests

from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import Lambda__Docker__SGraph_AI__Service__Playwright


def _aws_creds_available() -> bool:
    return bool(os.environ.get('AWS_ACCESS_KEY_ID')) and bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))


def _auth_env_available() -> bool:
    return bool(os.environ.get('FAST_API__AUTH__API_KEY__NAME')) and bool(os.environ.get('FAST_API__AUTH__API_KEY__VALUE'))


class test_Smoke__Playwright__Service__dev(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _aws_creds_available():
            pytest.skip('AWS credentials not set — smoke test requires a deployed Lambda')
        if not _auth_env_available():
            pytest.skip('FAST_API__AUTH__API_KEY__NAME/VALUE not set — middleware is active on the Lambda')
        cls.lambda_docker  = Lambda__Docker__SGraph_AI__Service__Playwright()
        cls.lambda_docker.setup()
        cls.function_url   = cls.lambda_docker.function_url()
        if not cls.function_url:
            pytest.skip('Function URL not available — deploy has not run for this stage')
        cls.api_key_name   = os.environ['FAST_API__AUTH__API_KEY__NAME' ]
        cls.api_key_value  = os.environ['FAST_API__AUTH__API_KEY__VALUE']
        cls.auth_headers   = {cls.api_key_name: cls.api_key_value}

    REQUEST_TIMEOUT_S = 30                                                              # Cap: a wedged Lambda must fail smoke in 30 s, not hang until the GH job timeout

    def test_1__health_info(self):
        response = requests.get(f'{self.function_url}health/info', headers=self.auth_headers, timeout=self.REQUEST_TIMEOUT_S)
        assert response.status_code == 200
        data = response.json()
        assert data['service_name']      == 'sg-playwright'
        assert data['deployment_target'] == 'lambda'

    def test_2__health_status(self):
        response = requests.get(f'{self.function_url}health/status', headers=self.auth_headers, timeout=self.REQUEST_TIMEOUT_S)
        assert response.status_code == 200
        assert 'healthy' in response.json()

    def test_3__capabilities(self):
        response = requests.get(f'{self.function_url}health/capabilities', headers=self.auth_headers, timeout=self.REQUEST_TIMEOUT_S)
        assert response.status_code == 200
        caps = response.json()
        assert 'supports_persistent' in caps
        assert 'inline' in caps['supported_sinks']

    def test_4__unauthenticated_is_rejected(self):                                      # Middleware must block requests without the API key
        response = requests.get(f'{self.function_url}health/info', timeout=self.REQUEST_TIMEOUT_S)
        assert response.status_code == 401, f'expected 401 without API key header; got {response.status_code}'
