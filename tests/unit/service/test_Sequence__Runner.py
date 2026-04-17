# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sequence__Runner (Layer-3 multi-step execution)
#
# Drives Sequence__Runner through a fully wired Playwright__Service. Real
# Chromium is NOT launched — Browser__Launcher is swapped for a fake that
# returns opaque _FakeBrowser / _FakeContext / _FakePage stand-ins. The same
# Step__Executor that powers Action__Runner executes against the fakes, so
# these tests exercise the real step-dispatch glue end-to-end.
#
# Coverage:
#   • ad-hoc session (no session_id in request) — browser_launcher.launch runs,
#     Sequence__Runner owns + closes the session via close_session_after=True
#   • explicit session_id — sequence reuses the caller's session, returns live
#     session_info from Session__Manager
#   • halt_on_error=True  → failure halts, remaining steps marked SKIPPED,
#     sequence status = FAILED
#   • halt_on_error=False → failure does NOT halt, sequence status = PARTIAL
#   • all steps passed → status = COMPLETED, counters match
#   • 404 when caller supplies a session_id that doesn't exist
#   • 422 when no session_id AND no browser_config
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pytest
from unittest                                                                               import TestCase

from fastapi                                                                                import HTTPException

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                   import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                   import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                       import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Status                        import Enum__Session__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                           import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config                 import Schema__Sequence__Config
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request                import Schema__Sequence__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request          import Schema__Session__Create__Request
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


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
    def new_context(self):
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
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,     # Fresh-per-call contract — wrap the fake in the Schema__Browser__Launch__Result shape real launcher now returns
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


def _open_session_via_service(service) -> str:                                       # Used by tests that reuse an existing session
    request  = Schema__Session__Create__Request(browser_config = Schema__Browser__Config(),
                                                capture_config = Schema__Capture__Config())
    response = service.session_create(request)
    return response.session_info.session_id


def _sequence_request_ad_hoc(steps, halt_on_error=True, close_session_after=True):
    return Schema__Sequence__Request(browser_config      = Schema__Browser__Config()                         ,
                                      capture_config      = Schema__Capture__Config()                         ,
                                      sequence_config     = Schema__Sequence__Config(halt_on_error=halt_on_error),
                                      steps               = steps                                             ,
                                      close_session_after = close_session_after                               )


def _sequence_request_existing(session_id, steps, halt_on_error=True, close_session_after=False):
    return Schema__Sequence__Request(session_id          = session_id                                         ,
                                      capture_config      = Schema__Capture__Config()                         ,
                                      sequence_config     = Schema__Sequence__Config(halt_on_error=halt_on_error),
                                      steps               = steps                                             ,
                                      close_session_after = close_session_after                               )


