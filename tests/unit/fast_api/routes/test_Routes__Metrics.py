# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Metrics (GET /metrics)
#
# Verifies route registration, correct Content-Type, and that the Prometheus
# text output contains the expected metric names. Uses the same _EnvScrub +
# _client() pattern as the sibling health/browser route tests.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.fast_api.routes.Routes__Metrics                           import (ROUTES_PATHS__METRICS,
                                                                                                    TAG__ROUTES_METRICS  )


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'

API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'unit-test-metrics'

AUTH_HEADERS  = {API_KEY_NAME: API_KEY_VALUE}

ENV_KEYS = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
            ENV_VAR__CI                    ,
            ENV_VAR__CLAUDE_SESSION        ,
            ENV_VAR__DEPLOYMENT_TARGET     ,
            ENV_VAR__SG_SEND_BASE_URL      ,
            ENV_VAR__API_KEY_NAME          ,
            ENV_VAR__API_KEY_VALUE         ]


class _EnvScrub:
    def __init__(self, **overrides):
        self.overrides = {ENV_VAR__API_KEY_NAME : API_KEY_NAME ,
                          ENV_VAR__API_KEY_VALUE: API_KEY_VALUE}
        self.overrides.update(overrides)
        self.snapshot = {}
    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


def _client():
    fa = Fast_API__Playwright__Service().setup()
    return fa, fa.client()


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_METRICS   == 'metrics'
        assert ROUTES_PATHS__METRICS == ['/metrics']


class test_route_registration(TestCase):

    def test__metrics_path_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _client()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        assert '/metrics' in paths


class test_get_metrics(TestCase):

    def test__returns_200_with_prometheus_content_type(self):
        with _EnvScrub():
            _, client = _client()
            response  = client.get('/metrics', headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert 'text/plain' in response.headers.get('content-type', '')

    def test__response_body_contains_expected_metric_names(self):
        with _EnvScrub():
            _, client = _client()
            response  = client.get('/metrics', headers=AUTH_HEADERS)
        body = response.text
        assert 'sg_playwright_request_total'            in body
        assert 'sg_playwright_chromium_launch_seconds'  in body
        assert 'sg_playwright_navigate_seconds'         in body
        assert 'sg_playwright_chromium_teardown_seconds' in body
        assert 'sg_playwright_total_duration_seconds'   in body

    def test__requires_api_key(self):
        with _EnvScrub():
            _, client = _client()
            response  = client.get('/metrics')                                      # No auth header
        assert response.status_code == 401
