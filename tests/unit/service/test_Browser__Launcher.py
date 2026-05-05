# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Browser__Launcher (non-launch surface)
#
# Real-Chromium tests live in tests/integration/service/test_Browser__Launcher.py.
# This file exercises everything that does NOT spawn a browser: provider /
# browser-name gates, launch_kwargs construction, registry behaviour, health,
# and stop() with fakes. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                                   import Any
from unittest                                                                                 import TestCase

import pytest

from sg_compute_specs.playwright.core.consts.env_vars                                             import ENV_VAR__CHROMIUM_EXECUTABLE, ENV_VAR__DEFAULT_PROXY_URL
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                     import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Launch__Result              import Schema__Browser__Launch__Result
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                           import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Provider                       import Enum__Browser__Provider
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Session_Id                   import Session_Id
from sg_compute_specs.playwright.core.service.Browser__Launcher                                    import Browser__Launcher


class _EnvScrub:                                                                   # Snapshot + restore just the env vars this class reads — keeps tests hermetic without monkeypatch
    VARS = (ENV_VAR__CHROMIUM_EXECUTABLE, ENV_VAR__DEFAULT_PROXY_URL)
    def __enter__(self):
        self.saved = {k: os.environ.get(k) for k in self.VARS}
        for k in self.VARS: os.environ.pop(k, None)
        return self
    def __exit__(self, *a):
        for k, v in self.saved.items():
            if v is None: os.environ.pop(k, None)
            else        : os.environ[k] = v


class _FakeBrowser:                                                                # Stand-in for a Playwright Browser; records close()
    def __init__(self, name='b'):
        self.name   = name
        self.closed = False
    def close(self):
        if self.closed: raise RuntimeError('already closed')
        self.closed = True


class _RaisingBrowser(_FakeBrowser):
    def close(self):
        raise RuntimeError('boom — simulated dead browser')


class _FakePlaywright:                                                             # sync_playwright() stand-in — records stop() for assertions
    def __init__(self):
        self.stopped = False
    def stop(self):
        self.stopped = True


def _cfg(**overrides) -> Schema__Browser__Config:
    return Schema__Browser__Config(**overrides)                                    # Defaults match Schema__Browser__Config defaults (CHROMIUM, LOCAL_SUBPROCESS, headless=True)


def _launch_result(browser=None, playwright=None) -> Schema__Browser__Launch__Result:
    return Schema__Browser__Launch__Result(browser             = browser    if browser    is not None else _FakeBrowser()   ,
                                            playwright          = playwright if playwright is not None else _FakePlaywright(),
                                            playwright_start_ms = 0                                                          ,
                                            browser_launch_ms   = 0                                                          )


class test_assert_provider_supported(TestCase):

    def test__rejects_cdp_connect(self):
        bl  = Browser__Launcher()
        cfg = _cfg(provider=Enum__Browser__Provider.CDP_CONNECT)
        with pytest.raises(NotImplementedError) as exc:
            bl.assert_provider_supported(cfg)
        assert 'cdp_connect' in str(exc.value)

    def test__rejects_browserless(self):
        bl  = Browser__Launcher()
        cfg = _cfg(provider=Enum__Browser__Provider.BROWSERLESS)
        with pytest.raises(NotImplementedError):
            bl.assert_provider_supported(cfg)

    def test__allows_local_subprocess(self):                                       # Default path; no exception
        bl  = Browser__Launcher()
        bl.assert_provider_supported(_cfg())


class test_browser_engine_support(TestCase):                                        # All three Playwright engines are supported — no runtime gate

    def test__no_assert_browser_supported_method(self):                             # Regression: the legacy gate was removed alongside Firefox/WebKit wiring
        assert not hasattr(Browser__Launcher, 'assert_browser_supported')


