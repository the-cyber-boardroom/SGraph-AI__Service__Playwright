# ═══════════════════════════════════════════════════════════════════════════════
# Lambda smoke test (dev) — SG Playwright Service
#
# Post-deploy smoke against the deployed Function URL: /health/info, /health/status,
# /health/capabilities. Gated on AWS creds + a function URL being resolvable.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                           import TestCase

import pytest
import requests

from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import Lambda__Docker__SGraph_AI__Service__Playwright


def _aws_creds_available() -> bool:
    return bool(os.environ.get('AWS_ACCESS_KEY_ID')) and bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))


class test_Smoke__Playwright__Service__dev(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _aws_creds_available():
            pytest.skip('AWS credentials not set — smoke test requires a deployed Lambda')
        cls.lambda_docker = Lambda__Docker__SGraph_AI__Service__Playwright()
        cls.lambda_docker.setup()
        cls.function_url  = cls.lambda_docker.function_url()
        if not cls.function_url:
            pytest.skip('Function URL not available — deploy has not run for this stage')

    def test_1__health_info(self):
        response = requests.get(f'{self.function_url}health/info')
        assert response.status_code == 200
        data = response.json()
        assert data['service_name']      == 'sg-playwright'
        assert data['deployment_target'] == 'lambda'

    def test_2__health_status(self):
        response = requests.get(f'{self.function_url}health/status')
        assert response.status_code == 200
        assert 'healthy' in response.json()

    def test_3__capabilities(self):
        response = requests.get(f'{self.function_url}health/capabilities')
        assert response.status_code == 200
        caps = response.json()
        assert 'supports_persistent' in caps
        assert 'inline' in caps['supported_sinks']
