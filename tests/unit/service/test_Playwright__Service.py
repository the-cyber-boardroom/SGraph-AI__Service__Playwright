# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Playwright__Service (v0.1.24 — stateless orchestrator)
#
# Scope:
#   • Health surface (get_service_info / get_capabilities / get_health)
#   • Composition (Type_Safe auto-instantiation of sub-services)
#   • setup() idempotence
#   • One-shot browser_* methods — each launches fresh Chromium via
#     Browser__Launcher, runs a tiny sequence, tears down, returns the
#     Schema__Browser__One_Shot__Response (or Schema__Browser__Screenshot__Result)
#   • execute_sequence delegates to Sequence__Runner
#
# Real Chromium is NOT launched — a _FakeLauncher returns opaque _FakeBrowser /
# _FakeContext / _FakePage stand-ins.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                                 import Any
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEFAULT_PROXY_URL     ,
                                                                                                    ENV_VAR__DEFAULT_S3_BUCKET     ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Click__Request            import Schema__Browser__Click__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Fill__Request             import Schema__Browser__Fill__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Get_Content__Request      import Schema__Browser__Get_Content__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Get_Url__Request          import Schema__Browser__Get_Url__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Navigate__Request         import Schema__Browser__Navigate__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__One_Shot__Response        import Schema__Browser__One_Shot__Response
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Screenshot__Request       import Schema__Browser__Screenshot__Request
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Screenshot__Result        import Schema__Browser__Screenshot__Result
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target                    import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.service.Schema__Health                            import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities             import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                     import Schema__Service__Info
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                              import Capability__Detector
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service
from sgraph_ai_service_playwright.service.Proxy__Auth__Binder                               import Proxy__Auth__Binder
from sgraph_ai_service_playwright.service.Sequence__Runner                                  import Sequence__Runner


ENV_KEYS = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
            ENV_VAR__CI                    ,
            ENV_VAR__CLAUDE_SESSION        ,
            ENV_VAR__DEFAULT_PROXY_URL     ,
            ENV_VAR__DEFAULT_S3_BUCKET     ,
            ENV_VAR__DEPLOYMENT_TARGET     ,
            ENV_VAR__SG_SEND_BASE_URL      ]


class _EnvScrub:                                                                    # Keep tests hermetic — sandbox's env could pollute target detection / connectivity check
    def __init__(self, **overrides):
        self.overrides = overrides
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

class _FakePage:
    def __init__(self):
        self.url = 'http://example.com/current'
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None): pass
    def fill (self, selector, value, timeout=None): pass
    def screenshot(self, full_page=False, timeout=None):
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16
    def content(self):
        return '<html><body>full-page-html</body></html>'
    def locator(self, selector):
        return _FakeLocator(selector)


class _FakeLocator:
    def __init__(self, selector):
        self.selector = selector
    def press_sequentially(self, value, timeout=None): pass
    def inner_text   (self, timeout=None): return 'locator-text'
    def inner_html   (self, timeout=None): return '<span>locator-html</span>'
    def screenshot   (self, timeout=None): return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16


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
    @property
    def contexts(self):
        return self._contexts
    def new_context(self, **kwargs):
        context = _FakeContext()
        self._contexts.append(context)
        return context
    def close(self): pass


class _FakePlaywright:
    def stop(self): pass


class _FakeLauncher(Browser__Launcher):
    last_config : Any  = None
    launched    : int  = 0
    stopped     : list

    def launch(self, browser_config):
        self.last_config = browser_config
        self.launched   += 1
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,
                                                playwright          = _FakePlaywright(),
                                                playwright_start_ms = 0                ,
                                                browser_launch_ms   = 0                )

    def stop(self, session_id):
        self.stopped.append(session_id)
        return 0


class _InMemoryArtefactWriter(Artefact__Writer):
    def read_from_vault(self, vault_ref): return None
    def write_to_vault (self, vault_ref, data): pass


def _build_service():
    writer   = _InMemoryArtefactWriter()
    launcher = _FakeLauncher()
    return Playwright__Service(browser_launcher   = launcher,
                               credentials_loader = Credentials__Loader(artefact_writer=writer)).setup()


# ─── Setup / health ──────────────────────────────────────────────────────────

