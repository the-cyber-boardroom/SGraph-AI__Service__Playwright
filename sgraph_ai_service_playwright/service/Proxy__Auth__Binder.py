# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Proxy__Auth__Binder
#
# Wires Schema__Proxy__Auth__Basic → Chromium's CDP Fetch domain so upstream
# proxy 407 CONNECT challenges are answered with the caller's credentials.
#
# Why this exists (from QA bug #1):
#   chromium.launch(proxy={"username": ..., "password": ...}) only works for a
#   subset of Chromium launch paths and silently no-ops on the modern headless
#   shell. The evidence: all credential variants (correct, wrong, empty) on
#   Lambda produced IDENTICAL 5.5 s timeouts, proving creds never reached
#   Chromium at all.
#
# The CDP Fetch dance that actually works:
#   1. `Fetch.enable {handleAuthRequests: True}` — subscribes to auth events.
#   2. `Fetch.authRequired` handler answers 407s with ProvideCredentials.
#   3. `Fetch.requestPaused` handler is MANDATORY — enabling Fetch with
#      handleAuthRequests pauses EVERY request, not just auth-challenged
#      ones. Without a passthrough, every page hangs.
#   4. Both handlers swallow stale-requestId errors because CDP events fire
#      after the navigation has abandoned the request.
#
# Verified locally in tests/local/test_L1__pure_playwright_cdp.py against
# mitmproxy before this class was written — we know the pattern works on
# this Playwright/Chromium combo. This class is the service-level wrapping.
#
# Responsibility: this is the ONLY place that talks CDP in the service (spec
# §10's Step__Executor carve-out applies to page.goto / click / fill — CDP
# session is different). Browser__Launcher does process lifecycle; this class
# does per-page auth setup.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                            import Any

from osbot_utils.type_safe.Type_Safe                                                   import Type_Safe

from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Auth__Basic           import Schema__Proxy__Auth__Basic


class Proxy__Auth__Binder(Type_Safe):

    def bind(self, context: Any, page: Any, auth: Schema__Proxy__Auth__Basic) -> None:   # No-op when auth is None; idempotent per page
        if auth is None:
            return
        username    = str(auth.username)
        password    = str(auth.password)
        cdp_session = context.new_cdp_session(page)
        cdp_session.send('Fetch.enable', {'handleAuthRequests': True})

        def on_auth_required(params):
            try:
                cdp_session.send('Fetch.continueWithAuth', {
                    'requestId'            : params['requestId']                     ,
                    'authChallengeResponse': {'response': 'ProvideCredentials'      ,
                                              'username': username                  ,
                                              'password': password                  }})
            except Exception:                                                        # Stale requestId — CDP event arrived after navigation abandoned the request
                pass

        def on_request_paused(params):                                                # MANDATORY passthrough — Fetch.enable pauses ALL requests when handleAuthRequests=True
            try:
                cdp_session.send('Fetch.continueRequest', {'requestId': params['requestId']})
            except Exception:                                                        # Stale requestId
                pass

        cdp_session.on('Fetch.authRequired' , on_auth_required )
        cdp_session.on('Fetch.requestPaused', on_request_paused)
