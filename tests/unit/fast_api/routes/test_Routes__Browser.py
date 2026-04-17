# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Browser (v0.1.24 — six one-shot POST endpoints)
#
#   POST /browser/navigate    -> JSON Schema__Browser__One_Shot__Response
#   POST /browser/click       -> JSON Schema__Browser__One_Shot__Response
#   POST /browser/fill        -> JSON Schema__Browser__One_Shot__Response
#   POST /browser/get-content -> JSON Schema__Browser__One_Shot__Response (html set)
#   POST /browser/get-url     -> JSON Schema__Browser__One_Shot__Response
#   POST /browser/screenshot  -> image/png (raw bytes + X-*-Ms timing headers)
#
# Every endpoint is self-contained: the TestClient POSTs a body, the route
# delegates to Playwright__Service.browser_<action>(), a fake Browser__Launcher
# hands back opaque _FakeBrowser stand-ins so no real Chromium ever boots.
#
# Each test asserts that the launcher.launch_count increments once per call,
# confirming the stateless "fresh Chromium per request" contract end-to-end.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.fast_api.routes.Routes__Browser                           import (ROUTES_PATHS__BROWSER,
                                                                                                    TAG__ROUTES_BROWSER  )
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'

API_KEY_NAME  = 'X-API-Key'
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


# ─── Fakes (no real Chromium, no real vault) ─────────────────────────────────

class _FakeLocator:
    def __init__(self, selector):
        self.selector = selector
    def press_sequentially(self, value, timeout=None): pass
    def inner_text   (self, timeout=None): return 'locator-text'
    def inner_html   (self, timeout=None): return '<span>locator-html</span>'
    def screenshot   (self, timeout=None): return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16


class _FakePage:
    def __init__(self):
        self.url = 'http://example.com/current'
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None): pass
    def fill (self, selector, value, timeout=None): pass
    def screenshot(self, full_page=False, timeout=None):
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16
    def content(self):
        return '<html><body>full-page-html</body></html>'
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
    @property
    def contexts(self):
        return self._contexts
    def new_context(self, **kwargs):
        context = _FakeContext()
        self._contexts.append(context)
        return context
    def close(self): pass


class _FakePlaywright:
    def stop(self): pass


class _FakeLauncher(Browser__Launcher):
    def __init__(self):
        super().__init__()
        self.launch_count   = 0
        self.stop_count     = 0
    def launch(self, browser_config):
        self.launch_count += 1
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,
                                                playwright          = _FakePlaywright(),
                                                playwright_start_ms = 0                ,
                                                browser_launch_ms   = 0                )
    def stop(self, session_id):
        self.stop_count += 1
        return 0


class _InMemoryArtefactWriter(Artefact__Writer):
    def read_from_vault(self, vault_ref): return None
    def write_to_vault (self, vault_ref, data): pass


def _build_fast_api():
    service  = Playwright__Service(browser_launcher   = _FakeLauncher()                              ,
                                   credentials_loader = Credentials__Loader(artefact_writer=_InMemoryArtefactWriter()))
    fa       = Fast_API__Playwright__Service(service=service).setup()
    launcher = service.browser_launcher                                              # Hand back the fake so tests can read launch_count
    return fa, fa.client(), launcher


# ─── Tests ───────────────────────────────────────────────────────────────────

class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_BROWSER == 'browser'
        assert ROUTES_PATHS__BROWSER == ['/browser/navigate'   ,
                                         '/browser/click'      ,
                                         '/browser/fill'       ,
                                         '/browser/get-content',
                                         '/browser/get-url'    ,
                                         '/browser/screenshot' ]


class test_route_registration(TestCase):

    def test__all_six_browser_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        for expected in ROUTES_PATHS__BROWSER:
            assert expected in paths


class test_post_navigate(TestCase):

    def test__launches_fresh_browser_per_call(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/'}
            response = client.post('/browser/navigate', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['url']       == 'http://example.com/'
        assert 'final_url'     in rj
        assert 'trace_id'      in rj
        assert 'timings'       in rj
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1


class test_post_click(TestCase):

    def test__returns_200_and_launches_one_browser(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/', 'selector': 'button.go'}
            response = client.post('/browser/click', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1


class test_post_fill(TestCase):

    def test__returns_200_and_launches_one_browser(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/', 'selector': 'input#q', 'value': 'hello world'}
            response = client.post('/browser/fill', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1


class test_post_get_content(TestCase):

    def test__returns_html_in_body_and_launches_one_browser(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/'}
            response = client.post('/browser/get-content', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['html'] is not None
        assert 'full-page-html' in rj['html']                                        # _FakePage.content() returns this
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1


class test_post_get_url(TestCase):

    def test__returns_final_url(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/landing'}
            response = client.post('/browser/get-url', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['final_url'] == 'http://example.com/landing'
        assert launcher.launch_count == 1


class test_post_screenshot(TestCase):

    def test__returns_png_bytes_and_timing_headers(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/'}
            response = client.post('/browser/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.headers.get('content-type', '').startswith('image/png')
        assert response.content[:4] == b'\x89PNG'                                    # Real PNG magic
        for hdr in ('x-playwright-start-ms', 'x-browser-launch-ms', 'x-steps-ms', 'x-browser-close-ms', 'x-total-ms'):
            assert hdr in {h.lower() for h in response.headers.keys()}
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1


class test_auth_gate(TestCase):

    def test__missing_api_key_is_rejected(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, _ = _build_fast_api()
            body         = {'url': 'http://example.com/'}
            response     = client.post('/browser/navigate', json=body)                # No headers
        assert response.status_code in (401, 403)                                    # osbot-fast-api's middleware may use either
