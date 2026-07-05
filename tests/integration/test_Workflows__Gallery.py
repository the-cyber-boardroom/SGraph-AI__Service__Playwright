# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests — Gallery workflows W1-W9 against REAL Chromium
#
# v0.2.64 dev pack — brief 06 §3 (workflow → assertion map) + §4 (UI execute-path
# smoke). Each gallery workflow becomes ONE assertion on the CONTRACT
# (schema / status / persisted artefact), never on implementation details
# (CLAUDE.md testing rule #2). W7 deliberately asserts the allowlist *failure* as
# a contract (a good-failure test).
#
# Composition: the repo's real in-memory pattern — Playwright__Service with the
# REAL Browser__Launcher injected, served through a FastAPI TestClient. NOT the
# non-existent register_playwright_service__in_memory() (brief 06 flags that name
# discrepancy; _build_fast_api() is the truth — mirrors
# tests/unit/fast_api/routes/test_Routes__Sequence.py:117-121, swapping the fake
# launcher for the real one).
#
# Gating: needs real Chromium AND outbound network (the W bodies hit example.com /
# sgraph.ai). Skipped cleanly when SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE is unset and
# Playwright cannot resolve a default Chromium (same gate as
# tests/integration/service/test_Browser__Launcher.py). No mocks, no patches.
#
# These run in the integration tier, not per-PR — they are the most expensive
# tests in the pack. The body-level regression guard that runs WITHOUT a browser
# lives in tests/unit/fast_api/routes/test_Workflows__Gallery__Bodies.py.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

import pytest

from sg_compute_specs.playwright.core.consts.env_vars                                       import ENV_VAR__CHROMIUM_EXECUTABLE
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service                import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.service.Browser__Launcher                             import Browser__Launcher
from sg_compute_specs.playwright.core.service.Credentials__Loader                           import Credentials__Loader
from sg_compute_specs.playwright.core.service.Playwright__Service                           import Playwright__Service


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'integration-gallery'
AUTH_HEADERS  = {API_KEY_NAME: API_KEY_VALUE}

ENV_VAR__API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'


def _chromium_available() -> bool:
    exe = os.environ.get(ENV_VAR__CHROMIUM_EXECUTABLE)                                       # Fast path: explicit override
    if exe and os.path.isfile(exe):
        return True
    try:                                                                                     # Fallback: can Playwright resolve a default Chromium?
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.exists(path)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_available(),
                                reason=f'No Chromium available. Set {ENV_VAR__CHROMIUM_EXECUTABLE} or run `playwright install chromium`.')


