# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Playwright__Service (orchestrator; Phase 2.7 health surface)
#
# Scope: only the /health-surface methods exist at this phase. Verifies
# composition, setup() idempotence, and that get_health aggregates the
# three sub-healthchecks.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                                 import Any
from unittest                                                                               import TestCase

import pytest
from fastapi                                                                                import HTTPException

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEFAULT_PROXY_URL     ,
                                                                                                    ENV_VAR__DEFAULT_S3_BUCKET     ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                        import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                   import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                   import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target                    import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Lifetime                     import Enum__Session__Lifetime
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Status                       import Enum__Session__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id         import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.service.Schema__Health                            import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities             import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                     import Schema__Service__Info
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request          import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Response         import Schema__Session__Create__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials              import Schema__Session__Credentials
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                     import Schema__Session__Info
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Request     import Schema__Session__State__Save__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Response    import Schema__Session__State__Save__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Close__Response          import Schema__Session__Close__Response
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                              import Capability__Detector
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service
from sgraph_ai_service_playwright.service.Session__Manager                                  import Session__Manager


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


class test_get_service_info(TestCase):

    def test__returns_schema_service_info(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            info = Playwright__Service().get_service_info()
        assert isinstance(info, Schema__Service__Info)
        assert str(info.service_name)      == 'sg-playwright'
        assert info.deployment_target      == Enum__Deployment__Target.LAPTOP

    def test__self_heals_if_setup_forgotten(self):                                  # Defensive — callers shouldn't skip setup(), but the service shouldn't crash if they do
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = Playwright__Service()                                         # No explicit setup()
            info    = service.get_service_info()
        assert info.deployment_target == Enum__Deployment__Target.LAMBDA


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

    def test__aggregates_three_checks(self):
        with _EnvScrub():                                                           # No vault base url set -> connectivity check fails
            service = Playwright__Service().setup()
            health  = service.get_health()
        assert isinstance(health, Schema__Health)
        names = [str(c.check_name) for c in health.checks]
        assert names == ['browser_launcher', 'session_manager', 'connectivity']

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
        assert isinstance(service.session_manager    , Session__Manager    )
        assert isinstance(service.browser_launcher   , Browser__Launcher   )
        assert isinstance(service.credentials_loader , Credentials__Loader )


# ─── Session surface (Phase 2.10 Slice A) ─────────────────────────────────────
#
# No real Chromium is launched here — we swap the Browser__Launcher with a
# fake that returns opaque _FakeBrowser objects. The Session__Manager treats
# browsers as `Any`, so the fake is accepted end-to-end. The Artefact__Writer
# is also replaced with an in-memory subclass so save_state doesn't raise
# NotImplementedError and we can inspect what was written.
# ──────────────────────────────────────────────────────────────────────────────

class _FakeContext:                                                                 # Playwright BrowserContext stand-in
    def __init__(self, state=None):
        self.state    = state if state is not None else {'cookies': [], 'origins': []}
        self.cookies_added     = []
        self.headers_set       = None
    def storage_state(self):
        return self.state
    def add_cookies(self, cookies):
        self.cookies_added.extend(cookies)
    def set_extra_http_headers(self, headers):
        self.headers_set = headers


class _FakeBrowser:                                                                 # Playwright Browser stand-in
    def __init__(self, state=None):
        self.context = _FakeContext(state=state)
        self.closed  = False
    @property                                                                       # Real Playwright sync API: `contexts` is a @property
    def contexts(self):
        return [self.context]
    def close(self):
        self.closed = True


class _FakeLauncher(Browser__Launcher):                                             # Subclass Browser__Launcher — satisfies Type_Safe attribute type
    last_config : Any  = None
    stopped     : list
    next_browser: Any  = None

    def launch(self, browser_config):
        self.last_config = browser_config
        if self.next_browser is None:
            self.next_browser = _FakeBrowser()
        return self.next_browser

    def stop(self, session_id):
        self.stopped.append(session_id)

    def start(self):                                                                # Skip sync_playwright.start() — no real runtime
        return self


class _InMemoryArtefactWriter(Artefact__Writer):
    vault_reads  : dict                                                             # key=str(vault_ref.path) -> value returned by read_from_vault
    vault_writes : list                                                             # list of (vault_ref, data)

    def read_from_vault(self, vault_ref):
        return self.vault_reads.get(str(vault_ref.path))

    def write_to_vault(self, vault_ref, data):
        self.vault_writes.append((vault_ref, data))


def _build_service(next_browser=None, vault_reads=None):                            # Compose a service with fakes; safe to call without env scrubbing caller
    writer   = _InMemoryArtefactWriter(vault_reads = (vault_reads or {}))
    launcher = _FakeLauncher()
    if next_browser is not None:
        launcher.next_browser = next_browser
    return Playwright__Service(browser_launcher   = launcher,
                               credentials_loader = Credentials__Loader(artefact_writer=writer))


def _create_request(**overrides) -> Schema__Session__Create__Request:
    defaults = dict(browser_config = Schema__Browser__Config(),
                    capture_config = Schema__Capture__Config())
    defaults.update(overrides)
    return Schema__Session__Create__Request(**defaults)


class test_session_create(TestCase):

    def test__returns_create_response_with_session_info_and_capabilities(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            response = service.session_create(_create_request())
        assert isinstance(response            , Schema__Session__Create__Response)
        assert isinstance(response.session_info, Schema__Session__Info            )
        assert isinstance(response.capabilities, Schema__Service__Capabilities    )
        assert response.session_info.status == Enum__Session__Status.ACTIVE
        assert str(response.session_info.trace_id)                                  # Auto-generated when caller omits
        assert service.session_manager.get(response.session_info.session_id) is not None

    def test__uses_caller_trace_id_when_supplied(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            request  = _create_request(trace_id=Safe_Str__Trace_Id('abc123'))
            response = service.session_create(request)
        assert str(response.session_info.trace_id) == 'abc123'

    def test__applies_credentials_when_supplied(self):
        cookies_ref = Schema__Vault_Ref(vault_key='vk-test', path='/cookies.json')
        cookies     = [{'name': 'sid', 'value': 'abc', 'domain': 'example.com', 'path': '/'}]
        browser     = _FakeBrowser()
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = _build_service(next_browser = browser,
                                     vault_reads  = {'/cookies.json': cookies})
            request = _create_request(credentials=Schema__Session__Credentials(cookies_vault_ref=cookies_ref))
            service.session_create(request)
        assert browser.context.cookies_added == cookies                             # Credentials__Loader applied them

    def test__rejects_distributed_lifetime(self):                                   # Request__Validator raises HTTPException(422)
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = _build_service()
            request = _create_request(lifetime_hint=Enum__Session__Lifetime.PERSISTENT_DISTRIBUTED)
            with pytest.raises(HTTPException) as exc:
                service.session_create(request)
        assert exc.value.status_code == 422
        assert exc.value.detail['error_code'] == 'distributed_not_supported'


class test_session_list_and_get(TestCase):

    def test__list_returns_all_active_sessions(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = _build_service()
            r1 = service.session_create(_create_request())
            r2 = service.session_create(_create_request())
            active = service.session_list()
        ids = {str(s.session_id) for s in active}
        assert ids == {str(r1.session_info.session_id), str(r2.session_info.session_id)}

    def test__get_returns_session_by_id(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            response = service.session_create(_create_request())
            fetched  = service.session_get(response.session_info.session_id)
        assert fetched.session_id == response.session_info.session_id

    def test__get_returns_none_for_unknown_id(self):
        from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id import Session_Id
        service = _build_service()
        assert service.session_get(Session_Id('no-such-session')) is None


class test_session_save_state(TestCase):

    def test__persists_storage_state_to_vault(self):
        storage_state = {'cookies': [{'name': 'k', 'value': 'v'}], 'origins': []}
        browser       = _FakeBrowser(state=storage_state)
        vault_ref     = Schema__Vault_Ref(vault_key='vk', path='/state.json')
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service(next_browser=browser)
            created  = service.session_create(_create_request())
            response = service.session_save_state(created.session_info.session_id,
                                                   Schema__Session__State__Save__Request(vault_ref=vault_ref))
        assert isinstance(response, Schema__Session__State__Save__Response)
        assert response.session_id == created.session_info.session_id
        assert response.vault_ref.path == vault_ref.path
        writer = service.credentials_loader.artefact_writer
        assert len(writer.vault_writes) == 1
        assert writer.vault_writes[0][1] == storage_state                           # Exact dict written

    def test__returns_none_for_unknown_session(self):
        from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id import Session_Id
        service = _build_service()
        request = Schema__Session__State__Save__Request(vault_ref=Schema__Vault_Ref(vault_key='vk', path='/x.json'))
        assert service.session_save_state(Session_Id('nope'), request) is None


class test_session_close(TestCase):

    def test__returns_close_response_and_tears_down_browser(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service  = _build_service()
            created  = service.session_create(_create_request())
            response = service.session_close(created.session_info.session_id)
        assert isinstance(response, Schema__Session__Close__Response)
        assert response.session_info.session_id == created.session_info.session_id
        assert response.total_duration_ms       >= 0
        assert created.session_info.session_id  in service.browser_launcher.stopped
        assert service.session_manager.get(created.session_info.session_id).status == Enum__Session__Status.CLOSED

    def test__returns_none_for_unknown_session(self):
        from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id import Session_Id
        service = _build_service()
        assert service.session_close(Session_Id('nope')) is None


class test_generate_trace_id(TestCase):

    def test__returns_8_char_hex(self):
        trace_id = Playwright__Service().generate_trace_id()
        assert len(trace_id) == 8
        assert all(c in '0123456789abcdef' for c in trace_id)

    def test__values_differ_across_calls(self):
        service = Playwright__Service()
        assert service.generate_trace_id() != service.generate_trace_id()
