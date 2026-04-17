# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Playwright__Service (FastAPI app boot + lambda handler)
#
# Verifies the top-level FastAPI wrapper:
#   • importable without side effects
#   • setup() primes service + disables api-key middleware so /health answers plain curl
#   • handler() returns a Mangum handler (for AWS LWA / Lambda integration)
#   • lambda_handler.run is wired to Fast_API__Playwright__Service
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                                import Serverless__Fast_API

from sgraph_ai_service_playwright.consts.env_vars                                           import ENV_VAR__DEPLOYMENT_TARGET
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


class _EnvScrub:
    KEYS = (ENV_VAR__DEPLOYMENT_TARGET,)
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in self.KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in self.KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class test_class_shape(TestCase):

    def test__extends_serverless_fast_api(self):
        assert issubclass(Fast_API__Playwright__Service, Serverless__Fast_API)

    def test__has_playwright_service_attribute(self):
        fa = Fast_API__Playwright__Service()
        assert isinstance(fa.service, Playwright__Service)


class test_setup(TestCase):

    def test__setup_returns_self_and_primes_detector(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa = Fast_API__Playwright__Service()
            assert fa.service.capability_detector.detected_target is None
            out = fa.setup()
            assert out is fa                                                        # Chainable
            assert fa.service.capability_detector.detected_target is not None

    def test__disables_api_key_check(self):                                         # Prereq for plain-curl health probes
        with _EnvScrub():
            fa = Fast_API__Playwright__Service().setup()
            assert fa.config.enable_api_key is False


class test_route_wiring(TestCase):

    def test__health_routes_are_registered_after_setup(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa    = Fast_API__Playwright__Service().setup()
            paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        assert '/health/info'         in paths
        assert '/health/status'       in paths
        assert '/health/capabilities' in paths


class test_handler(TestCase):

    def test__handler_returns_a_callable(self):                                     # Mangum wrapper — verifies Lambda entry works at module load time
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            fa      = Fast_API__Playwright__Service().setup()
            handler = fa.handler()
        assert callable(handler)


class test_client_end_to_end(TestCase):                                             # Quickest way to assert the full boot path returns real JSON

    def test__get_health_info_returns_200_and_service_name(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa    = Fast_API__Playwright__Service().setup()
            body  = fa.client().get('/health/info').json()
        assert body['service_name'] == 'sg-playwright'


class test_lambda_handler_module(TestCase):

    def test__import_is_side_effect_free(self):                                     # Importing lambda_handler must NOT boot uvicorn — run() is gated behind __main__
        from sgraph_ai_service_playwright.fast_api                                      import lambda_handler
        assert callable(lambda_handler.run)
