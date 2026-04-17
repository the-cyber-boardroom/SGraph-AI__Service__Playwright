# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Sequence (POST /sequence/execute)
#
# Drives the sequence endpoint through a TestClient. Real Chromium is NOT
# launched — the Fast_API__Playwright__Service is booted with an injected
# Playwright__Service whose Browser__Launcher is a fake that returns opaque
# _FakeBrowser stand-ins. Each test walks /session/create (optionally) then
# POSTs /sequence/execute so auth + routing + payload shapes are all in scope.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.fast_api.routes.Routes__Sequence                          import (ROUTES_PATHS__SEQUENCE,
                                                                                                    TAG__ROUTES_SEQUENCE  )
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


class _FakePage:
    def __init__(self):
        self.url = 'http://example.com/current'
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None): pass


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


def _create_session(client) -> str:
    body     = {'browser_config': {}, 'capture_config': {}}
    response = client.post('/session/create', headers=AUTH_HEADERS, json=body)
    assert response.status_code == 200
    return response.json()['session_info']['session_id']


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_SEQUENCE   == 'sequence'
        assert ROUTES_PATHS__SEQUENCE == ['/sequence/execute']


class test_route_registration(TestCase):

    def test__sequence_path_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        assert '/sequence/execute' in paths


class test_post_sequence__ad_hoc(TestCase):

    def test__returns_200_completed_for_all_passing_steps(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'browser_config'     : {}                                                     ,
                         'capture_config'     : {}                                                     ,
                         'sequence_config'    : {'halt_on_error': True}                                ,
                         'steps'              : [{'action': 'navigate', 'url': 'http://one.test/' },
                                                  {'action': 'navigate', 'url': 'http://two.test/' },
                                                  {'action': 'click'   , 'selector': '#submit'    }],
                         'close_session_after': True                                                    }
            response  = client.post('/sequence/execute', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['status']        == 'completed'
        assert rj['steps_total' ]  == 3
        assert rj['steps_passed']  == 3
        assert rj['steps_failed']  == 0


class test_post_sequence__reuses_session(TestCase):

    def test__returns_200_and_preserves_session(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client   = _build_fast_api()
            session_id  = _create_session(client)
            body        = {'session_id'         : session_id                                  ,
                           'capture_config'     : {}                                          ,
                           'sequence_config'    : {'halt_on_error': True}                     ,
                           'steps'              : [{'action': 'navigate', 'url': 'http://a.test/'}],
                           'close_session_after': False                                       }
            response    = client.post('/sequence/execute', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['status']                    == 'completed'
        assert rj['session_info']['status']    == 'active'
        assert rj['session_info']['session_id']== session_id


class test_post_sequence__404_unknown_session(TestCase):

    def test__returns_404(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'session_id'         : 'no-such-session'                             ,
                         'capture_config'     : {}                                            ,
                         'sequence_config'    : {}                                            ,
                         'steps'              : [{'action': 'navigate', 'url': 'http://x.test/'}],
                         'close_session_after': False                                         }
            response  = client.post('/sequence/execute', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 404


class test_auth_gate(TestCase):

    def test__missing_api_key_is_rejected(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body      = {'browser_config'     : {}                                            ,
                         'capture_config'     : {}                                            ,
                         'sequence_config'    : {}                                            ,
                         'steps'              : [{'action': 'navigate', 'url': 'http://x.test/'}],
                         'close_session_after': True                                          }
            response  = client.post('/sequence/execute', json=body)
        assert response.status_code in (401, 403)
