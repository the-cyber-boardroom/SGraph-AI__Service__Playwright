# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sequence__Runner (v0.1.24 — stateless Layer-3 execution)
#
# Drives Sequence__Runner through a fully wired Playwright__Service. Real
# Chromium is NOT launched — Browser__Launcher is swapped for a fake that
# returns opaque _FakeBrowser / _FakeContext / _FakePage stand-ins.
#
# Coverage (stateless contract):
#   • Every call launches + tears down a fresh Chromium (no cross-request reuse)
#   • halt_on_error=True  → failure halts, remaining steps marked SKIPPED,
#     sequence status = FAILED
#   • halt_on_error=False → failure does NOT halt, sequence status = PARTIAL
#   • All steps passed → status = COMPLETED, counters match
#   • Timings block populated on every response (JSON-friendly)
#   • 20 sequential ad-hoc requests all launch + teardown cleanly
#   • Step exception still teardown-safe (try/finally)
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                   import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Auth__Basic                import Schema__Proxy__Auth__Basic
from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Config                     import Schema__Proxy__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                   import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                          import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                       import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                           import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                  import Session_Id
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config                 import Schema__Sequence__Config
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request                import Schema__Sequence__Request
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service
from sgraph_ai_service_playwright.service.Proxy__Auth__Binder                               import Proxy__Auth__Binder


ENV_KEYS = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
            ENV_VAR__CI                    ,
            ENV_VAR__CLAUDE_SESSION        ,
            ENV_VAR__DEPLOYMENT_TARGET     ,
            ENV_VAR__SG_SEND_BASE_URL      ]


class _EnvScrub:
    def __init__(self, **overrides):
        self.overrides = dict(overrides)
        self.snapshot  = {}
    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


# ─── Fakes (no real Chromium, no real vault) ─────────────────────────────────

class _FakePage:                                                                     # Records Step__Executor calls; page.goto supports a fail-on-url toggle
    fail_on_url = None                                                                # Class-level: 'http://boom.test/' → .goto raises for that URL
    def __init__(self):
        self.goto_calls  = []
        self.click_calls = []
        self.url         = 'http://example.com/current'
    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append(url)
        if _FakePage.fail_on_url is not None and url == _FakePage.fail_on_url:
            raise RuntimeError(f'fake nav failure for {url}')
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None):
        self.click_calls.append(selector)


class _FakeContext:
    def __init__(self):
        self.pages = []
    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page
    def storage_state(self): return {'cookies': [], 'origins': []}
    def add_cookies(self, cookies): pass
    def set_extra_http_headers(self, headers): pass


class _FakeBrowser:
    def __init__(self):
        self._contexts = []
    @property                                                                                # Mirror real Playwright sync API — `contexts` is a property, not a method
    def contexts(self):
        return self._contexts
    def new_context(self, **kwargs):
        context = _FakeContext()
        self._contexts.append(context)
        return context
    def close(self): pass


class _FakePlaywright:                                                                           # sync_playwright() stand-in; only needs a stop() no-op
    def stop(self): pass


class _FakeLauncher(Browser__Launcher):
    def __init__(self):
        super().__init__()
        self.launched = 0
        self.stopped  = []
    def launch(self, browser_config):
        self.launched += 1
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,     # Fresh-per-call contract — wrap the fake in the Schema__Browser__Launch__Result shape real launcher returns
                                                playwright          = _FakePlaywright(),
                                                playwright_start_ms = 0                ,
                                                browser_launch_ms   = 0                )
    def stop(self, session_id):
        self.stopped.append(session_id)
        return 0                                                                              # Sequence__Runner converts this to Safe_UInt__Milliseconds for timings.browser_close_ms


class _InMemoryArtefactWriter(Artefact__Writer):
    def read_from_vault(self, vault_ref): return None
    def write_to_vault (self, vault_ref, data): pass


def _build_service():
    launcher = _FakeLauncher()
    writer   = _InMemoryArtefactWriter()
    service  = Playwright__Service(browser_launcher   = launcher                                  ,
                                   credentials_loader = Credentials__Loader(artefact_writer=writer))
    return service.setup(), launcher


