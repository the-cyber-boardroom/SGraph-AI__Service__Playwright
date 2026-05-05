# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Health (GET /health/info, /health/status, /health/capabilities)
#
# Drives the routes through a TestClient rather than calling the methods
# directly — guarantees the URL wiring is correct, not just the service
# delegation. Uses env-scrubbed Playwright__Service so detection is
# deterministic.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Health                            import (ROUTES_PATHS__HEALTH,
                                                                                                    TAG__ROUTES_HEALTH  )


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'

API_KEY_NAME  = 'X-API-Key'                                                                 # Test-fixture value — middleware reads it from env
API_KEY_VALUE = 'unit-test'

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
        self.overrides = {ENV_VAR__API_KEY_NAME : API_KEY_NAME ,                            # Always prime the API-key env so the middleware accepts AUTH_HEADERS
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
        assert TAG__ROUTES_HEALTH   == 'health'
        assert ROUTES_PATHS__HEALTH == ['/health/info', '/health/status', '/health/capabilities']


class test_route_registration(TestCase):

    def test__all_three_health_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _client()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}              # Paths come back as Safe_Str__Fast_API__Route__Prefix wrappers — coerce
        for expected in ROUTES_PATHS__HEALTH:
            assert expected in paths


class test_get_info(TestCase):

    def test__returns_service_info_json(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _client()
            response  = client.get('/health/info', headers=AUTH_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body['service_name']      == 'sg-playwright'
        assert body['deployment_target'] == 'lambda'
        assert 'capabilities' in body


class test_get_status(TestCase):

    def test__returns_schema_health_with_two_checks(self):                            # v0.1.24 — session_manager removed; only browser_launcher + connectivity
        with _EnvScrub():
            _, client = _client()
            response  = client.get('/health/status', headers=AUTH_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert 'healthy'   in body
        assert 'timestamp' in body
        check_names = [c['check_name'] for c in body['checks']]
        assert check_names == ['browser_launcher', 'connectivity']

    def test__unhealthy_when_vault_unreachable(self):
        with _EnvScrub():
            _, client = _client()
            response  = client.get('/health/status', headers=AUTH_HEADERS)
        assert response.json()['healthy'] is False


class test_get_capabilities(TestCase):

    def test__returns_lambda_capabilities(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _client()
            response  = client.get('/health/capabilities', headers=AUTH_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body['max_session_lifetime_ms'] == 900_000
        assert body['available_browsers']      == ['chromium', 'firefox', 'webkit']  # All three engines ship with the Microsoft playwright base image — Firefox + WebKit are the only native-proxy-auth path
        assert 'local_file' not in body['supported_sinks']                           # Lambda cannot write to disk

    def test__returns_laptop_capabilities_including_local_file_sink(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            _, client = _client()
            response  = client.get('/health/capabilities', headers=AUTH_HEADERS)
        body = response.json()
        assert 'local_file' in body['supported_sinks']