def _build_fast_api():                                                                       # real launcher, in-memory composition (brief 06 §2 pattern)
    os.environ[ENV_VAR__API_KEY_NAME]  = API_KEY_NAME
    os.environ[ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
    service = Playwright__Service(browser_launcher   = Browser__Launcher()                                 ,
                                  credentials_loader = Credentials__Loader(artefact_writer=None))
    fa      = Fast_API__Playwright__Service(service=service).setup()
    return fa, fa.client()


# ── Gallery bodies (brief 02 / the console's GALLERY) — kept identical to W1-W9 ──
# W2 (login-redirect glob) and W9 (stateful session) are intentionally NOT mapped
# here: W2 hits Safe_Str__Url__Permissive rejection (D7, see the body-level test)
# and W9 needs supports_persistent — both covered by tests/integration_live/.

W1 = {'capture_config': {'screenshot': {'enabled': True, 'sink': 'inline'}},
      'sequence_config': {},
      'steps': [{'action': 'navigate', 'url': 'https://example.com', 'wait_until': 'domcontentloaded'},
                {'action': 'screenshot', 'full_page': False},
                {'action': 'screenshot', 'full_page': True}]}

W3 = {'navigate': {'url': 'https://example.com'},
      'settle'  : [{'action': 'wait_for', 'state': 'networkidle'}],
      'diagnostics_on_fail': True,
      'probes'  : {'dom' : {'action': 'get_dom_tree' , 'max_depth': 6, 'include_invisible': False},
                   'a11y': {'action': 'get_a11y_tree', 'interesting_only': True}}}

W4 = {'capture_config': {'pdf': {'enabled': True, 'sink': 'inline'}},
      'sequence_config': {},
      'steps': [{'action': 'navigate', 'url': 'https://example.com', 'wait_until': 'load'},
                {'action': 'get_pdf', 'format': 'A4', 'landscape': False, 'print_background': True}]}

W5 = {'navigate': {'url': 'https://example.com'},
      'settle'  : [],
      'diagnostics_on_fail': True,
      'probes'  : {'console' : {'action': 'get_console_tail', 'lines': 200},
                   'failures': {'action': 'get_network_failures'}}}

W6 = {'capture_config': {'screenshot': {'enabled': True, 'sink': 'inline'}},
      'sequence_config': {},
      'steps': [{'action': 'navigate'    , 'url': 'https://example.com'},
                {'action': 'set_viewport', 'viewport': {'width': 1440, 'height': 900}},
                {'action': 'screenshot'  , 'full_page': True},
                {'action': 'screenshot'  , 'selector': 'h1'}]}

W7 = {'capture_config': {'screenshot': {'enabled': True, 'sink': 'inline'}},
      'sequence_config': {},
      'steps': [{'action': 'navigate'  , 'url': 'https://example.com'},
                {'action': 'evaluate'  , 'expression': "document.querySelectorAll('a').length", 'return_type': 'number'},
                {'action': 'screenshot', 'full_page': True}]}

W8 = {'items': [{'url': 'https://example.com', 'full_page': True},
                {'url': 'https://example.org', 'format'   : 'png'}]}


def _post(client, path, body):
    r = client.post(path, headers=AUTH_HEADERS, json=body)
    assert r.status_code == 200, f'{path} returned {r.status_code}: {r.text[:400]}'
    return r.json()


class test_Workflows__Gallery(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fa, cls.client = _build_fast_api()

    @classmethod
    def tearDownClass(cls):
        cls.fa.service.browser_launcher.stop_all()                                           # release every Chromium process

    # ── W1: form fill + per-step shots → /sequence/execute ──────────────────────
    def test__W1_per_step_screenshots(self):
        rj = _post(self.client, '/sequence/execute', W1)
        assert rj['status'] == 'completed'
        assert rj['steps_passed'] == rj['steps_total']
        shots = [s for s in rj['step_results'] if s.get('action') == 'screenshot']
        assert len(shots) == 2
        for s in shots:
            assert s['artefacts'][0]['inline_b64']                                            # non-empty inline screenshot

    # ── W3: scrape DOM + a11y → /inspect ────────────────────────────────────────
    def test__W3_dom_and_a11y(self):
        rj = _post(self.client, '/inspect', W3)
        pr = rj['probe_results']
        assert isinstance(pr['dom']['dom_tree'], dict)                                        # nested object
        assert isinstance(pr['a11y']['accessibility_tree']['nodes'], list)

    # ── W4: render PDF → /sequence/execute ──────────────────────────────────────
    def test__W4_pdf_artefact(self):
        rj = _post(self.client, '/sequence/execute', W4)
        pdf_step = next(s for s in rj['step_results'] if s.get('action') == 'get_pdf')
        assert pdf_step['artefacts'][0]['artefact_type'] == 'PDF'

    # ── W5: console + network → /inspect ────────────────────────────────────────
    def test__W5_console_and_network(self):
        rj = _post(self.client, '/inspect', W5)
        pr = rj['probe_results']
        assert isinstance(pr['console']['console_log'], list)
        assert isinstance(pr['failures']['network_failures'], list)

    # ── W6: viewport/selector scoped capture → /sequence/execute ────────────────
    def test__W6_scoped_capture(self):
        rj = _post(self.client, '/sequence/execute', W6)
        shots = [s for s in rj['step_results'] if s.get('action') == 'screenshot']
        assert len(shots) == 2
        for s in shots:
            assert s['artefacts'][0]['inline_b64']

    # ── W7: evaluate is allowlist-gated → the documented FAILURE is the contract ─
    def test__W7_evaluate_allowlist_failure(self):                                            # good-failure test (brief 06 §3)
        rj = _post(self.client, '/sequence/execute', W7)
        assert rj['status'] in ('completed', 'partial')
        eval_step = next(s for s in rj['step_results'] if s.get('action') == 'evaluate')
        assert eval_step['status'] == 'failed'
        assert 'allowlist' in (eval_step.get('error_message') or '').lower()

    # ── W8: batch independent screenshots → /screenshot/batch ───────────────────
    def test__W8_batch(self):
        rj = _post(self.client, '/screenshot/batch', W8)
        assert len(rj['screenshots']) == len(W8['items'])
        for s in rj['screenshots']:
            assert s['screenshot_b64']


# ═══════════════════════════════════════════════════════════════════════════════
# S6 — set_cookie → reload → screenshot, against the service's OWN /test-pages/cookies
# fixture. Unlike W1-W8 the browser must reach the fixture over real HTTP, so the
# app is also served on a loopback uvicorn (same pattern as test_Workflows__UI_
# Execute_Smoke). STATELESS contract: the cookie exists only inside that one
# request's fresh browser context — nothing persists between the two tests below.
# ═══════════════════════════════════════════════════════════════════════════════

def _s6_body(base: str) -> dict:                                                             # the gallery S6 body with tpUrl(base) resolved
    cookies_url = f'{base}/test-pages/cookies'
    return {'capture_config' : {'screenshot': {'enabled': True, 'sink': 'inline'}},
            'sequence_config': {},
            'steps': [{'action': 'navigate'  , 'url': cookies_url, 'wait_until': 'domcontentloaded'},
                      {'action': 'screenshot', 'full_page': True},
                      {'action': 'set_cookie', 'name': 'sg_demo', 'value': 'hello-from-sg-playwright', 'url': cookies_url},
                      {'action': 'navigate'  , 'url': cookies_url, 'wait_until': 'domcontentloaded'},
                      {'action': 'screenshot', 'full_page': True}]}


class test_Workflows__Gallery__S6_set_cookie(TestCase):

    @classmethod
    def setUpClass(cls):
        import threading
        import socket
        import time
        import uvicorn

        cls.fa, cls.client = _build_fast_api()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                                # loopback port for the fixture pages the browser fetches
        s.bind(('127.0.0.1', 0)); cls.port = s.getsockname()[1]; s.close()
        config      = uvicorn.Config(cls.fa.app(), host='127.0.0.1', port=cls.port, log_level='warning')
        cls.server  = uvicorn.Server(config)
        cls.thread  = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        deadline = time.time() + 15
        while time.time() < deadline:                                                        # wait for the port to accept connections
            try:
                probe = socket.create_connection(('127.0.0.1', cls.port), timeout=0.5)
                probe.close(); break
            except OSError:
                time.sleep(0.1)
        cls.base = f'http://127.0.0.1:{cls.port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.fa.service.browser_launcher.stop_all()

    def test__S6_second_screenshot_artefact_exists(self):                                    # the brief's contract assertion — both shots land, set_cookie passes
        rj = _post(self.client, '/sequence/execute', _s6_body(self.base))
        assert rj['status'] == 'completed', rj
        assert rj['steps_passed'] == rj['steps_total'] == 5
        set_cookie_step = next(s for s in rj['step_results'] if s.get('action') == 'set_cookie')
        assert set_cookie_step['status'] == 'passed'
        assert 'hello-from-sg-playwright' not in str(set_cookie_step)                        # cookie value is never echoed in the step result
        shots = [s for s in rj['step_results'] if s.get('action') == 'screenshot']
        assert len(shots) == 2
        for s in shots:
            assert s['artefacts'][0]['inline_b64']                                           # both artefacts exist — notably the post-reload one
        assert shots[1]['artefacts'][0]['inline_b64'] != shots[0]['artefacts'][0]['inline_b64']  # the page changed after the cookie landed

    def test__S6_cookie_visible_to_document_cookie_after_reload(self):                       # verb proof — the fixture renders the jar into #cookie-list
        body = _s6_body(self.base)
        body['steps'] += [{'action': 'wait_for', 'selector': '#cookie-sg_demo'},
                          {'action': 'get_text', 'selector': '#cookie-list'}]
        rj = _post(self.client, '/sequence/execute', body)
        assert rj['status'] == 'completed', rj
        text_step = next(s for s in rj['step_results'] if s.get('action') == 'get_text')
        assert 'sg_demo' in text_step['text']
        assert 'hello-from-sg-playwright' in text_step['text']
