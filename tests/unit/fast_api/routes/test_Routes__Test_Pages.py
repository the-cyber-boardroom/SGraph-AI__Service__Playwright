# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Test_Pages (GET /test-pages/{name} deterministic fixtures)
#
# v0.2.64 console iteration-2, item 5 (Decision #5): the self-contained S-series
# console examples target HTML fixtures served BY this service so they run against
# the server-side browser with no external egress. This suite asserts, via the
# in-memory TestClient (no Chromium):
#   • each of the five fixtures returns 200 with its stable element ids
#   • the /test-pages/* paths are reachable WITHOUT an API key (auth-excluded — the
#     same mechanism that exempts /auth/set-cookie-form), so the server-side browser
#     can fetch them
#   • the 404 branch escapes the reflected name (no reflected-XSS)
#
# No mocks, no patches — register the real service and drive it through TestClient.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                          import TestCase

from osbot_fast_api.api.schemas.consts.consts__Fast_API                                import AUTH__EXCLUDED_PATHS
from sg_compute_specs.playwright.core.consts.env_vars                                  import ENV_VAR__DEPLOYMENT_TARGET, ENV_VAR__ROOT_PATH
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service           import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Test_Pages              import (TEST_PAGE_NAMES,
                                                                                              ROUTES_PATHS__TEST_PAGES)


_API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
_API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'


# Per-fixture: a stable id that MUST be present (used by the S-series workflows).
EXPECTED_IDS = {'simple'  : ['id="title"', 'id="intro"', 'id="footer"']                    ,
                'form'    : ['id="username"', 'id="password"', 'id="submit"', 'id="result"'],
                'dynamic' : ['id="status"', 'id="late"', 'id="ready"']                     ,  # #ready injected by inline JS (present in source)
                'links'   : ['id="link-alpha"', 'id="bottom"', 'id="gamma"']               ,
                'slow'    : ['id="content"', 'id="loaded"']                                ,
                'cookies' : ['id="cookie-list"', 'id="has-cookies"', 'id="no-cookies"']    }  # set_cookie slice — S6 target; renders document.cookie into stable ids


class _EnvScrub:                                                                           # deterministic serving: auth ON via a known key, default prefix
    KEYS = (ENV_VAR__DEPLOYMENT_TARGET, _API_KEY_NAME, _API_KEY_VALUE, ENV_VAR__ROOT_PATH)
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


class test_Routes__Test_Pages(TestCase):

    def test__fixture_names_are_the_six_self_contained_pages(self):
        assert TEST_PAGE_NAMES         == ['simple', 'form', 'dynamic', 'links', 'slow', 'cookies']
        assert ROUTES_PATHS__TEST_PAGES == [f'/test-pages/{n}' for n in TEST_PAGE_NAMES]

    def test__each_fixture_returns_200_with_expected_ids__without_an_api_key(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'   ,                          # auth IS enabled — a key is configured
                          _API_KEY_NAME             : 'X-API-Key',
                          _API_KEY_VALUE            : 'unit-test'}):
            client = Fast_API__Playwright__Service().setup().client()
            for name in TEST_PAGE_NAMES:
                r = client.get(f'/test-pages/{name}')                                       # NO X-API-Key header → reaches the page only because it is auth-excluded
                assert r.status_code == 200, f'{name} not reachable without a key: {r.status_code}'
                assert 'text/html' in r.headers.get('content-type', '')
                for marker in EXPECTED_IDS[name]:
                    assert marker in r.text, f'{name} missing {marker}'

    def test__test_page_paths_are_auth_excluded(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'   ,
                          _API_KEY_NAME             : 'X-API-Key',
                          _API_KEY_VALUE            : 'unit-test'}):
            Fast_API__Playwright__Service().setup()                                         # setup() appends the paths to AUTH__EXCLUDED_PATHS
            for path in ROUTES_PATHS__TEST_PAGES:
                assert path in AUTH__EXCLUDED_PATHS, f'{path} not auth-excluded'

    def test__unknown_page_404_escapes_reflected_name(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'   ,                          # the unknown-name path is NOT auth-excluded, so pass the key
                          _API_KEY_NAME             : 'X-API-Key',
                          _API_KEY_VALUE            : 'unit-test'}):
            client = Fast_API__Playwright__Service().setup().client()
            # single path segment (no '/') so it matches /test-pages/{name} and reaches
            # the handler's 404 branch (a name with '/' would not match the route at all)
            r = client.get('/test-pages/<script>alert(1)<x>', headers={'X-API-Key': 'unit-test'})
        assert r.status_code == 404
        assert '<script>alert(1)<x>' not in r.text                                          # raw reflected input must NOT appear
        assert '&lt;script&gt;'       in r.text                                              # escaped instead
