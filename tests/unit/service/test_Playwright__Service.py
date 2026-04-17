# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Playwright__Service (orchestrator; Phase 2.7 health surface)
#
# Scope: only the /health-surface methods exist at this phase. Verifies
# composition, setup() idempotence, and that get_health aggregates the
# three sub-healthchecks.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                               import TestCase

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEFAULT_PROXY_URL     ,
                                                                                                    ENV_VAR__DEFAULT_S3_BUCKET     ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target                    import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.service.Schema__Health                            import Schema__Health
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities             import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Info                     import Schema__Service__Info
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Capability__Detector                              import Capability__Detector
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
