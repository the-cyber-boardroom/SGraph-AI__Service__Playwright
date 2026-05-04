# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Screenshot
#
#   POST /screenshot        → JSON Schema__Screenshot__Response
#   POST /screenshot/batch  → JSON Schema__Screenshot__Batch__Response
#
# Verifies the two screenshot routes without real Chromium. Uses the same
# _FakeLauncher / _FakePage pattern as test_Routes__Browser: a fake launcher
# substitutes for Browser__Launcher so no subprocess ever starts.
#
# _FakePage.evaluate() is a no-op; _FakePage.screenshot() returns a minimal
# valid PNG header so base64 round-trips cleanly.
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
from sgraph_ai_service_playwright.fast_api.routes.Routes__Screenshot                       import (ROUTES_PATHS__SCREENSHOT,
                                                                                                    TAG__ROUTES_SCREENSHOT  )
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result           import Schema__Browser__Launch__Result
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

FAKE_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 16        # Minimal PNG magic bytes


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


# ─── Fakes ────────────────────────────────────────────────────────────────────

class _FakeLocator:
    def __init__(self, selector):
        self.selector = selector
    def press_sequentially(self, value, timeout=None): pass
    def inner_text   (self, timeout=None): return 'locator-text'
    def inner_html   (self, timeout=None): return '<span>locator-html</span>'
    def screenshot   (self, timeout=None): return FAKE_PNG


class _FakePage:
    def __init__(self):
        self.url           = 'http://example.com/current'
        self.evaluate_log  = []
        self.click_log     = []
    def goto       (self, url, wait_until=None, timeout=None): self.url = url
    def click      (self, selector, button=None, click_count=None, delay=None, force=None, timeout=None):
        self.click_log.append(selector)
    def fill       (self, selector, value, timeout=None): pass
    def evaluate   (self, expression):
        self.evaluate_log.append(expression)
    def screenshot (self, full_page=False, timeout=None): return FAKE_PNG
    def content    (self): return '<html><body>screenshot-html</body></html>'
    def locator    (self, selector): return _FakeLocator(selector)


class _FakeContext:
    def __init__(self, page_factory=None):
        self._page_factory = page_factory or _FakePage
        self.pages         = []
    def new_page(self):
        page = self._page_factory()
        self.pages.append(page)
        return page
    def storage_state        (self)         : return {'cookies': [], 'origins': []}
    def add_cookies          (self, cookies): pass
    def set_extra_http_headers(self, headers): pass


class _FakeBrowser:
    def __init__(self):
        self._contexts = []
    @property
    def contexts(self): return self._contexts
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
        self.launch_count = 0
        self.stop_count   = 0
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
    launcher = service.browser_launcher
    return fa, fa.client(), launcher


# ─── Tests ───────────────────────────────────────────────────────────────────

class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_SCREENSHOT   == 'screenshot'
        assert ROUTES_PATHS__SCREENSHOT == ['/screenshot', '/screenshot/batch']


class test_route_registration(TestCase):

    def test__both_screenshot_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        for expected in ROUTES_PATHS__SCREENSHOT:
            assert expected in paths, f'{expected!r} not found in registered paths: {sorted(paths)}'


class test_post_screenshot__png(TestCase):

    def test__url_only__returns_screenshot_b64(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/'}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['screenshot_b64'] is not None
        decoded = base64.b64decode(rj['screenshot_b64'])
        assert decoded[:4] == b'\x89PNG'
        assert rj['html']  is None
        assert rj['url']   is not None
        assert launcher.launch_count == 1
        assert launcher.stop_count   == 1

    def test__full_page_flag_passes_through(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, _ = _build_fast_api()
            body     = {'url': 'http://example.com/', 'full_page': True}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.json()['screenshot_b64'] is not None

    def test__with_click_still_returns_screenshot_b64(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/', 'click': 'button#accept'}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.json()['screenshot_b64'] is not None
        assert launcher.launch_count == 1

    def test__with_javascript_still_returns_screenshot_b64(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/', 'javascript': 'document.title = "test"'}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.json()['screenshot_b64'] is not None
        assert launcher.launch_count == 1


class test_post_screenshot__html(TestCase):

    def test__format_html__returns_html_field(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body     = {'url': 'http://example.com/', 'format': 'html'}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['html']           is not None
        assert 'screenshot-html'    in rj['html']
        assert rj['screenshot_b64'] is None
        assert launcher.launch_count == 1

    def test__format_html__with_click(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, _ = _build_fast_api()
            body     = {'url': 'http://example.com/', 'format': 'html', 'click': 'button#ok'}
            response = client.post('/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.json()['html'] is not None


class test_post_screenshot_batch__items(TestCase):

    def test__two_items__two_screenshots_returned(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body = {'items': [{'url': 'http://example.com/page1'},
                               {'url': 'http://example.com/page2'}]}
            response = client.post('/screenshot/batch', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert len(rj['screenshots']) == 2
        for shot in rj['screenshots']:
            assert shot['screenshot_b64'] is not None
        assert launcher.launch_count == 2                                              # One fresh browser per item

    def test__empty_body__returns_empty_list(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, _ = _build_fast_api()
            body     = {}
            response = client.post('/screenshot/batch', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        assert response.json()['screenshots'] == []


class test_post_screenshot_batch__steps(TestCase):

    def test__two_steps_screenshot_per_step_false__one_screenshot(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body = {'steps': [{'url': 'http://example.com/step1'},
                               {'url': 'http://example.com/step2'}],
                    'screenshot_per_step': False}
            response = client.post('/screenshot/batch', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert len(rj['screenshots']) == 1                                             # Only final screenshot
        assert rj['screenshots'][0]['screenshot_b64'] is not None
        assert launcher.launch_count == 1                                              # Single shared session

    def test__two_steps_screenshot_per_step_true__two_screenshots(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, launcher = _build_fast_api()
            body = {'steps': [{'url': 'http://example.com/step1'},
                               {'url': 'http://example.com/step2'}],
                    'screenshot_per_step': True}
            response = client.post('/screenshot/batch', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert len(rj['screenshots']) == 2                                             # One per step
        for shot in rj['screenshots']:
            assert shot['screenshot_b64'] is not None
        assert launcher.launch_count == 1                                              # Still one shared session


class test_auth_gate(TestCase):

    def test__missing_api_key_rejected(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client, _ = _build_fast_api()
            body         = {'url': 'http://example.com/'}
            response     = client.post('/screenshot', json=body)                       # No auth headers
        assert response.status_code in (401, 403)
