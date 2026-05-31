# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Session__Registry (Φ7)
# ═══════════════════════════════════════════════════════════════════════════════

import time
from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config         import Schema__Browser__Config
from sg_compute_specs.playwright.core.service.Session__Registry                       import Session__Registry, Session__State


# ── Fakes: launcher + browser + context + page ────────────────────────────────

class _Fake_Page:
    def __init__(self): self.handlers = {}
    def on(self, evt, handler): self.handlers[evt] = handler

class _Fake_Context:
    def __init__(self): self.pages = []
    def new_page(self):
        p = _Fake_Page()
        self.pages.append(p)
        return p

class _Fake_Browser:
    def __init__(self):
        self.contexts = []
        self.closed   = False
        self.context_kwargs : list = []                                              # Records every new_context(**kwargs) call so tests can assert on ignore_https_errors etc.
    def new_context(self, **kwargs):
        self.context_kwargs.append(kwargs)
        ctx = _Fake_Context()
        self.contexts.append(ctx)
        return ctx

class _Fake_Launch_Result:
    def __init__(self, browser): self.browser = browser

class _Fake_Launcher:
    def __init__(self):
        self.launched : list = []
        self.stopped  : list = []
        self.registry = {}
    def launch(self, config):
        browser = _Fake_Browser()
        self.launched.append(browser)
        return _Fake_Launch_Result(browser)
    def register(self, sid, result):
        self.registry[str(sid)] = result
    def stop(self, sid):
        self.stopped.append(str(sid))
        return 1                                                                  # ms taken; placeholder for tests


def _registry():
    r = Session__Registry()
    r.browser_launcher = _Fake_Launcher()
    return r


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_open_get_close(TestCase):

    def test__open_launches_browser_attaches_buffer_returns_state(self):
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=60_000)
        assert isinstance(state, Session__State)
        assert state.session_id is not None
        assert state.browser   is not None
        assert state.page      is not None
        assert state.buffer    is not None
        assert reg.browser_launcher.launched                                       # browser was launched
        assert str(state.session_id) in reg.session_ids()

    def test__get_refreshes_ttl_on_access(self):
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=60_000)
        before = state.expires_at_ms
        time.sleep(0.005)                                                          # 5ms — enough to see the bump
        again = reg.get(str(state.session_id))
        assert again is state
        assert again.expires_at_ms >= before                                       # Bumped (or equal at the same wall-clock ms)

    def test__get_returns_none_for_unknown_session(self):
        reg = _registry()
        assert reg.get('does-not-exist') is None

    def test__close_returns_true_and_calls_launcher_stop(self):
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=60_000)
        sid   = str(state.session_id)
        assert reg.close(sid)       is True
        assert sid in reg.browser_launcher.stopped
        assert reg.get(sid)         is None

    def test__close_unknown_session_returns_false(self):
        reg = _registry()
        assert reg.close('nope') is False


class test_ttl_expiry(TestCase):

    def test__expired_session_is_not_returned_and_is_closed(self):
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=1)                      # 1ms TTL → expires almost immediately
        sid   = str(state.session_id)
        time.sleep(0.050)                                                           # 50ms — guarantees expiry on any CI timing granularity
        result = reg.get(sid)                                                       # get() detects expiry + cleans up
        assert result is None
        assert sid in reg.browser_launcher.stopped

    def test__sweep_expired_closes_all_past_deadline(self):                         # Asserts OBSERVABLE state, not the return count. open() implicitly sweeps so the 1st session can be cleaned by the 2nd open(); a stable test checks what's LEFT after the explicit sweep, not how many that sweep removed
        reg = _registry()
        s1  = reg.open(Schema__Browser__Config(), ttl_ms=50)                       # 50ms — survives the s2.open() call, expires before the sleep ends
        s2  = reg.open(Schema__Browser__Config(), ttl_ms=60_000)                   # stays alive throughout
        time.sleep(0.200)                                                           # 200ms — well past s1's TTL, well under s2's
        reg.sweep_expired()
        active = reg.session_ids()
        assert str(s1.session_id) not in active                                     # s1 swept
        assert str(s2.session_id) in     active                                     # s2 alive
        assert str(s1.session_id) in reg.browser_launcher.stopped                   # browser stopped for s1


# ─── ISSUE-A regression: session worker must honour ignore_https_errors ─────────
# The @Content debrief (31 May 2026) reported /session/{id}/act navigation to
# https://dev.vault.sgraph.ai failing with ERR_CERT_AUTHORITY_INVALID, while the
# SAME url worked via /sequence/execute and /inspect. Root cause: Session__Registry's
# _get_or_create_page didn't read SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS the way
# Sequence__Runner.get_or_create_page did. This test pins that parity.

import os

from sg_compute_specs.playwright.core.consts.env_vars import ENV_VAR__IGNORE_HTTPS_ERRORS


class test_ignore_https_errors_parity(TestCase):

    def setUp(self):
        self._old = os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def tearDown(self):
        if self._old is not None:
            os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = self._old
        else:
            os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def test__env_var_set_passes_ignore_https_errors_to_new_context(self):
        os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = '1'
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=60_000)
        try:
            kwargs_list = state.browser.context_kwargs
            assert kwargs_list, 'expected new_context to have been called'
            assert kwargs_list[0].get('ignore_https_errors') is True
        finally:
            reg.close(str(state.session_id))

    def test__env_var_unset_omits_the_kwarg(self):                                          # No env var → no ignore_https_errors kwarg (default-secure)
        reg   = _registry()
        state = reg.open(Schema__Browser__Config(), ttl_ms=60_000)
        try:
            kwargs_list = state.browser.context_kwargs
            assert kwargs_list, 'expected new_context to have been called'
            assert 'ignore_https_errors' not in kwargs_list[0]
        finally:
            reg.close(str(state.session_id))
