# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Session (POST /session/create, GET /session/list,
#                         GET /session/get/by-id/{id}, POST /session/save-state/{id},
#                         DELETE /session/close/{id})
#
# Drives the routes through a TestClient. Real Chromium is NOT launched —
# the Fast_API__Playwright__Service is booted with an injected Playwright__Service
# whose Browser__Launcher and Artefact__Writer are replaced with fakes. The
# Session__Manager treats browsers as opaque, so the fake flows through.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                                 import Any
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.fast_api.routes.Routes__Session                           import (ROUTES_PATHS__SESSION,
                                                                                                    TAG__ROUTES_SESSION  )
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
        self.overrides = {ENV_VAR__API_KEY_NAME : API_KEY_NAME ,                    # Always prime API-key env so AUTH_HEADERS is accepted
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

class _FakeContext:
    def __init__(self, state=None):
        self.state = state if state is not None else {'cookies': [], 'origins': []}
    def storage_state(self):
        return self.state
    def add_cookies(self, cookies):                                                 # Credentials__Loader calls these; we only need to not-crash
        pass
    def set_extra_http_headers(self, headers):
        pass


class _FakeBrowser:
    def __init__(self, state=None):
        self.context = _FakeContext(state=state)
    @property                                                                       # Real Playwright sync API: `contexts` is a @property
    def contexts(self):
        return [self.context]
    def close(self):
        pass


class _FakeLauncher(Browser__Launcher):
    stopped : list
    def launch(self, browser_config):
        return _FakeBrowser()
    def stop(self, session_id):
        self.stopped.append(session_id)
    def start(self):                                                                # Skip sync_playwright
        return self


class _InMemoryArtefactWriter(Artefact__Writer):
    vault_writes : list
    def read_from_vault(self, vault_ref):
        return None
    def write_to_vault(self, vault_ref, data):
        self.vault_writes.append((vault_ref, data))


def _build_fast_api():
    service = Playwright__Service(browser_launcher   = _FakeLauncher(),
                                  credentials_loader = Credentials__Loader(artefact_writer=_InMemoryArtefactWriter()))
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa, fa.client()


def _create_body(**overrides) -> dict:                                              # Minimal valid POST /session/create body
    body = {'browser_config': {},
            'capture_config': {}}
    body.update(overrides)
    return body


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_SESSION == 'session'
        assert ROUTES_PATHS__SESSION == ['/session/create'          ,
                                         '/session/list'            ,
                                         '/session/get/by-id/{id}'  ,
                                         '/session/save-state/{id}' ,
                                         '/session/close/{id}'      ]


class test_route_registration(TestCase):

    def test__all_five_session_paths_registered(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            fa, _ = _build_fast_api()
        paths = {str(getattr(r, 'path', '')) for r in fa.app().routes}
        for expected in ROUTES_PATHS__SESSION:
            assert expected in paths


class test_post_create(TestCase):

    def test__returns_201_or_200_with_session_info(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.post('/session/create', headers=AUTH_HEADERS, json=_create_body())
        assert response.status_code == 200
        body = response.json()
        assert 'session_info' in body
        assert 'capabilities' in body
        assert body['session_info']['status'] == 'active'

    def test__rejects_distributed_lifetime_with_422(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.post('/session/create', headers=AUTH_HEADERS,
                                    json=_create_body(lifetime_hint='persistent_distributed'))
        assert response.status_code == 422
        body = response.json()
        assert body['detail']['error_code'] == 'distributed_not_supported'


class test_get_list(TestCase):

    def test__returns_empty_list_initially(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.get('/session/list', headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json()      == []

    def test__lists_active_sessions_after_create(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            client.post('/session/create', headers=AUTH_HEADERS, json=_create_body())
            client.post('/session/create', headers=AUTH_HEADERS, json=_create_body())
            response = client.get('/session/list', headers=AUTH_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert {s['status'] for s in body} == {'active'}


class test_get_by_id(TestCase):

    def test__returns_session_info_for_known_id(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            created = client.post('/session/create', headers=AUTH_HEADERS, json=_create_body()).json()
            sid     = created['session_info']['session_id']
            response = client.get(f'/session/get/by-id/{sid}', headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json()['session_id'] == sid

    def test__returns_404_for_unknown_id(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.get('/session/get/by-id/no-such-session', headers=AUTH_HEADERS)
        assert response.status_code == 404


class test_post_save_state(TestCase):

    def test__returns_200_and_persists_storage_state(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            fa, client = _build_fast_api()
            created  = client.post('/session/create', headers=AUTH_HEADERS, json=_create_body()).json()
            sid      = created['session_info']['session_id']
            body     = {'vault_ref': {'vault_key': 'vk-test', 'path': '/state.json'}}
            response = client.post(f'/session/save-state/{sid}', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 200
        rj = response.json()
        assert rj['session_id']     == sid
        assert rj['vault_ref']['path'] == '/state.json'
        writer = fa.service.credentials_loader.artefact_writer
        assert len(writer.vault_writes) == 1

    def test__returns_404_when_session_unknown(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            body     = {'vault_ref': {'vault_key': 'vk', 'path': '/x.json'}}
            response = client.post('/session/save-state/nope', headers=AUTH_HEADERS, json=body)
        assert response.status_code == 404


class test_delete_close(TestCase):

    def test__returns_200_and_stops_browser(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            fa, client = _build_fast_api()
            created  = client.post('/session/create', headers=AUTH_HEADERS, json=_create_body()).json()
            sid      = created['session_info']['session_id']
            response = client.delete(f'/session/close/{sid}', headers=AUTH_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body['session_info']['session_id'] == sid
        assert body['session_info']['status']     == 'closed'
        assert sid in [str(s) for s in fa.service.browser_launcher.stopped]

    def test__returns_404_when_session_unknown(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.delete('/session/close/nope', headers=AUTH_HEADERS)
        assert response.status_code == 404


class test_auth_gate(TestCase):

    def test__post_create_without_api_key_is_rejected(self):                        # Confirms route is behind middleware (not in AUTH__EXCLUDED_PATHS)
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            _, client = _build_fast_api()
            response  = client.post('/session/create', json=_create_body())
        assert response.status_code == 401
