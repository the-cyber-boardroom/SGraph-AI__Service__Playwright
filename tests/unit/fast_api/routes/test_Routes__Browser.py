# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Browser (POST /browser/navigate, /browser/click, /browser/screenshot)
#
# Drives the three-endpoint Slice-B subset through a TestClient. Real Chromium
# is NOT launched — the Fast_API__Playwright__Service is booted with an injected
# Playwright__Service whose Browser__Launcher is a fake that returns opaque
# _FakeBrowser stand-ins. Each test walks the /session/create -> /browser/*
# round trip so auth + routing + payload shapes are all in scope.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
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

class _FakePage:                                                                     # Records Step__Executor calls; does nothing real
    def __init__(self):
        self.url = 'about:blank'
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None): pass
    def screenshot(self, full_page=False, timeout=None):
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16


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
    service = Playwright__Service(browser_launcher   = _FakeLauncher()                              ,
                                  credentials_loader = Credentials__Loader(artefact_writer=_InMemoryArtefactWriter()))
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa, fa.client()


def _create_session(client) -> str:                                                  # Helper — open a session, return its id
    body     = {'browser_config': {}, 'capture_config': {}}
    response = client.post('/session/create', headers=AUTH_HEADERS, json=body)
    assert response.status_code == 200
    return response.json()['session_info']['session_id']


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_BROWSER == 'browser'
        assert ROUTES_PATHS__BROWSER == ['/browser/navigate'  ,
                                         '/browser/click'     ,
                                         '/browser/screenshot']


class test_route_registration(TestCase):

    def test__all_three_browser_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        for expected in ROUTES_PATHS__BROWSER:
            assert expected in paths


class test_post_navigate(TestCase):

    def test__returns_200_with_step_result_passed(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client  = _build_fast_api()
            session_id = _create_session(client)
            body       = {'session_id': session_id                                       ,
                          'step'      : {'action': 'navigate', 'url': 'http://example.com/'}}
            response   = client.post('/browser/navigate', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['session_id']            == session_id
        assert rj['step_result']['status'] == 'passed'
        assert rj['step_result']['action'] == 'navigate'

    def test__returns_404_when_session_unknown(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'session_id': 'no-such-session'                                 ,
                         'step'      : {'action': 'navigate', 'url': 'http://example.com/'}}
            response  = client.post('/browser/navigate', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 404


class test_post_click(TestCase):

    def test__returns_200_after_prior_navigate(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client  = _build_fast_api()
            session_id = _create_session(client)
            client.post('/browser/navigate', headers=AUTH_HEADERS,
                        json={'session_id': session_id                                       ,
                              'step'      : {'action': 'navigate', 'url': 'http://example.com/'}})
            body     = {'session_id': session_id                               ,
                        'step'      : {'action': 'click', 'selector': 'button.go'}}
            response = client.post('/browser/click', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['step_result']['status'] == 'passed'
        assert rj['step_result']['action'] == 'click'


class test_post_screenshot(TestCase):

    def test__returns_200_with_disabled_sink(self):                                   # Default capture_config -> screenshot.enabled=False; Step__Executor still passes
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client  = _build_fast_api()
            session_id = _create_session(client)
            client.post('/browser/navigate', headers=AUTH_HEADERS,
                        json={'session_id': session_id                                       ,
                              'step'      : {'action': 'navigate', 'url': 'http://example.com/'}})
            body     = {'session_id': session_id                                             ,
                        'step'      : {'action': 'screenshot'                              }}
            response = client.post('/browser/screenshot', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['step_result']['status']    == 'passed'
        assert rj['step_result']['action']    == 'screenshot'
        assert rj['step_result']['artefacts'] == []


class test_auth_gate(TestCase):

    def test__missing_api_key_is_rejected(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body     = {'session_id': 'whatever'                                         ,
                        'step'      : {'action': 'navigate', 'url': 'http://example.com/'}}
            response = client.post('/browser/navigate', json=body)                     # No headers
        assert response.status_code in (401, 403)                                     # osbot-fast-api's middleware may use either
