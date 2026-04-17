# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests — Step__Executor (real Chromium)
#
# Drives a live Chromium (via Browser__Launcher) through the Phase 2.9 first
# pass: NAVIGATE → GET_URL → GET_CONTENT → SCREENSHOT → CLICK → FILL. Uses a
# tiny in-process HTTP server for the fixture so the tests have no network
# dependency.
#
# Skipped when Chromium isn't resolvable. Same gate as
# tests/integration/service/test_Browser__Launcher.py — set
# SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE or run `playwright install chromium`.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import threading
from http.server                                                                              import BaseHTTPRequestHandler, HTTPServer
from unittest                                                                                 import TestCase

import pytest

from sgraph_ai_service_playwright.consts.env_vars                                             import ENV_VAR__CHROMIUM_EXECUTABLE
from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Sink_Config              import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                     import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                     import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                          import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Content__Format                         import Enum__Content__Format
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                            import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click                           import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Fill                            import Schema__Step__Fill
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Content                     import Schema__Step__Get_Content
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Url                         import Schema__Step__Get_Url
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate                        import Schema__Step__Navigate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Screenshot                      import Schema__Step__Screenshot
from sgraph_ai_service_playwright.service.Artefact__Writer                                    import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                   import Browser__Launcher
from sgraph_ai_service_playwright.service.Step__Executor                                      import Step__Executor


FIXTURE_HTML = b'''<!doctype html>
<html>
  <head><title>sg-playwright fixture</title></head>
  <body>
    <h1 id="heading">hello from sg-playwright</h1>
    <p class="blurb">integration-test fixture</p>
    <button id="btn" onclick="document.getElementById('heading').innerText='clicked'">click me</button>
    <input id="name" name="name"/>
  </body>
</html>'''


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


pytestmark = pytest.mark.skipif(not _chromium_available(),
                                reason=f'No Chromium available. Set {ENV_VAR__CHROMIUM_EXECUTABLE} or run `playwright install chromium`.')


class _Fixture_Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(FIXTURE_HTML)))
        self.end_headers()
        self.wfile.write(FIXTURE_HTML)

    def log_message(self, format, *args):                                           # Silence the default stderr access log
        pass


class _Fixture_Server:

    def __init__(self):
        self.httpd  = HTTPServer(('127.0.0.1', 0), _Fixture_Handler)                # Port 0 → OS assigns free port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address
        return f'http://{host}:{port}/'


def _capture_config_all_inline() -> Schema__Capture__Config:
    cfg = Schema__Capture__Config()
    for field in ('screenshot', 'screenshot_on_fail', 'video', 'pdf', 'har',
                  'trace', 'console_log', 'network_log', 'page_content'):
        setattr(cfg, field, Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE))
    return cfg


class test_execute_against_real_chromium(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = _Fixture_Server()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def setUp(self):
        self.launcher = Browser__Launcher()
        self.browser  = self.launcher.launch(Schema__Browser__Config())             # chromium / LOCAL_SUBPROCESS / headless
        self.context  = self.browser.new_context()
        self.page     = self.context.new_page()
        self.executor = Step__Executor(artefact_writer=Artefact__Writer())
        self.capture  = _capture_config_all_inline()

    def tearDown(self):
        try:
            self.context.close()
            self.browser.close()
        finally:
            self.launcher.stop_all()

    def test__navigate_then_get_url(self):
        navigate = Schema__Step__Navigate(url=self.server.url)
        nav_res  = self.executor.execute(self.page, navigate, step_index=0, capture_config=self.capture)
        assert nav_res.status == Enum__Step__Status.PASSED

        get_url = Schema__Step__Get_Url()
        url_res = self.executor.execute(self.page, get_url, step_index=1, capture_config=self.capture)
        assert url_res.status == Enum__Step__Status.PASSED
        assert str(url_res.url) == self.server.url

    def test__screenshot_captures_png_bytes_inline(self):
        self.executor.execute(self.page, Schema__Step__Navigate(url=self.server.url), 0, self.capture)

        shot    = Schema__Step__Screenshot(full_page=True)
        res     = self.executor.execute(self.page, shot, step_index=1, capture_config=self.capture)
        assert res.status         == Enum__Step__Status.PASSED
        assert len(res.artefacts) == 1
        ref = res.artefacts[0]
        assert ref.inline_b64 is not None and len(ref.inline_b64) > 0               # Non-empty inline payload
        import base64
        png_bytes = base64.b64decode(str(ref.inline_b64))
        assert png_bytes.startswith(b'\x89PNG\r\n\x1a\n')                            # Real PNG magic bytes

    def test__get_content_html_inline_returns_full_page_html(self):
        self.executor.execute(self.page, Schema__Step__Navigate(url=self.server.url), 0, self.capture)

        step = Schema__Step__Get_Content(content_format=Enum__Content__Format.HTML, inline_in_response=True)
        res  = self.executor.execute(self.page, step, step_index=1, capture_config=self.capture)
        assert res.status == Enum__Step__Status.PASSED
        assert 'sg-playwright fixture'       in str(res.content)
        assert 'hello from sg-playwright'    in str(res.content)
        assert str(res.content_type)         == 'text/html'

    def test__get_content_text_with_selector_returns_inner_text(self):
        self.executor.execute(self.page, Schema__Step__Navigate(url=self.server.url), 0, self.capture)

        step = Schema__Step__Get_Content(content_format=Enum__Content__Format.TEXT, selector='#heading', inline_in_response=True)
        res  = self.executor.execute(self.page, step, step_index=1, capture_config=self.capture)
        assert res.status               == Enum__Step__Status.PASSED
        assert str(res.content).strip() == 'hello from sg-playwright'
        assert str(res.content_type)    == 'text/plain'

    def test__click_mutates_page_then_get_content_confirms(self):
        self.executor.execute(self.page, Schema__Step__Navigate(url=self.server.url), 0, self.capture)

        click_res = self.executor.execute(self.page, Schema__Step__Click(selector='#btn'), 1, self.capture)
        assert click_res.status == Enum__Step__Status.PASSED

        text_step = Schema__Step__Get_Content(content_format=Enum__Content__Format.TEXT, selector='#heading', inline_in_response=True)
        text_res  = self.executor.execute(self.page, text_step, 2, self.capture)
        assert str(text_res.content).strip() == 'clicked'                           # onclick handler ran

    def test__fill_types_value_into_input(self):
        self.executor.execute(self.page, Schema__Step__Navigate(url=self.server.url), 0, self.capture)

        fill_res = self.executor.execute(self.page, Schema__Step__Fill(selector='#name', value='integration test', clear_first=True), 1, self.capture)
        assert fill_res.status == Enum__Step__Status.PASSED

        assert self.page.locator('#name').input_value() == 'integration test'

    def test__navigate_to_bad_host_returns_failed_result(self):
        navigate = Schema__Step__Navigate(url='http://127.0.0.1:1/', timeout_ms=2000)
        res      = self.executor.execute(self.page, navigate, step_index=0, capture_config=self.capture)
        assert res.status == Enum__Step__Status.FAILED
        assert res.error_message is not None and len(str(res.error_message)) > 0
