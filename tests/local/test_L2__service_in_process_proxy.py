# ═══════════════════════════════════════════════════════════════════════════════
# Local validation — L2 — service-in-process against local mitmproxy
#
# L1 proved the raw CDP Fetch pattern works. L2 proves the SERVICE WIRING
# (Schema__Proxy__Config nested auth → Browser__Launcher → Proxy__Auth__Binder)
# carries those credentials through to Chromium. Drives Playwright__Service
# directly — no HTTP, no FastAPI — with a real sync_playwright()+Chromium
# against the local mitmproxy.
#
# What this guards against:
#   • A caller populates `proxy.auth.username/password`; service silently drops
#     them before Chromium sees them (the original Bug #1 regression).
#   • `ignore_https_errors=True` is ignored for TLS-intercepting proxies — page
#     fails with NET::ERR_CERT_AUTHORITY_INVALID.
#   • CDP binder not invoked → Fetch.enable never sent → auth challenges unanswered.
#   • `Fetch.requestPaused` passthrough missing → every goto hangs to timeout.
#
# Prereqs (same as L1):
#   - mitmdump --listen-port 8888 --proxyauth qa-user:qa-pass-x7
#   - /tmp/py312-sgp/bin/playwright install chromium
#
# Skipped when mitmproxy is not reachable.
# ═══════════════════════════════════════════════════════════════════════════════

import socket
import time
from unittest                                                                                  import TestCase

import pytest

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                      import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Auth__Basic                   import Schema__Proxy__Auth__Basic
from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Config                        import Schema__Proxy__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                      import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                         import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                              import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.host.Safe_Str__Host                       import Safe_Str__Host
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request             import Schema__Session__Create__Request
from sgraph_ai_service_playwright.service.Playwright__Service                                  import Playwright__Service


PROXY_HOST     = '127.0.0.1'
PROXY_PORT     = 8888
PROXY_USERNAME = 'qa-user'                                                                     # Match the running mitmdump --proxyauth qa-user:qa-pass-x7 (see L1 test)
PROXY_PASSWORD = 'qa-pass-x7'

PROBE_URL      = 'https://api.ipify.org/?format=json'                                           # Returns IP JSON — confirms traffic reached the outside via the proxy


def _mitmproxy_reachable() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1):
            return True
    except OSError:
        return False


def _proxy_config(username=PROXY_USERNAME, password=PROXY_PASSWORD) -> Schema__Proxy__Config:
    return Schema__Proxy__Config(server              = f'http://{PROXY_HOST}:{PROXY_PORT}'    ,
                                 bypass              = [Safe_Str__Host('localhost')]          ,
                                 ignore_https_errors = True                                    ,   # mitmproxy is a TLS interceptor — self-signed cert
                                 auth                = Schema__Proxy__Auth__Basic(username=username, password=password))


def _browser_config(proxy: Schema__Proxy__Config) -> Schema__Browser__Config:
    return Schema__Browser__Config(proxy = proxy)                                               # Keep defaults (CHROMIUM + headless) and just attach proxy


class test_L2__service_in_process_proxy(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _mitmproxy_reachable():
            pytest.skip(f'mitmdump not running on {PROXY_HOST}:{PROXY_PORT} — '
                        f'start it with: mitmdump --listen-port {PROXY_PORT} '
                        f'--proxyauth {PROXY_USERNAME}:{PROXY_PASSWORD}')

    def test__correct_creds_navigate_succeeds(self):                                            # Gold path — service + real Chromium + real proxy
        service    = Playwright__Service().setup()
        session_id = None
        try:
            create_req  = Schema__Session__Create__Request(browser_config = _browser_config(_proxy_config())  ,
                                                            capture_config = Schema__Capture__Config()         )
            create_resp = service.session_create(create_req)
            session_id  = create_resp.session_info.session_id

            action_req  = Schema__Action__Request(session_id = session_id                                               ,
                                                   step       = {'action': 'navigate', 'url': PROBE_URL, 'timeout_ms': 15000})
            response    = service.execute_action(action_req)

            assert response.step_result.status == Enum__Step__Status.PASSED, \
                f'navigate failed: {response.step_result.error_message}'

            content_req = Schema__Action__Request(session_id = session_id                                   ,
                                                   step       = {'action': 'get_content', 'inline_in_response': True})
            content_resp = service.execute_action(content_req)
            assert content_resp.step_result.status == Enum__Step__Status.PASSED
            body = str(content_resp.step_result.content or '')
            assert '"ip"' in body, f'expected IP JSON from ipify, got: {body[:200]}'
        finally:
            if session_id is not None:
                service.session_close(session_id)

    def test__wrong_creds_fail_fast_through_service(self):                                      # Regression — wrong creds MUST fail differently from right creds, same way as L1
        service    = Playwright__Service().setup()
        session_id = None
        try:
            create_req  = Schema__Session__Create__Request(browser_config = _browser_config(_proxy_config(username='wronguser', password='wrongpass')),
                                                            capture_config = Schema__Capture__Config()                                                 )
            create_resp = service.session_create(create_req)
            session_id  = create_resp.session_info.session_id

            action_req = Schema__Action__Request(session_id = session_id                                               ,
                                                  step       = {'action': 'navigate', 'url': PROBE_URL, 'timeout_ms': 15000})
            started    = time.time()
            response   = service.execute_action(action_req)
            elapsed    = time.time() - started

            assert response.step_result.status == Enum__Step__Status.FAILED                     # Chromium surfaces ERR_PROXY_AUTH_FAILED / net::ERR_INVALID_AUTH_CREDENTIALS
            assert elapsed < 10, f'wrong creds should fail fast (<10s), took {elapsed:.2f}s — signature of the original "auth silently dropped" regression'
        finally:
            if session_id is not None:
                service.session_close(session_id)
