# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Proxy__Auth__Binder (CDP Fetch domain wiring for proxy auth)
#
# Real CDP sessions require a live Playwright Chromium — those live in the
# integration / L1 harness. This file exercises the binder against a fake
# CDP session that records sends + event subscriptions and lets us synthesise
# the CDP event callbacks ourselves, so we can assert:
#
#   • Fetch.enable is sent with handleAuthRequests=True on bind()
#   • Fetch.authRequired subscribers answer with ProvideCredentials + creds
#   • Fetch.requestPaused subscribers continue requests (mandatory passthrough —
#     Fetch.enable with handleAuthRequests pauses ALL requests, not just auth)
#   • Stale requestId exceptions are swallowed (CDP fires events after the
#     navigation abandons the request)
#   • auth=None is a clean no-op (no CDP traffic whatsoever)
#
# No mocks / patches — just a Type_Safe-friendly _FakeCDPSession.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Auth__Basic        import Schema__Proxy__Auth__Basic
from sgraph_ai_service_playwright.service.Proxy__Auth__Binder                       import Proxy__Auth__Binder


class _FakeCDPSession:                                                              # Records every .send() and .on() — tests fire events by looking up subscribed callbacks
    def __init__(self):
        self.sends       = []                                                       # List[(method, params)]
        self.subscribers = {}                                                       # event_name -> callback
        self.raise_on_send_for = None                                               # Simulate stale requestId

    def send(self, method, params):
        self.sends.append((method, params))
        if self.raise_on_send_for is not None and method == self.raise_on_send_for:
            raise RuntimeError(f'simulated stale requestId on {method}')

    def on(self, event_name, callback):
        self.subscribers[event_name] = callback                                     # Single handler per event is enough for binder's shape


class _FakeContext:                                                                 # Not exercised here (binder asks `context.new_cdp_session(page)` — this lets us inject our own session)
    def __init__(self, cdp_session):
        self._cdp_session = cdp_session

    def new_cdp_session(self, page):
        return self._cdp_session


class _FakePage:                                                                    # Binder doesn't touch .page — it's only passed through to new_cdp_session
    pass


class test_bind(TestCase):

    def test__noop_when_auth_is_none(self):
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), None)
        assert cdp.sends       == []                                                # No CDP traffic
        assert cdp.subscribers == {}                                                # No event subscriptions

    def test__enables_fetch_with_handleAuthRequests(self):
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        auth    = Schema__Proxy__Auth__Basic(username='qa-user', password='qa-pass-x7')    # Basic_Auth variants preserve hyphens (osbot Safe_Str__Username silently underscored them)
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), auth)
        assert cdp.sends[0] == ('Fetch.enable', {'handleAuthRequests': True})              # First wire — subscribes to auth events
        assert 'Fetch.authRequired'  in cdp.subscribers
        assert 'Fetch.requestPaused' in cdp.subscribers
        assert str(auth.username) == 'qa-user'                                             # Regression: Basic_Auth__Username preserves hyphens verbatim
        assert str(auth.password) == 'qa-pass-x7'                                          # Regression: Basic_Auth__Password preserves hyphens verbatim

    def test__authRequired_handler_answers_with_provided_credentials(self):
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        auth    = Schema__Proxy__Auth__Basic(username='qa-user', password='qa-pass-x7')    # Basic_Auth variants preserve hyphens / dots — osbot Safe_Str__Username silently underscored them
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), auth)
        cdp.sends.clear()                                                           # Drop the setup send so we can look at the handler's send alone

        cdp.subscribers['Fetch.authRequired']({'requestId': 'req-42'})              # Synthesize the CDP event
        assert cdp.sends == [('Fetch.continueWithAuth',
                              {'requestId'            : 'req-42'                                         ,
                               'authChallengeResponse': {'response': 'ProvideCredentials'              ,
                                                         'username': 'qa-user'                         ,
                                                         'password': 'qa-pass-x7'                      }})]

    def test__requestPaused_handler_continues_every_request(self):                  # MANDATORY passthrough — Fetch.enable with handleAuthRequests=True pauses every request
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        auth    = Schema__Proxy__Auth__Basic(username='u', password='p')
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), auth)
        cdp.sends.clear()

        cdp.subscribers['Fetch.requestPaused']({'requestId': 'req-99'})
        assert cdp.sends == [('Fetch.continueRequest', {'requestId': 'req-99'})]

    def test__authRequired_swallows_stale_requestId_errors(self):                   # CDP event arrived after navigation abandoned the request — must not crash page flow
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        auth    = Schema__Proxy__Auth__Basic(username='u', password='p')
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), auth)
        cdp.raise_on_send_for = 'Fetch.continueWithAuth'

        cdp.subscribers['Fetch.authRequired']({'requestId': 'stale-1'})             # No exception should propagate

    def test__requestPaused_swallows_stale_requestId_errors(self):
        cdp     = _FakeCDPSession()
        context = _FakeContext(cdp)
        auth    = Schema__Proxy__Auth__Basic(username='u', password='p')
        binder  = Proxy__Auth__Binder()
        binder.bind(context, _FakePage(), auth)
        cdp.raise_on_send_for = 'Fetch.continueRequest'

        cdp.subscribers['Fetch.requestPaused']({'requestId': 'stale-2'})            # No exception should propagate