class test_execute__ad_hoc_session(TestCase):

    def test__all_passed_completes_and_tears_down(self):
        _FakePage.fail_on_url = None                                                  # Reset any prior-test state
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            steps = [{'action': 'navigate', 'url': 'http://one.test/'  },
                     {'action': 'navigate', 'url': 'http://two.test/'  },
                     {'action': 'click'   , 'selector': 'button.submit'}]
            response = service.execute_sequence(_sequence_request_ad_hoc(steps=steps))

        assert launcher.launched          == 1
        assert len(launcher.stopped)      == 1                                        # close_session_after=True -> real teardown
        assert response.status            == Enum__Sequence__Status.COMPLETED
        assert int(response.steps_total)  == 3
        assert int(response.steps_passed) == 3
        assert int(response.steps_failed) == 0
        assert int(response.steps_skipped)== 0
        assert response.session_info.status == Enum__Session__Status.CLOSED

    def test__missing_browser_config_without_session_id_raises_422(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _ = _build_service()
            request    = Schema__Sequence__Request(capture_config      = Schema__Capture__Config()    ,
                                                    sequence_config     = Schema__Sequence__Config()   ,
                                                    steps               = [{'action': 'navigate', 'url': 'http://x.test/'}],
                                                    close_session_after = False                        )
            with pytest.raises(HTTPException) as exc:
                service.execute_sequence(request)
        assert exc.value.status_code == 422


class test_execute__existing_session(TestCase):

    def test__reuses_session_and_skips_teardown(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            session_id        = _open_session_via_service(service)                    # Launcher usage = 1 after this
            before_launched   = launcher.launched
            steps = [{'action': 'navigate', 'url': 'http://reuse.test/'},
                     {'action': 'click'   , 'selector': '#ok'          }]
            response = service.execute_sequence(_sequence_request_existing(session_id=session_id, steps=steps))

        assert launcher.launched        == before_launched                            # No extra browser launch — reused the existing session
        assert launcher.stopped         == []                                         # close_session_after=False
        assert response.status          == Enum__Sequence__Status.COMPLETED
        assert int(response.steps_total) == 2
        assert response.session_info.session_id == session_id
        assert response.session_info.status     == Enum__Session__Status.ACTIVE
        assert int(response.session_info.total_actions) == 2                          # Session__Manager.record_action bumped counters

    def test__unknown_session_id_raises_404(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _ = _build_service()
            request    = _sequence_request_existing(session_id='no-such-session',
                                                     steps=[{'action': 'navigate', 'url': 'http://x.test/'}])
            with pytest.raises(HTTPException) as exc:
                service.execute_sequence(request)
        assert exc.value.status_code == 404


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
                response = service.execute_sequence(_sequence_request_ad_hoc(steps=steps, halt_on_error=True))
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
                response = service.execute_sequence(_sequence_request_ad_hoc(steps=steps, halt_on_error=False))
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
            response   = service.execute_sequence(_sequence_request_ad_hoc(steps=steps))

        assert str(response.sequence_id) != ''
        assert str(response.trace_id   ) != ''
        assert int(response.steps_total) == 1


class test_execute__timings(TestCase):                                              # Every response carries the same per-phase breakdown shown to /quick/html callers

    def test__ad_hoc_sequence_populates_all_timing_fields(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _ = _build_service()
            steps      = [{'action': 'navigate', 'url': 'http://t.test/'}]
            response   = service.execute_sequence(_sequence_request_ad_hoc(steps=steps))

        timings = response.timings
        assert timings is not None
        assert int(timings.total_ms) >= 0                                           # Fakes report zero boot cost; total is the only non-trivial wall clock here
        for field in ('playwright_start_ms', 'browser_launch_ms', 'steps_ms', 'browser_close_ms', 'total_ms'):
            assert hasattr(timings, field)                                          # Contract surface for /quick/html JSON + /quick/screenshot response headers

    def test__reused_session_reports_zero_boot_timings(self):                       # Pre-existing session → no new launch → boot timings are 0
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, _  = _build_service()
            session_id  = _open_session_via_service(service)
            steps       = [{'action': 'navigate', 'url': 'http://reuse.test/'}]
            response    = service.execute_sequence(_sequence_request_existing(session_id=session_id, steps=steps))

        assert int(response.timings.playwright_start_ms) == 0
        assert int(response.timings.browser_launch_ms  ) == 0                       # Reusing the session means no fresh Chromium boot — surfaced as zeros


class test_execute__clean_state_between_requests(TestCase):                         # 100%-clean-state contract: every ad-hoc request spawns its own launch and tears it down — no handle leak

    def test__20_sequential_ad_hoc_requests_leave_launcher_registry_empty(self):
        _FakePage.fail_on_url = None
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service, launcher = _build_service()
            for _ in range(20):
                steps    = [{'action': 'navigate', 'url': 'http://loop.test/'}]
                response = service.execute_sequence(_sequence_request_ad_hoc(steps=steps))
                assert response.status == Enum__Sequence__Status.COMPLETED

        assert launcher.launched    == 20                                           # Every call got a fresh launch — proves no cross-request browser reuse
        assert len(launcher.stopped) == 20                                          # And every launch was torn down — proves no leak path

    def test__teardown_runs_even_when_step_raises(self):                            # try/finally contract — step failures must not strand a browser in the registry
        _FakePage.fail_on_url = 'http://boom.test/'
        try:
            with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
                service, launcher = _build_service()
                steps    = [{'action': 'navigate', 'url': 'http://boom.test/'}]
                response = service.execute_sequence(_sequence_request_ad_hoc(steps=steps))
        finally:
            _FakePage.fail_on_url = None

        assert response.status == Enum__Sequence__Status.FAILED                     # halt_on_error=True (default) → FAILED
        assert len(launcher.stopped) == 1                                           # Teardown still ran despite the step failure
