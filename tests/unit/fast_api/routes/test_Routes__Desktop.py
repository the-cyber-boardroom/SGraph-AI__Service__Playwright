# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Desktop (POST /desktop/browser, sg-playwright-vnc P2)
#
# In-memory TestClient, no mocks, no Chromium: the route is registered + key-
# gated, and on a headless instance (this test env) it 400s with the env-var
# name instead of attempting a headed launch. The happy path (real headed
# browser under Xvfb) is tests/integration/test_Desktop__Headed__Launch.py.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                          import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                                  import ENV_VAR__DEPLOYMENT_TARGET, ENV_VAR__DISPLAY_MODE
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service           import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Desktop                  import ROUTES_PATHS__DESKTOP


_API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
_API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'


class _Env:                                                                            # deterministic: auth on via a known key; display mode controlled per test
    KEYS = (ENV_VAR__DEPLOYMENT_TARGET, ENV_VAR__DISPLAY_MODE, _API_KEY_NAME, _API_KEY_VALUE)
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


class test_Routes__Desktop(TestCase):

    def test_route_is_registered(self):
        with _Env(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop', _API_KEY_NAME: 'X-API-Key', _API_KEY_VALUE: 'unit-test'}):
            fast_api = Fast_API__Playwright__Service().setup()
            paths    = {str(p) for p in fast_api.routes_paths_all()}                   # osbot helper expands _IncludedRouter (FastAPI >= 0.137 / Starlette 1.x no longer flattens)
            for path in ROUTES_PATHS__DESKTOP:
                assert path in paths, f'{path} not registered'

    def test_requires_api_key(self):                                                   # same gate as every other route — NOT auth-excluded
        with _Env(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop', _API_KEY_NAME: 'X-API-Key', _API_KEY_VALUE: 'unit-test'}):
            client = Fast_API__Playwright__Service().setup().client()
            r = client.post('/desktop/browser', json={})                               # no key
            assert r.status_code == 401

    def test_headless_instance_400s_with_env_var_name(self):                           # this test env has no X display — the guard must fire before any launch
        with _Env(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop', _API_KEY_NAME: 'X-API-Key', _API_KEY_VALUE: 'unit-test'}):
            client = Fast_API__Playwright__Service().setup().client()
            r = client.post('/desktop/browser', json={}, headers={'X-API-Key': 'unit-test'})
            assert r.status_code == 400
            assert ENV_VAR__DISPLAY_MODE in r.text                                     # actionable error, names the switch
