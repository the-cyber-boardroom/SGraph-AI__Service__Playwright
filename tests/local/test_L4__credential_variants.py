# ═══════════════════════════════════════════════════════════════════════════════
# Local validation — L4 — credential variants regression
#
# The regression assertion for Bug #1: if credentials are correctly wired,
# right creds navigate successfully while wrong/empty creds fail FAST. The
# black-box symptom on Lambda was identical ~5.5 s timeouts for every variant,
# which proved creds never reached Chromium. This test locks in the opposite
# behaviour: different outcomes AND clearly differentiated timings.
#
# Drives the service through /sequence/execute (same single-request pattern as
# L3) — this is the right surface because it exercises the full HTTP + service
# + Chromium + CDP binder chain.
#
# Prereqs (same as L1/L2/L3):
#   - mitmdump --listen-port 8888 --proxyauth qa-user:qa-pass-x7
#   - SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium-1208/chrome-linux64/chrome
#
# Skipped when mitmproxy is not reachable.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
import time
from unittest                                                                                  import TestCase

import pytest

from sg_compute_specs.playwright.core.consts.env_vars                                              import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                       ENV_VAR__CI                    ,
                                                                                                       ENV_VAR__CLAUDE_SESSION        ,
                                                                                                       ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                       ENV_VAR__SG_SEND_BASE_URL      )
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service                       import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.service.Playwright__Service                                  import Playwright__Service


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


class _EnvScrub:
    def __init__(self, **overrides):
        self.overrides = {ENV_VAR__API_KEY_NAME     : API_KEY_NAME ,
                          ENV_VAR__API_KEY_VALUE    : API_KEY_VALUE,
                          ENV_VAR__DEPLOYMENT_TARGET: 'laptop'     }
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


def _build_client():
    service = Playwright__Service().setup()
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa.client()


def _sequence_body(username: str, password: str) -> dict:
    proxy = {'server'             : f'http://{PROXY_HOST}:{PROXY_PORT}',
             'ignore_https_errors': True                                ,
             'bypass'             : []                                  ,
             'auth'               : {'username': username, 'password': password}}
    return {'browser_config'     : {'proxy': proxy}                                       ,
            'capture_config'     : {}                                                      ,
            'sequence_config'    : {'halt_on_error': False}                                ,   # Continue after nav failure so we can always inspect status cleanly
            'close_session_after': True                                                    ,
            'steps'              : [{'action': 'navigate', 'url': PROBE_URL, 'timeout_ms': 15000}]}


class test_L4__credential_variants(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _mitmproxy_reachable():
            pytest.skip(f'mitmdump not running on {PROXY_HOST}:{PROXY_PORT}')
        if not os.environ.get('SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE'):
            pytest.skip('SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE not set')

    def _run_one(self, client, username: str, password: str):
        started = time.time()
        resp    = client.post('/sequence/execute', headers=AUTH_HEADERS, json=_sequence_body(username, password))
        elapsed = time.time() - started
        assert resp.status_code == 200, resp.text
        return resp.json(), elapsed

    def test__different_creds_produce_different_outcomes_and_timings(self):
        with _EnvScrub():
            client = _build_client()

            correct_result, correct_elapsed   = self._run_one(client, PROXY_USERNAME, PROXY_PASSWORD)
            wrong_user_result, wrong_user_elapsed = self._run_one(client, 'wrong-user',    PROXY_PASSWORD)
            wrong_pass_result, wrong_pass_elapsed = self._run_one(client, PROXY_USERNAME, 'wrong-pass' )
            empty_result,      empty_elapsed      = self._run_one(client, 'no-creds',      'no-creds'   )             # Empty strings fail Safe_Str; use clearly-wrong-but-well-formed values

            # ── Outcome differentiation — the critical regression assertion ──
            assert correct_result   ['status'] == 'completed', f'correct creds should complete; got {correct_result["status"]}: {correct_result["step_results"]}'
            assert wrong_user_result['status'] != 'completed', f'wrong user should NOT complete — creds not reaching Chromium? got status={wrong_user_result["status"]}'
            assert wrong_pass_result['status'] != 'completed', f'wrong pass should NOT complete — creds not reaching Chromium? got status={wrong_pass_result["status"]}'
            assert empty_result     ['status'] != 'completed', f'bogus creds should NOT complete; got status={empty_result["status"]}'

            # ── Timing differentiation — wrong creds must fail fast (< 10 s); the Lambda regression showed ~5.5 s for EVERY variant meaning none reached Chromium
            for label, elapsed in [('wrong_user', wrong_user_elapsed),
                                    ('wrong_pass', wrong_pass_elapsed),
                                    ('empty'     , empty_elapsed     )]:
                assert elapsed < 10, f'{label} creds should fail fast (<10 s), took {elapsed:.2f}s — signature of the original regression'

            # ── Correct path completed within reasonable wall-clock ──────────
            assert correct_elapsed < 20, f'correct creds took {correct_elapsed:.2f}s — should be comfortably under 20 s'
