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

from sgraph_ai_service_playwright.consts.env_vars                                             import ENV_VAR__CHROMIUM_EXECUTABLE
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                     import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Config                       import Schema__Proxy__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                           import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Provider                       import Enum__Browser__Provider
from sgraph_ai_service_playwright.schemas.primitives.host.Safe_Str__Host                      import Safe_Str__Host
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                   import Session_Id
from sgraph_ai_service_playwright.service.Browser__Launcher                                    import Browser__Launcher


class _EnvScrub:                                                                   # Snapshot + restore just the env vars this class reads — keeps tests hermetic without monkeypatch
    VARS = (ENV_VAR__CHROMIUM_EXECUTABLE,)
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


def _cfg(**overrides) -> Schema__Browser__Config:
    return Schema__Browser__Config(**overrides)                                    # Defaults match Schema__Browser__Config defaults (CHROMIUM, LOCAL_SUBPROCESS, headless=True)


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


class test_assert_browser_supported(TestCase):

    def test__rejects_firefox_and_webkit(self):
        bl = Browser__Launcher()
        for name in (Enum__Browser__Name.FIREFOX, Enum__Browser__Name.WEBKIT):
            with pytest.raises(NotImplementedError) as exc:
                bl.assert_browser_supported(_cfg(browser_name=name))
            assert name.value in str(exc.value)

    def test__allows_chromium(self):
        bl = Browser__Launcher()
        bl.assert_browser_supported(_cfg())


class test_build_launch_kwargs(TestCase):

    def test__defaults_are_headless_no_exe_no_args(self):
        with _EnvScrub():                                                          # No executable override — don't leak sandbox path into kwargs
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg())
            assert kw == {'headless': True}                                        # No args/executable/proxy populated

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

    def test__proxy_flattened_to_dict(self):                                       # Schema__Proxy__Config -> Playwright proxy dict
        with _EnvScrub():
            proxy = Schema__Proxy__Config(server   = 'http://proxy.example.com:8080'              ,
                                          username = 'u'                                          ,
                                          password = 'p'                                          ,
                                          bypass   = [Safe_Str__Host('localhost'), Safe_Str__Host('internal.corp')])
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(proxy=proxy))
            assert kw['proxy'] == {'server'  : 'http://proxy.example.com:8080'    ,
                                   'username': 'u'                                ,
                                   'password': 'p'                                ,
                                   'bypass'  : 'localhost,internal.corp'          }

    def test__proxy_without_auth_omits_username_password(self):
        with _EnvScrub():
            proxy = Schema__Proxy__Config(server='http://proxy:3128')
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(proxy=proxy))
            assert kw['proxy'] == {'server': 'http://proxy:3128'}                   # No username/password/bypass keys

    def test__headless_false_is_preserved(self):
        with _EnvScrub():
            bl = Browser__Launcher()
            kw = bl.build_launch_kwargs(_cfg(headless=False))
            assert kw['headless'] is False


class test_registry(TestCase):

    def test__register_and_stop_closes_browser_and_removes_from_registry(self):
        bl  = Browser__Launcher()
        sid = Session_Id()
        fb  = _FakeBrowser()
        bl.register(sid, fb)
        assert bl.active_session_ids() == [sid]
        bl.stop(sid)
        assert fb.closed is True
        assert bl.active_session_ids() == []

    def test__stop_unknown_session_is_silent_noop(self):
        bl  = Browser__Launcher()
        bl.stop(Session_Id())                                                      # No exception, no side effect
        assert bl.active_session_ids() == []

    def test__stop_swallows_browser_close_errors(self):                            # Already-dead browsers shouldn't crash the whole service
        bl  = Browser__Launcher()
        sid = Session_Id()
        bl.register(sid, _RaisingBrowser())
        bl.stop(sid)
        assert bl.active_session_ids() == []                                       # Still removed from registry despite raised error

    def test__stop_all_closes_every_registered_browser(self):
        bl  = Browser__Launcher()
        sids = [Session_Id(), Session_Id(), Session_Id()]
        browsers = [_FakeBrowser(f'b{i}') for i in range(3)]
        for sid, fb in zip(sids, browsers):
            bl.register(sid, fb)
        bl.stop_all()
        assert all(fb.closed for fb in browsers)
        assert bl.active_session_ids() == []


class test_healthcheck(TestCase):

    def test__reports_playwright_started_false_and_zero_browsers_by_default(self):
        bl = Browser__Launcher()
        hc = bl.healthcheck()
        assert hc.check_name == 'browser_launcher'
        assert hc.healthy    is True
        assert 'playwright_started=False' in str(hc.detail)
        assert 'active_browsers=0'        in str(hc.detail)

    def test__reports_active_browser_count(self):
        bl = Browser__Launcher()
        bl.register(Session_Id(), _FakeBrowser())
        bl.register(Session_Id(), _FakeBrowser())
        hc = bl.healthcheck()
        assert 'active_browsers=2' in str(hc.detail)
