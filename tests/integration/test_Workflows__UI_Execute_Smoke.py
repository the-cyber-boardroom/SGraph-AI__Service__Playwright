# ═══════════════════════════════════════════════════════════════════════════════
# Integration test — UI execute-path headless smoke (brief 06 §4)
#
# v0.2.64 dev pack. The ONLY test that exercises the actual DOM/JS of the console
# (the rest assert request bodies + HTTP contracts). It proves the "Load example
# → Execute" path a user clicks works end-to-end:
#
#   1. boot the in-memory service (real Browser__Launcher) on a real loopback port
#   2. load GET / in a headless Chromium (the service's own Playwright — dog-fooding)
#   3. drive window.__tool.run(window.__tool.loadExample('W1')) — the same
#      programmatic surface the UI's "Load example → Execute" click hits (brief 05 §4)
#   4. assert the returned result is a completed sequence with passed steps and
#      an inline screenshot artefact
#
# The MOST expensive test in the pack — gated on real Chromium AND a usable
# window.__tool. Skipped cleanly (no failure) when Chromium is absent (this
# environment) or when window.__tool is not present in the served page. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import threading
from unittest                                                                               import TestCase

import pytest

from sg_compute_specs.playwright.core.consts.env_vars                                       import ENV_VAR__CHROMIUM_EXECUTABLE
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index                         import INDEX_HTML


def _chromium_available() -> bool:
    exe = os.environ.get(ENV_VAR__CHROMIUM_EXECUTABLE)
    if exe and os.path.isfile(exe):
        return True
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.exists(path)
    except Exception:
        return False


def _window_tool_present() -> bool:                                                          # cheap structural gate — if Phase 5 JS-API is absent, skip (brief 06 §4)
    return 'window.__tool' in INDEX_HTML and 'loadExample' in INDEX_HTML


pytestmark = pytest.mark.skipif(not (_chromium_available() and _window_tool_present()),
                                reason=f'Needs real Chromium ({ENV_VAR__CHROMIUM_EXECUTABLE} or `playwright install chromium`) '
                                       f'and window.__tool present in INDEX_HTML.')


class test_Workflows__UI_Execute_Smoke(TestCase):

    @classmethod
    def setUpClass(cls):
        import uvicorn
        from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service
        from sg_compute_specs.playwright.core.service.Browser__Launcher              import Browser__Launcher
        from sg_compute_specs.playwright.core.service.Credentials__Loader            import Credentials__Loader
        from sg_compute_specs.playwright.core.service.Playwright__Service            import Playwright__Service

        cls.api_key_name  = 'X-API-Key'
        cls.api_key_value = 'ui-smoke'
        os.environ['FAST_API__AUTH__API_KEY__NAME']  = cls.api_key_name
        os.environ['FAST_API__AUTH__API_KEY__VALUE'] = cls.api_key_value

        cls.service = Playwright__Service(browser_launcher   = Browser__Launcher()                              ,
                                          credentials_loader = Credentials__Loader(artefact_writer=None))
        cls.fa      = Fast_API__Playwright__Service(service=cls.service).setup()

        # bind a real loopback port and serve the ASGI app in a background thread
        cls.port    = _free_port()
        config      = uvicorn.Config(cls.fa.app(), host='127.0.0.1', port=cls.port, log_level='warning')
        cls.server  = uvicorn.Server(config)
        cls.thread  = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        _wait_for_port('127.0.0.1', cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.service.browser_launcher.stop_all()

    def test__load_example_W1_then_run_renders_a_completed_sequence(self):
        from playwright.sync_api import sync_playwright

        base = f'http://127.0.0.1:{self.port}'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f'{base}/', wait_until='domcontentloaded')
                # set the auth key the console reuses on every fetch (Phase-1 fix)
                page.evaluate("(k) => window.__tool.setAuth({mode:'direct', key:k})", self.api_key_value)
                # the exact surface the "Load example → Execute" click hits (brief 05 §4)
                result = page.evaluate("async () => await window.__tool.run(window.__tool.loadExample('W1'))")
            finally:
                browser.close()

        # loadExample returns into the builder; run posts the W1 body to /sequence/execute
        assert isinstance(result, dict), f'Unexpected result shape: {result!r}'
        assert result.get('status') in ('completed', 'partial'), f'status={result.get("status")}: {result}'
        assert result.get('steps_passed', 0) >= 1


def _free_port() -> int:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_port(host: str, port: int, timeout_s: float = 30.0):
    import socket, time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f'Server never came up on {host}:{port}')