def _sequence_request(steps, halt_on_error=True, browser_config=None):
    return Schema__Sequence__Request(browser_config  = browser_config or Schema__Browser__Config()              ,
                                      capture_config  = Schema__Capture__Config()                                ,
                                      sequence_config = Schema__Sequence__Config(halt_on_error=halt_on_error)    ,
                                      steps           = steps                                                    )


class test_execute__stateless(TestCase):

    def test__all_passed_completes_and_tears_down(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            steps = [{'action': 'navigate', 'url': 'http://one.test/'  },
                     {'action': 'navigate', 'url': 'http://two.test/'  },
                     {'action': 'click'   , 'selector': 'button.submit'}]
            response = service.execute_sequence(_sequence_request(steps=steps))

        assert launcher.launched          == 1
        assert len(launcher.stopped)      == 1                                        # stateless — every call tears the launch down
        assert response.status            == Enum__Sequence__Status.COMPLETED
        assert int(response.steps_total)  == 3
        assert int(response.steps_passed) == 3
        assert int(response.steps_failed) == 0
        assert int(response.steps_skipped)== 0

    def test__no_browser_config_uses_launcher_defaults(self):                        # browser_config is optional on stateless surface
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            request  = Schema__Sequence__Request(capture_config  = Schema__Capture__Config() ,
                                                  sequence_config = Schema__Sequence__Config(),
                                                  steps           = [{'action': 'navigate', 'url': 'http://x.test/'}])
            response = service.execute_sequence(request)

        assert response.status       == Enum__Sequence__Status.COMPLETED
        assert launcher.launched     == 1
        assert len(launcher.stopped) == 1


class test_execute__halt_on_error(TestCase):

    def test__failure_halts_and_marks_remainder_skipped(self):
        _FakePage.fail_on_url = 'http://boom.test/'
        try:
            with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
                service, _ = _build_service()
                steps = [{'action': 'navigate', 'url': 'http://ok.test/'  },
                         {'action': 'navigate', 'url': 'http://boom.test/'},                 # Second step fails
                         {'action': 'click'   , 'selector': 'button'      },
                         {'action': 'navigate', 'url': 'http://after.test/'}]
                response = service.execute_sequence(_sequence_request(steps=steps, halt_on_error=True))
        finally:
            _FakePage.fail_on_url = None

        assert response.status             == Enum__Sequence__Status.FAILED
        assert int(response.steps_total)   == 4
        assert int(response.steps_passed)  == 1
        assert int(response.steps_failed)  == 1
        assert int(response.steps_skipped) == 2
        skipped_indices = [int(r.step_index) for r in response.step_results if r.status == Enum__Step__Status.SKIPPED]
        assert skipped_indices == [2, 3]

    def test__no_halt_runs_all_and_reports_partial(self):
        _FakePage.fail_on_url = 'http://boom.test/'
        try:
            with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
                service, _ = _build_service()
                steps = [{'action': 'navigate', 'url': 'http://boom.test/'},                 # Failure — but halt_on_error=False
                         {'action': 'navigate', 'url': 'http://after.test/'},
                         {'action': 'click'   , 'selector': 'button'       }]
                response = service.execute_sequence(_sequence_request(steps=steps, halt_on_error=False))
        finally:
            _FakePage.fail_on_url = None

        assert response.status             == Enum__Sequence__Status.PARTIAL
        assert int(response.steps_failed)  == 1
        assert int(response.steps_passed)  == 2
        assert int(response.steps_skipped) == 0


class test_execute__counters_and_trace(TestCase):

    def test__auto_sequence_id_and_trace_id_present(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _ = _build_service()
            steps      = [{'action': 'navigate', 'url': 'http://trace.test/'}]
            response   = service.execute_sequence(_sequence_request(steps=steps))

        assert str(response.sequence_id) != ''
        assert str(response.trace_id   ) != ''
        assert int(response.steps_total) == 1


class test_execute__timings(TestCase):                                              # Every response carries the same per-phase breakdown used by /browser/* JSON

    def test__populates_all_timing_fields(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _ = _build_service()
            steps      = [{'action': 'navigate', 'url': 'http://t.test/'}]
            response   = service.execute_sequence(_sequence_request(steps=steps))

        timings = response.timings
        assert timings is not None
        assert int(timings.total_ms) >= 0                                           # Fakes report zero boot cost; total is the only non-trivial wall clock here
        for field in ('playwright_start_ms', 'browser_launch_ms', 'steps_ms', 'browser_close_ms', 'total_ms'):
            assert hasattr(timings, field)                                          # Contract surface for /browser/* JSON + /browser/screenshot response headers


class test_execute__clean_state_between_requests(TestCase):                         # 100%-clean-state contract: every request spawns its own launch and tears it down

    def test__20_sequential_requests_leave_launcher_registry_empty(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            for _ in range(20):
                steps    = [{'action': 'navigate', 'url': 'http://loop.test/'}]
                response = service.execute_sequence(_sequence_request(steps=steps))
                assert response.status == Enum__Sequence__Status.COMPLETED

        assert launcher.launched    == 20                                           # Every call got a fresh launch — proves no cross-request browser reuse
        assert len(launcher.stopped) == 20                                          # And every launch was torn down — proves no leak path

    def test__teardown_runs_even_when_step_raises(self):                            # try/finally contract — step failures must not strand a browser in the registry
        _FakePage.fail_on_url = 'http://boom.test/'
        try:
            with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
                service, launcher = _build_service()
                steps    = [{'action': 'navigate', 'url': 'http://boom.test/'}]
                response = service.execute_sequence(_sequence_request(steps=steps))
        finally:
            _FakePage.fail_on_url = None

        assert response.status       == Enum__Sequence__Status.FAILED               # halt_on_error=True (default) → FAILED
        assert len(launcher.stopped) == 1                                           # Teardown still ran despite the step failure


class _RecordingBinder(Proxy__Auth__Binder):                                         # Subclass so Type_Safe allows assignment back onto Sequence__Runner.proxy_auth_binder
    calls : list                                                                     # List[(context, page, auth)]
    def bind(self, context, page, auth):
        self.calls.append((context, page, auth))


class test_get_or_create_page_cdp_binder_gate(TestCase):                            # The CDP Fetch binder is Chromium-only — must be skipped on Firefox/WebKit (they accept proxy creds natively at launch, and don't expose CDP anyway)

    def _run(self, browser_name):                                                   # Shared setup: register a launch result with browser_name + proxy.auth, then call get_or_create_page with a recording binder
        service, launcher = _build_service()
        runner  = service.sequence_runner
        binder  = _RecordingBinder()
        runner.proxy_auth_binder = binder                                            # Swap in the recorder subclass; Type_Safe accepts it because it extends Proxy__Auth__Binder

        session_id = Session_Id()
        auth       = Schema__Proxy__Auth__Basic(username='u', password='p')
        proxy      = Schema__Proxy__Config(server='http://proxy:3128', auth=auth)
        launcher.browsers[session_id] = Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,
                                                                        playwright          = _FakePlaywright(),
                                                                        playwright_start_ms = 0                ,
                                                                        browser_launch_ms   = 0                ,
                                                                        browser_name        = browser_name     ,
                                                                        proxy               = proxy            )
        browser = launcher.browsers[session_id].browser
        runner.get_or_create_page(browser, session_id)                               # Triggers the bind-or-skip decision
        return binder

    def test__binder_called_on_chromium(self):                                      # Baseline: Chromium still needs CDP Fetch for proxy auth
        binder = self._run(Enum__Browser__Name.CHROMIUM)
        assert len(binder.calls) == 1

    def test__binder_skipped_on_firefox(self):                                      # Firefox accepts creds natively at launch — CDP is unavailable / pointless
        binder = self._run(Enum__Browser__Name.FIREFOX)
        assert binder.calls == []

    def test__binder_skipped_on_webkit(self):                                       # WebKit accepts creds natively at launch — CDP is unavailable / pointless
        binder = self._run(Enum__Browser__Name.WEBKIT)
        assert binder.calls == []
