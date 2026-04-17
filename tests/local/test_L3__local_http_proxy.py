# ═══════════════════════════════════════════════════════════════════════════════
# Local validation — L3 — full HTTP stack against FastAPI TestClient
#
# L2 proved the service-level wiring. L3 proves FastAPI routing + schema
# validation + API-key auth middleware don't drop the proxy auth payload.
# Uses the real Browser__Launcher (real Chromium) behind a TestClient — same
# uvicorn-shaped path the Lambda uses, minus the LWA envelope.
#
# Why TestClient and not a real uvicorn process:
#   • FastAPI TestClient drives the ASGI app in-process; same handlers, same
#     middleware chain, same Type_Safe → Pydantic bridge. The only things it
#     skips are OS-level socket + wire serialisation, neither of which matter
#     for proxy-wiring regressions.
#   • Avoids the subprocess-management fragility that plagued earlier
#     scratch-pad tests.
#
# Prereqs (same as L1/L2):
#   - mitmdump --listen-port 8888 --proxyauth qa-user:qa-pass-x7
#   - SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium-1208/chrome-linux64/chrome
#
# Skipped when mitmproxy is not reachable.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
from unittest                                                                                  import TestCase

import pytest

from sgraph_ai_service_playwright.consts.env_vars                                              import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                       ENV_VAR__CI                    ,
                                                                                                       ENV_VAR__CLAUDE_SESSION        ,
                                                                                                       ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                       ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service                       import Fast_API__Playwright__Service
from sgraph_ai_service_playwright.service.Playwright__Service                                  import Playwright__Service


PROXY_HOST     = '127.0.0.1'
PROXY_PORT     = 8888
PROXY_USERNAME = 'qa-user'
PROXY_PASSWORD = 'qa-pass-x7'

PROBE_URL      = 'https://api.ipify.org/?format=json'

ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'

API_KEY_NAME   = 'X-API-Key'
API_KEY_VALUE  = 'local-validation-key'
AUTH_HEADERS   = {API_KEY_NAME: API_KEY_VALUE}

ENV_KEYS = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
            ENV_VAR__CI                    ,
            ENV_VAR__CLAUDE_SESSION        ,
            ENV_VAR__DEPLOYMENT_TARGET     ,
            ENV_VAR__SG_SEND_BASE_URL      ,
            ENV_VAR__API_KEY_NAME          ,
            ENV_VAR__API_KEY_VALUE         ]


class _EnvScrub:                                                                              # Prime FastAPI's API-key auth env vars; tear down cleanly
    def __init__(self, **overrides):
        self.overrides = {ENV_VAR__API_KEY_NAME : API_KEY_NAME ,
                          ENV_VAR__API_KEY_VALUE: API_KEY_VALUE,
                          ENV_VAR__DEPLOYMENT_TARGET: 'laptop' }                              # Avoid Lambda LWA boot path in-process
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


def _mitmproxy_reachable() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1):
            return True
    except OSError:
        return False


def _proxy_body(username: str, password: str) -> dict:
    return {'server'             : f'http://{PROXY_HOST}:{PROXY_PORT}',
            'ignore_https_errors': True                                ,                      # mitmproxy self-signed CA
            'bypass'             : []                                  ,
            'auth'               : {'username': username, 'password': password}}


def _create_body(proxy_body: dict) -> dict:
    return {'browser_config': {'proxy': proxy_body},
            'capture_config': {}                    }


def _build_client():                                                                          # Spin up the full Fast_API__Playwright__Service with a real Playwright__Service
    service = Playwright__Service().setup()                                                   # Default wiring — real Browser__Launcher, real Proxy__Auth__Binder
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa.client()


class test_L3__local_http_proxy(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _mitmproxy_reachable():
            pytest.skip(f'mitmdump not running on {PROXY_HOST}:{PROXY_PORT}')
        if not os.environ.get('SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE'):
            pytest.skip('SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE not set — point at a real Chromium')

    def test__correct_creds_flow_through_http_stack(self):                                    # Gold path — POST /sequence/execute does everything in ONE request so the sync Playwright handle stays on one thread
        with _EnvScrub():
            client = _build_client()

            body = {'browser_config'     : {'proxy': _proxy_body(PROXY_USERNAME, PROXY_PASSWORD)},
                    'capture_config'     : {}                                                     ,
                    'sequence_config'    : {'halt_on_error': True}                                 ,
                    'close_session_after': True                                                    ,
                    'steps'              : [{'action': 'navigate'   , 'url': PROBE_URL, 'timeout_ms': 15000},
                                             {'action': 'get_content', 'inline_in_response': True          }]}

            resp = client.post('/sequence/execute', headers=AUTH_HEADERS, json=body)
            assert resp.status_code == 200, resp.text

            data = resp.json()
            assert data['status']        == 'completed', f'sequence status={data["status"]}: {data["step_results"]}'
            assert data['steps_passed']  == 2
            assert data['steps_failed']  == 0

            get_content = next(r for r in data['step_results'] if r['action'] == 'get_content')   # Extract the inline HTML
            body_html   = get_content.get('content') or ''
            assert '"ip"' in body_html, f'expected IP JSON from ipify, got: {body_html[:200]}'