class test_setup(TestCase):

    def test__primes_capability_detector(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = Playwright__Service()
            assert service.capability_detector.detected_target is None              # Not yet detected
            service.setup()
            assert service.capability_detector.detected_target == Enum__Deployment__Target.LAMBDA

    def test__is_idempotent(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'ci'}):
            service = Playwright__Service().setup()
            caps_1  = service.capability_detector.detected_capabilities
            service.setup()                                                         # Second call — should not re-detect
            caps_2  = service.capability_detector.detected_capabilities
            assert caps_1 is caps_2                                                 # Same object — no re-detection

    def test__shares_deps_into_sequence_runner(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = Playwright__Service().setup()
        assert service.sequence_runner.capability_detector is service.capability_detector
        assert service.sequence_runner.browser_launcher    is service.browser_launcher
        assert service.sequence_runner.credentials_loader  is service.credentials_loader
        assert service.sequence_runner.request_validator   is service.request_validator
        assert service.sequence_runner.proxy_auth_binder   is service.proxy_auth_binder


class test_get_service_info(TestCase):

    def test__returns_schema_service_info(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            info = Playwright__Service().get_service_info()
        assert isinstance(info, Schema__Service__Info)
        assert str(info.service_name) == 'sg-playwright'
        assert info.deployment_target == Enum__Deployment__Target.LAPTOP


class test_get_capabilities(TestCase):

    def test__returns_schema_service_capabilities(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            caps = Playwright__Service().get_capabilities()
        assert isinstance(caps, Schema__Service__Capabilities)
        assert caps.max_session_lifetime_ms == 900_000                              # Lambda profile

    def test__laptop_profile_has_local_file_sink(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            caps = Playwright__Service().get_capabilities()
        from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink import Enum__Artefact__Sink
        assert Enum__Artefact__Sink.LOCAL_FILE in caps.supported_sinks


class test_get_health(TestCase):

    def test__aggregates_two_checks(self):                                          # Session_Manager is gone — just browser_launcher + connectivity
        with _EnvScrub():
            service = Playwright__Service().setup()
            health  = service.get_health()
        assert isinstance(health, Schema__Health)
        names = [str(c.check_name) for c in health.checks]
        assert names == ['browser_launcher', 'connectivity']

    def test__healthy_false_when_vault_unreachable(self):
        with _EnvScrub():                                                           # Connectivity check returns healthy=False
            health = Playwright__Service().get_health()
        assert health.healthy is False                                              # all() over checks; connectivity brings it down

    def test__healthy_true_when_vault_url_configured(self):
        with _EnvScrub(**{ENV_VAR__SG_SEND_BASE_URL: 'https://vault.example.com'}):
            health = Playwright__Service().get_health()
        assert health.healthy is True


class test_composition(TestCase):

    def test__uses_real_sub_services_by_default(self):                              # Type_Safe auto-instantiates the declared types
        service = Playwright__Service()
        assert isinstance(service.capability_detector, Capability__Detector)
        assert isinstance(service.browser_launcher   , Browser__Launcher   )
        assert isinstance(service.credentials_loader , Credentials__Loader )
        assert isinstance(service.proxy_auth_binder  , Proxy__Auth__Binder )
        assert isinstance(service.sequence_runner    , Sequence__Runner    )


# ─── One-shot browser surface ────────────────────────────────────────────────

class test_browser_navigate(TestCase):

    def test__launches_fresh_browser_and_returns_one_shot_response(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Navigate__Request(url='http://one-shot.test/')
            response = service.browser_navigate(request)

        assert isinstance(response, Schema__Browser__One_Shot__Response)
        assert str(response.url)       == 'http://one-shot.test/'
        assert service.browser_launcher.launched == 1
        assert len(service.browser_launcher.stopped) == 1                           # Teardown ran


class test_browser_click(TestCase):

    def test__navigates_then_clicks_and_returns_one_shot_response(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Click__Request(url='http://click.test/', selector='button.go')
            response = service.browser_click(request)

        assert isinstance(response, Schema__Browser__One_Shot__Response)
        assert service.browser_launcher.launched     == 1
        assert len(service.browser_launcher.stopped) == 1


class test_browser_fill(TestCase):

    def test__navigates_then_fills_and_returns_one_shot_response(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Fill__Request(url='http://fill.test/', selector='input#q', value='hello')
            response = service.browser_fill(request)

        assert isinstance(response, Schema__Browser__One_Shot__Response)


class test_browser_get_content(TestCase):

    def test__returns_page_html_in_response_body(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Get_Content__Request(url='http://html.test/')
            response = service.browser_get_content(request)

        assert isinstance(response, Schema__Browser__One_Shot__Response)
        assert response.html is not None
        assert 'full-page-html' in str(response.html)                               # _FakePage.content() returns this


class test_browser_get_url(TestCase):

    def test__returns_current_page_url(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Get_Url__Request(url='http://redirect.test/')
            response = service.browser_get_url(request)

        assert isinstance(response, Schema__Browser__One_Shot__Response)
        assert str(response.final_url) == 'http://redirect.test/'                   # _FakePage.goto sets page.url — get_url reflects it


class test_browser_screenshot(TestCase):

    def test__returns_png_bytes_and_timings(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Browser__Screenshot__Request(url='http://shot.test/')
            result   = service.browser_screenshot(request)

        assert isinstance(result, Schema__Browser__Screenshot__Result)
        assert result.png_bytes[:4] == b'\x89PNG'                                   # Real PNG magic
        assert result.timings is not None
        assert service.browser_launcher.launched     == 1
        assert len(service.browser_launcher.stopped) == 1


# ─── Sequence surface ────────────────────────────────────────────────────────

class test_execute_sequence(TestCase):

    def test__delegates_to_sequence_runner(self):
        from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Request import Schema__Sequence__Request
        from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config    import Schema__Capture__Config
        from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config  import Schema__Sequence__Config
        from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status       import Enum__Sequence__Status

        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = Schema__Sequence__Request(capture_config  = Schema__Capture__Config() ,
                                                  sequence_config = Schema__Sequence__Config(),
                                                  steps           = [{'action': 'navigate', 'url': 'http://seq.test/'}])
            response = service.execute_sequence(request)

        assert response.status == Enum__Sequence__Status.COMPLETED


class test_generate_trace_id(TestCase):

    def test__returns_8_char_hex(self):
        trace_id = Playwright__Service().generate_trace_id()
        assert len(trace_id) == 8
        assert all(c in '0123456789abcdef' for c in trace_id)

    def test__values_differ_across_calls(self):
        service = Playwright__Service()
        assert service.generate_trace_id() != service.generate_trace_id()
