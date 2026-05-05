# ═══════════════════════════════════════════════════════════════════════════════
# Local validation — L2 — service-in-process against local mitmproxy (v0.1.24)
#
# L1 proved the raw CDP Fetch pattern works. L2 proves the SERVICE WIRING
# (Schema__Proxy__Config nested auth → Browser__Launcher → Proxy__Auth__Binder)
# carries those credentials through to Chromium. Drives Playwright__Service
# directly — no HTTP, no FastAPI — with a real sync_playwright()+Chromium
# against the local mitmproxy, exercising the stateless /browser/* surface.
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

from fastapi                                                                                   import HTTPException

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                      import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Get_Content__Request        import Schema__Browser__Get_Content__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Navigate__Request           import Schema__Browser__Navigate__Request
from sg_compute_specs.playwright.core.schemas.browser.Schema__Proxy__Auth__Basic                   import Schema__Proxy__Auth__Basic
from sg_compute_specs.playwright.core.schemas.browser.Schema__Proxy__Config                        import Schema__Proxy__Config
from sg_compute_specs.playwright.core.schemas.primitives.host.Safe_Str__Host                       import Safe_Str__Host
from sg_compute_specs.playwright.core.service.Playwright__Service                                  import Playwright__Service


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

    def test__correct_creds_get_content_succeeds(self):                                        # Gold path — stateless /browser/get-content + real Chromium + real proxy
        service   = Playwright__Service().setup()
        request   = Schema__Browser__Get_Content__Request(url            = PROBE_URL                                      ,
                                                           browser_config = _browser_config(_proxy_config())               ,
                                                           timeout_ms     = 15000                                          )
        response  = service.browser_get_content(request)

        body = str(response.html or '')
        assert '"ip"' in body, f'expected IP JSON from ipify, got: {body[:200]}'

    def test__wrong_creds_fail_fast_through_service(self):                                     # Regression — wrong creds MUST fail differently from right creds, same way as L1
        service   = Playwright__Service().setup()
        request   = Schema__Browser__Navigate__Request(url            = PROBE_URL                                                     ,
                                                        browser_config = _browser_config(_proxy_config(username='wronguser', password='wrongpass')),
                                                        timeout_ms     = 15000                                                        )
        started   = time.time()
        with pytest.raises(HTTPException) as exc_info:
            service.browser_navigate(request)                                                  # One-shot raises HTTPException(502) on step failure
        elapsed = time.time() - started

        assert exc_info.value.status_code == 502                                               # Chromium surfaces ERR_PROXY_AUTH_FAILED / net::ERR_INVALID_AUTH_CREDENTIALS
        assert elapsed < 10, f'wrong creds should fail fast (<10s), took {elapsed:.2f}s — signature of the original "auth silently dropped" regression'
