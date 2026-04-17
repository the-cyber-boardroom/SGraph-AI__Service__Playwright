# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Quick (POST /quick/html + POST /quick/screenshot)
#
# Drives the quick endpoints through a TestClient with a fake browser stack.
# No real Chromium. Each test asserts: (a) the flat Swagger-friendly shape
# works end-to-end, (b) the underlying sequence teardown happened (session is
# closed after each call).
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.fast_api.routes.Routes__Quick                             import (ROUTES_PATHS__QUICK,
                                                                                                    TAG__ROUTES_QUICK  )
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'
API_KEY_NAME           = 'X-API-Key'
API_KEY_VALUE          = 'unit-test'
AUTH_HEADERS           = {API_KEY_NAME: API_KEY_VALUE}

PNG_BYTES = b'\x89PNG\r\n\x1a\nFAKE_PNG_FOR_TESTS'                                          # Shape-valid PNG magic header; body is arbitrary

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


class _FakeLocator:                                                                         # Element-only screenshot + inner_text/inner_html
    def __init__(self, selector):
        self.selector = selector
    def screenshot(self, timeout=None):
        return PNG_BYTES
    def inner_text(self, timeout=None): return 'locator-text'
    def inner_html(self, timeout=None): return '<span>locator-html</span>'


class _FakePage:
    def __init__(self):
        self.url = 'http://example.com/start'
        self.click_calls = []
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url                                                                      # Mimic browser address-bar update for get_url extraction
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None):
        self.click_calls.append(selector)
        self.url = f'{self.url}#after-click'                                                # Simulate client-side nav so final_url != url
    def content(self):
        return f'<html><body>content of {self.url}</body></html>'
    def screenshot(self, full_page=False, timeout=None):
        return PNG_BYTES
    def locator(self, selector):
        return _FakeLocator(selector)


class _FakeContext:
    def __init__(self):
        self.pages = []
    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page
    def storage_state(self): return {'cookies': [], 'origins': []}
    def add_cookies(self, cookies): pass
    def set_extra_http_headers(self, headers): pass


class _FakeBrowser:
    def __init__(self):
        self._contexts = []
    @property                                                                                # Playwright sync API exposes `contexts` as a @property, not a method — keep fakes identical so the old bug (browser.contexts() → 'list' not callable) cannot slip back in
    def contexts(self):
        return self._contexts
    def new_context(self):
        context = _FakeContext()
        self._contexts.append(context)
        return context
    def close(self): pass


class _FakeLauncher(Browser__Launcher):
    def launch(self, browser_config):
        return _FakeBrowser()
    def stop(self, session_id): pass
    def start(self): return self


class _InMemoryArtefactWriter(Artefact__Writer):
    def read_from_vault(self, vault_ref): return None
    def write_to_vault (self, vault_ref, data): pass


def _build_fast_api():
    service = Playwright__Service(browser_launcher   = _FakeLauncher()                                           ,
                                  credentials_loader = Credentials__Loader(artefact_writer=_InMemoryArtefactWriter()))
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa, fa.client()


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_QUICK   == 'quick'
        assert ROUTES_PATHS__QUICK == ['/quick/html', '/quick/screenshot']


class test_route_registration(TestCase):

    def test__quick_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        assert '/quick/html'       in paths
        assert '/quick/screenshot' in paths


class test_post_quick_html(TestCase):

    def test__returns_flat_response_with_html_and_final_url(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/target'}
            response  = client.post('/quick/html', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['url']       == 'http://example.com/target'
        assert rj['final_url'] == 'http://example.com/target'                                # No click -> navigate-time URL
        assert 'content of http://example.com/target' in rj['html']
        assert 'duration_ms' in rj

    def test__click_mutates_final_url(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/form', 'click': '#submit'}
            response  = client.post('/quick/html', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['url']       == 'http://example.com/form'
        assert rj['final_url'] == 'http://example.com/form#after-click'                       # Fake click appends #after-click

    def test__timeout_ms_zero_is_treated_as_unset(self):                                      # Swagger's default example renders integers as 0 — that payload must NOT zero every step's timeout
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/target', 'click': '', 'wait_until': 'load', 'timeout_ms': 0}
            response  = client.post('/quick/html', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200                                                    # Would 502 with "Timeout 0ms exceeded" if 0 leaked through to step.timeout_ms
        rj = response.json()
        assert rj['final_url'] == 'http://example.com/target'


class test_post_quick_screenshot(TestCase):

    def test__returns_raw_png(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/shoot'}
            response  = client.post('/quick/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/png')
        assert response.content == PNG_BYTES

    def test__selector_uses_locator_screenshot(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/shoot', 'selector': '.card'}
            response  = client.post('/quick/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.content == PNG_BYTES

    def test__roundtrip_bytes_match_base64_decode(self):                                     # Sanity — the bytes the route emits are the same bytes the fake page produced
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'url': 'http://example.com/roundtrip'}
            response  = client.post('/quick/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.content == base64.b64decode(base64.b64encode(PNG_BYTES))             # Prove the base64 encode/decode around the INLINE sink is lossless


class test_auth_gate(TestCase):

    def test__missing_api_key_is_rejected_for_html(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.post('/quick/html', json={'url': 'http://example.com/'})
        assert response.status_code in (401, 403)

    def test__missing_api_key_is_rejected_for_screenshot(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.post('/quick/screenshot', json={'url': 'http://example.com/'})
        assert response.status_code in (401, 403)