class test_build_launch_kwargs(TestCase):

    def test__defaults_apply_chromium_sandbox_and_shm_flags(self):
        with _EnvScrub():                                                          # No executable override — don't leak sandbox path into kwargs
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg())
            assert kw == {'headless': True                                                                       ,
                          'args'    : ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--single-process', '--use-mock-keychain']}  # Spec §5.2 mandated defaults — without these Chromium dies on Lambda

    def test__env_var_sets_executable_path(self):
        with _EnvScrub():
            os.environ[ENV_VAR__CHROMIUM_EXECUTABLE] = '/opt/custom/chrome'
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg())
            assert kw['executable_path'] == '/opt/custom/chrome'

    def test__launch_args_flow_through(self):
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(launch_args=['--no-sandbox', '--disable-gpu']))
            assert kw['args'] == ['--no-sandbox', '--disable-gpu']

    def test__no_proxy_when_env_var_unset(self):                                   # Lambda / laptop with no sidecar — no proxy key in launch kwargs
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg())
            assert 'proxy' not in kw

    def test__proxy_server_set_from_env_var(self):                                 # EC2 sidecar deployment — proxy URL from boot-time env, no credentials
        with _EnvScrub():
            os.environ[ENV_VAR__DEFAULT_PROXY_URL] = 'http://agent-mitmproxy:8080'
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg())
            assert kw['proxy'] == {'server': 'http://agent-mitmproxy:8080'}         # Server only — no username/password/bypass
            assert 'username' not in kw['proxy']
            assert 'password' not in kw['proxy']

    def test__proxy_env_var_applies_to_all_browser_types(self):                    # Same env var, same result regardless of browser engine
        with _EnvScrub():
            os.environ[ENV_VAR__DEFAULT_PROXY_URL] = 'http://agent-mitmproxy:8080'
            bl = Browser__Launcher()
            for browser_name in (Enum__Browser__Name.CHROMIUM, Enum__Browser__Name.FIREFOX, Enum__Browser__Name.WEBKIT):
                kw = bl.build_launch_kwargs(_cfg(browser_name=browser_name))
                assert kw['proxy'] == {'server': 'http://agent-mitmproxy:8080'}

    def test__firefox_gets_no_chromium_default_args(self):                         # --no-sandbox et al would break Firefox launch; only Chromium gets them
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(browser_name=Enum__Browser__Name.FIREFOX))
            assert 'args' not in kw                                                # Empty args list means omit the key entirely — Playwright applies engine defaults

    def test__webkit_gets_no_chromium_default_args(self):
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(browser_name=Enum__Browser__Name.WEBKIT))
            assert 'args' not in kw

    def test__chromium_executable_override_does_not_leak_to_firefox(self):         # SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE is Chromium-specific
        with _EnvScrub():
            os.environ[ENV_VAR__CHROMIUM_EXECUTABLE] = '/opt/custom/chrome'
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(browser_name=Enum__Browser__Name.FIREFOX))
            assert 'executable_path' not in kw

    def test__headless_false_is_preserved(self):
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(headless=False))
            assert kw['headless'] is False


class test_registry(TestCase):

    def test__register_and_stop_closes_browser_and_playwright_and_removes_from_registry(self):
        bl  = Browser__Launcher()
        sid = Session_Id()
        fb  = _FakeBrowser()
        fp  = _FakePlaywright()
        bl.register(sid, _launch_result(browser=fb, playwright=fp))
        assert bl.active_session_ids() == [sid]
        bl.stop(sid)
        assert fb.closed  is True                                                  # Browser closed
        assert fp.stopped is True                                                  # AND its paired sync_playwright runtime stopped — fresh-per-call contract
        assert bl.active_session_ids() == []

    def test__stop_unknown_session_is_silent_noop(self):
        bl  = Browser__Launcher()
        bl.stop(Session_Id())                                                      # No exception, no side effect
        assert bl.active_session_ids() == []

    def test__stop_swallows_browser_close_errors(self):                            # Already-dead browsers shouldn't crash the whole service
        bl  = Browser__Launcher()
        sid = Session_Id()
        bl.register(sid, _launch_result(browser=_RaisingBrowser()))
        bl.stop(sid)
        assert bl.active_session_ids() == []                                       # Still removed from registry despite raised error

    def test__stop_all_closes_every_registered_browser(self):
        bl  = Browser__Launcher()
        sids = [Session_Id(), Session_Id(), Session_Id()]
        browsers = [_FakeBrowser(f'b{i}') for i in range(3)]
        for sid, fb in zip(sids, browsers):
            bl.register(sid, _launch_result(browser=fb))
        bl.stop_all()
        assert all(fb.closed for fb in browsers)
        assert bl.active_session_ids() == []


class test_healthcheck(TestCase):

    def test__reports_zero_browsers_by_default(self):
        bl = Browser__Launcher()
        hc = bl.healthcheck()
        assert hc.check_name == 'browser_launcher'
        assert hc.healthy    is True
        assert 'active_browsers=0' in str(hc.detail)                               # No more singleton playwright to report — every active browser has its own runtime

    def test__reports_active_browser_count(self):
        bl = Browser__Launcher()
        bl.register(Session_Id(), _launch_result())
        bl.register(Session_Id(), _launch_result())
        hc = bl.healthcheck()
        assert 'active_browsers=2' in str(hc.detail)
