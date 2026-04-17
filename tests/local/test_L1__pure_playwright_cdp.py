# ═══════════════════════════════════════════════════════════════════════════════
# Local validation — L1 — pure Playwright + CDP Fetch proxy auth
#
# Proves the CDP Fetch handler pattern works on THIS machine's Chromium before
# any service-level refactor. No service imports, no FastAPI — just raw
# Playwright.
#
# Per QA brief `team/humans/dinis_cruz/briefs/04/17/local-validation-spec__proxy-fix.md`:
#   - Chromium's `launch(proxy=...)` only carries `server` + `bypass`.
#   - Credentials go through the CDP Fetch domain, registered per-page post-
#     context, before the first navigation.
#   - `Fetch.enable {handleAuthRequests: True}` pauses ALL requests — the paired
#     `Fetch.requestPaused` passthrough is mandatory or every page hangs.
#   - Both handlers must swallow stale-requestId errors (CDP events fire after
#     navigations abandon requests).
#
# Prereqs:
#   - mitmdump --listen-port 8888 --proxyauth qa-user:qa-pass-x7  (running)
#   - `/tmp/py312-sgp/bin/playwright install chromium` (already done)
#   - `/tmp/py312-sgp/bin/python -m pytest tests/local/test_L1__pure_playwright_cdp.py`
#
# Skipped when mitmproxy is not reachable — this is a developer-machine test,
# not a CI gate.
# ═══════════════════════════════════════════════════════════════════════════════

import socket
import time
from unittest                                                                       import TestCase

import pytest
from playwright.sync_api                                                            import sync_playwright


PROXY_HOST     = '127.0.0.1'
PROXY_PORT     = 8888
PROXY_USERNAME = 'qa-user'
PROXY_PASSWORD = 'qa-pass-x7'

PROBE_URL      = 'https://api.ipify.org/?format=json'                               # Returns the outbound IP — confirms traffic actually traversed the proxy


def _mitmproxy_reachable() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1):
            return True
    except OSError:
        return False


class test_L1__pure_playwright_cdp(TestCase):

    @classmethod
    def setUpClass(cls):
        if not _mitmproxy_reachable():
            pytest.skip(f'mitmdump not running on {PROXY_HOST}:{PROXY_PORT} — '
                        f'start it with: mitmdump --listen-port {PROXY_PORT} '
                        f'--proxyauth {PROXY_USERNAME}:{PROXY_PASSWORD}')

    def _register_cdp_auth(self, cdp_session, username: str, password: str):
        cdp_session.send('Fetch.enable', {'handleAuthRequests': True})

        def on_auth_required(params):
            try:
                cdp_session.send('Fetch.continueWithAuth', {
                    'requestId'            : params['requestId'],
                    'authChallengeResponse': {'response': 'ProvideCredentials',
                                              'username': username          ,
                                              'password': password          }})
            except Exception:                                                       # Stale requestId — CDP event arrived after navigation abandoned the request
                pass

        def on_request_paused(params):
            try:
                cdp_session.send('Fetch.continueRequest', {'requestId': params['requestId']})
            except Exception:                                                       # Stale requestId
                pass

        cdp_session.on('Fetch.authRequired' , on_auth_required )
        cdp_session.on('Fetch.requestPaused', on_request_paused)

    def test__correct_creds_succeed(self):                                          # Gold path — end-to-end proves the pattern works
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless = True                                   ,
                                         proxy   = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}'})
            try:
                context = browser.new_context(ignore_https_errors=True)             # mitmproxy uses a self-signed CA — real prod TLS interceptors behave the same
                page    = context.new_page()
                self._register_cdp_auth(context.new_cdp_session(page), PROXY_USERNAME, PROXY_PASSWORD)

                page.goto(PROBE_URL, timeout=15_000)
                body = page.content()
                assert '"ip"' in body, f'expected IP JSON from ipify, got: {body[:200]}'
            finally:
                browser.close()

    def test__wrong_creds_fail_fast(self):                                          # The regression assertion — wrong creds MUST fail differently from right creds
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless = True                                   ,
                                         proxy   = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}'})
            try:
                context = browser.new_context(ignore_https_errors=True)
                page    = context.new_page()
                self._register_cdp_auth(context.new_cdp_session(page), 'wrong-user', 'wrong-pass')

                started = time.time()
                with pytest.raises(Exception):                                      # Chromium surfaces as ERR_PROXY_AUTH_FAILED / net::ERR_INVALID_AUTH_CREDENTIALS
                    page.goto(PROBE_URL, timeout=15_000)
                elapsed = time.time() - started
                assert elapsed < 10, f'wrong creds should fail fast (<10 s), took {elapsed:.2f}s'
            finally:
                browser.close()

    def test__missing_requestPaused_handler_hangs(self):                            # Documents the critical gotcha — Fetch.enable with handleAuthRequests pauses EVERYTHING
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless = True                                   ,
                                         proxy   = {'server': f'http://{PROXY_HOST}:{PROXY_PORT}'})
            try:
                context = browser.new_context(ignore_https_errors=True)
                page    = context.new_page()
                cdp     = context.new_cdp_session(page)
                cdp.send('Fetch.enable', {'handleAuthRequests': True})              # Only auth handler — no passthrough
                cdp.on('Fetch.authRequired', lambda p: cdp.send('Fetch.continueWithAuth', {
                    'requestId'            : p['requestId'],
                    'authChallengeResponse': {'response': 'ProvideCredentials',
                                              'username': PROXY_USERNAME      ,
                                              'password': PROXY_PASSWORD      }}))

                with pytest.raises(Exception):                                      # Every paused request stays paused → goto times out
                    page.goto(PROBE_URL, timeout=5_000)
            finally:
                browser.close()
