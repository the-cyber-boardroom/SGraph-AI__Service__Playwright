# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests — Browser__Launcher (real Chromium)
#
# These tests spawn actual Chromium processes. They're skipped unless a
# Chromium binary is discoverable — either via Playwright's default resolution
# (which needs `playwright install chromium` matching the package version) or
# via SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE pointing at a pre-installed build.
#
# In the project's Docker image the default path works; in this sandbox /
# laptops with system Chrome, export the env var.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                                 import TestCase

import pytest

from sgraph_ai_service_playwright.consts.env_vars                                             import ENV_VAR__CHROMIUM_EXECUTABLE
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                     import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                   import Session_Id
from sgraph_ai_service_playwright.service.Browser__Launcher                                    import Browser__Launcher


def _chromium_available() -> bool:
    exe = os.environ.get(ENV_VAR__CHROMIUM_EXECUTABLE)                             # Fast path: explicit override
    if exe and os.path.isfile(exe):
        return True
    try:                                                                           # Fallback: can Playwright resolve a default Chromium?
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.exists(path)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_available(),
                                reason=f'No Chromium available. Set {ENV_VAR__CHROMIUM_EXECUTABLE} or run `playwright install chromium`.')


class test_launch_and_use_real_chromium(TestCase):

    def setUp(self):
        self.launcher = Browser__Launcher()

    def tearDown(self):
        self.launcher.stop_all()                                                   # Always shut Chromium + sync_playwright down

    def test__launch_returns_a_live_browser_that_can_render_html(self):
        browser = self.launcher.launch(Schema__Browser__Config())                  # Defaults: chromium, LOCAL_SUBPROCESS, headless=True
        try:
            context = browser.new_context()
            page    = context.new_page()
            page.set_content('<html><body><h1 id="t">hello from sg-playwright</h1></body></html>')
            assert page.inner_text('#t') == 'hello from sg-playwright'
        finally:
            browser.close()

    def test__register_then_stop_closes_the_browser(self):
        browser = self.launcher.launch(Schema__Browser__Config())
        sid     = Session_Id()
        self.launcher.register(sid, browser)
        assert sid in self.launcher.active_session_ids()
        self.launcher.stop(sid)
        assert sid not in self.launcher.active_session_ids()
        assert browser.is_connected() is False                                     # Playwright reports browser as closed

    def test__two_browsers_are_independent(self):                                  # Critical for multi-session service
        b1 = self.launcher.launch(Schema__Browser__Config())
        b2 = self.launcher.launch(Schema__Browser__Config())
        try:
            assert b1 is not b2
            assert b1.is_connected() and b2.is_connected()
        finally:
            b1.close()
            b2.close()

    def test__stop_all_tears_down_everything(self):
        b1 = self.launcher.launch(Schema__Browser__Config())
        b2 = self.launcher.launch(Schema__Browser__Config())
        s1, s2 = Session_Id(), Session_Id()
        self.launcher.register(s1, b1)
        self.launcher.register(s2, b2)
        self.launcher.stop_all()
        assert self.launcher.active_session_ids() == []
        assert self.launcher.playwright is None
        assert b1.is_connected() is False
        assert b2.is_connected() is False

    def test__healthcheck_reports_started_after_launch(self):
        self.launcher.launch(Schema__Browser__Config())                            # Auto-starts playwright
        hc = self.launcher.healthcheck()
        assert 'playwright_started=True' in str(hc.detail)
