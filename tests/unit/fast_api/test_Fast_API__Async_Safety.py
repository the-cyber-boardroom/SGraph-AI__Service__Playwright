# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Playwright__Service / async-safety regression (Bug #4)
#
# The original Bug #4 report: hitting /session/create repeatedly inside a single
# Lambda container produced "sync API inside asyncio loop" — the *second* call
# died because the sync_playwright() instance from the first call was still
# pinned to that call's event-loop context.
#
# v0.1.13 made Browser__Launcher fresh-per-call (each launch spawns its own
# sync_playwright + stops it on close), which eliminates the root cause. This
# file is the regression test: we hammer /session/create 20× sequentially via
# the FastAPI TestClient and assert:
#   • every response is 200 (no asyncio contamination)
#   • the watchdog middleware drains in_flight back to 0 (register/unregister
#     are symmetric under both happy-path and error-path)
#
# The watchdog is DISABLED here via ENV_VAR__WATCHDOG_DISABLED — tests must not
# spawn background daemon threads. We assert on the *middleware* wrapping, not
# the watchdog's thread. To also cover the enabled path (in_flight updated on
# every request) there's a second scenario that turns the watchdog on but
# leaves max_request_ms so generous it never fires.
#
# Fakes: same pattern as test_Routes__Session — _FakeLauncher + _InMemoryArtefactWriter.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__DEPLOYMENT_TARGET        ,
                                                                                                    ENV_VAR__WATCHDOG_DISABLED         ,
                                                                                                    ENV_VAR__WATCHDOG_MAX_REQUEST_MS   ,
                                                                                                    ENV_VAR__WATCHDOG_POLL_INTERVAL_MS )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                    import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'

API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'unit-test'
AUTH_HEADERS  = {API_KEY_NAME: API_KEY_VALUE}

ENV_KEYS = [ENV_VAR__DEPLOYMENT_TARGET        ,
            ENV_VAR__API_KEY_NAME              ,
            ENV_VAR__API_KEY_VALUE             ,
            ENV_VAR__WATCHDOG_DISABLED         ,
            ENV_VAR__WATCHDOG_MAX_REQUEST_MS   ,
            ENV_VAR__WATCHDOG_POLL_INTERVAL_MS ]


class _EnvScrub:                                                                    # Snapshot/restore API-key + watchdog + target env vars only
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

class _FakeContext:
    def storage_state(self):           return {'cookies': [], 'origins': []}
    def add_cookies(self, cookies):    pass
    def set_extra_http_headers(self, h): pass


class _FakeBrowser:
    def __init__(self):
        self.context = _FakeContext()
    @property
    def contexts(self):
        return [self.context]
    def close(self): pass


class _FakePlaywright:
    def stop(self): pass


class _FakeLauncher(Browser__Launcher):
    stopped : list
    def launch(self, browser_config):
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,
                                                playwright          = _FakePlaywright(),
                                                playwright_start_ms = 0                ,
                                                browser_launch_ms   = 0                )
    def stop(self, session_id):
        self.stopped.append(session_id)
        return 0


class _InMemoryArtefactWriter(Artefact__Writer):
    vault_writes : list
    def read_from_vault (self, vault_ref)       : return None
    def write_to_vault  (self, vault_ref, data) : self.vault_writes.append((vault_ref, data))


def _build_fast_api():
    service = Playwright__Service(browser_launcher   = _FakeLauncher(),
                                  credentials_loader = Credentials__Loader(artefact_writer=_InMemoryArtefactWriter()))
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa, fa.client()


CREATE_BODY = {'browser_config': {}, 'capture_config': {}}


class test_session_create_repeated(TestCase):                                       # Regression for Bug #4 — sequential creates must all succeed
    N_CALLS = 20

    def test__twenty_sequential_creates_all_return_200__watchdog_disabled(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET : 'lambda',
                          ENV_VAR__WATCHDOG_DISABLED : '1'     }):                   # Disabled — background thread not started, middleware still runs
            fa, client = _build_fast_api()
            assert fa.watchdog.disabled is True
            assert fa.watchdog.started  is False                                     # Disabled ⇒ start() is a no-op

            statuses = []
            for _ in range(self.N_CALLS):
                resp = client.post('/session/create', headers=AUTH_HEADERS, json=CREATE_BODY)
                statuses.append(resp.status_code)

            assert statuses              == [200] * self.N_CALLS                     # No asyncio contamination across calls
            assert len(fa.watchdog.in_flight) == 0                                   # Disabled watchdog never tracks anything

    def test__middleware_drains_in_flight_back_to_zero(self):                        # Watchdog ENABLED but threshold generous so it never fires
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET        : 'lambda'  ,
                          ENV_VAR__WATCHDOG_MAX_REQUEST_MS  : '600000'  ,             # 10 min — never breached in unit tests
                          ENV_VAR__WATCHDOG_POLL_INTERVAL_MS: '600000'  }):
            fa, client = _build_fast_api()
            assert fa.watchdog.disabled is False
            assert fa.watchdog.started  is True                                      # start() spawns the daemon thread

            for _ in range(self.N_CALLS):
                resp = client.post('/session/create', headers=AUTH_HEADERS, json=CREATE_BODY)
                assert resp.status_code == 200

            assert len(fa.watchdog.in_flight) == 0                                   # Every register paired with an unregister — middleware symmetry

    def test__middleware_unregisters_even_when_route_errors(self):                   # 422 path: distributed lifetime rejected before the route body runs
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET        : 'lambda'  ,
                          ENV_VAR__WATCHDOG_MAX_REQUEST_MS  : '600000'  ,
                          ENV_VAR__WATCHDOG_POLL_INTERVAL_MS: '600000'  }):
            fa, client = _build_fast_api()
            bad_body = {'browser_config': {}, 'capture_config': {}, 'lifetime_hint': 'persistent_distributed'}
            for _ in range(5):
                resp = client.post('/session/create', headers=AUTH_HEADERS, json=bad_body)
                assert resp.status_code == 422                                       # Validator rejects — middleware still unregisters
            assert len(fa.watchdog.in_flight) == 0
