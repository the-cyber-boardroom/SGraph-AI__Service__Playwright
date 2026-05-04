# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Capability__Detector (spec §4.6)
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sgraph_ai_service_playwright.consts.env_vars                    import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                             ENV_VAR__CI                    ,
                                                                             ENV_VAR__CLAUDE_SESSION        ,
                                                                             ENV_VAR__DEFAULT_PROXY_URL     ,
                                                                             ENV_VAR__DEFAULT_S3_BUCKET     ,
                                                                             ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                             ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink    import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name     import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target import Enum__Deployment__Target
from sgraph_ai_service_playwright.service.Capability__Detector           import Capability__Detector


ENV_KEYS_TO_SCRUB = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                     ENV_VAR__CI                    ,
                     ENV_VAR__CLAUDE_SESSION        ,
                     ENV_VAR__DEFAULT_PROXY_URL     ,
                     ENV_VAR__DEFAULT_S3_BUCKET     ,
                     ENV_VAR__DEPLOYMENT_TARGET     ,
                     ENV_VAR__SG_SEND_BASE_URL      ]


class _EnvScrub:                                                                    # Context-mgr: snapshot/restore only the env vars we mutate

    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}

    def __enter__(self):
        for k in ENV_KEYS_TO_SCRUB:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k in ENV_KEYS_TO_SCRUB:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class test_detect_target(TestCase):

    def test__explicit_override_wins(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET    : 'lambda',
                          ENV_VAR__AWS_LAMBDA_RUNTIME_API: ''      ,
                          ENV_VAR__CI                   : 'true'  }):                # Even with CI set, explicit override wins
            assert Capability__Detector().detect_target() == Enum__Deployment__Target.LAMBDA

    def test__lambda_detected_from_runtime_api(self):
        with _EnvScrub(**{ENV_VAR__AWS_LAMBDA_RUNTIME_API: '127.0.0.1:9001'}):
            assert Capability__Detector().detect_target() == Enum__Deployment__Target.LAMBDA

    def test__claude_web_detected_from_session(self):
        with _EnvScrub(**{ENV_VAR__CLAUDE_SESSION: 'session-id'}):
            assert Capability__Detector().detect_target() == Enum__Deployment__Target.CLAUDE_WEB

    def test__ci_detected_from_ci_env(self):
        with _EnvScrub(**{ENV_VAR__CI: 'true'}):
            assert Capability__Detector().detect_target() == Enum__Deployment__Target.CI

    def test__laptop_is_the_default(self):
        with _EnvScrub():
            assert Capability__Detector().detect_target() == Enum__Deployment__Target.LAPTOP


class test_build_capabilities(TestCase):

    def test__lambda_profile(self):
        with _EnvScrub():                                                           # No vault/proxy env set
            caps = Capability__Detector().build_capabilities(Enum__Deployment__Target.LAMBDA)
        assert caps.max_session_lifetime_ms    == 900_000
        assert caps.supports_persistent        is False
        assert caps.supports_video             is True
        assert caps.available_browsers         == [Enum__Browser__Name.CHROMIUM     ,   # All three engines ship with the Microsoft playwright base image — Firefox/WebKit are the only path to native proxy-auth support
                                                   Enum__Browser__Name.FIREFOX      ,
                                                   Enum__Browser__Name.WEBKIT       ]
        assert Enum__Artefact__Sink.LOCAL_FILE not in caps.supported_sinks           # Lambda has no writable disk for retrieval
        assert caps.has_s3_access              is True
        assert caps.has_vault_access           is False                              # SG_SEND_BASE_URL not set
        assert caps.proxy_configured           is False                              # DEFAULT_PROXY_URL not set

    def test__claude_web_profile(self):
        with _EnvScrub():
            caps = Capability__Detector().build_capabilities(Enum__Deployment__Target.CLAUDE_WEB)
        assert caps.max_session_lifetime_ms == 600_000
        assert caps.supports_persistent     is False
        assert caps.supported_sinks         == [Enum__Artefact__Sink.INLINE]        # Claude_web only surfaces inline artefacts
        assert caps.has_vault_access        is False
        assert caps.has_s3_access           is False
        assert caps.proxy_configured        is True                                 # Pinned True per spec

    def test__laptop_profile(self):
        with _EnvScrub():
            caps = Capability__Detector().build_capabilities(Enum__Deployment__Target.LAPTOP)
        assert caps.max_session_lifetime_ms     == 14_400_000
        assert caps.supports_persistent         is True
        assert Enum__Browser__Name.CHROMIUM     in caps.available_browsers
        assert Enum__Browser__Name.FIREFOX      in caps.available_browsers
        assert Enum__Browser__Name.WEBKIT       in caps.available_browsers
        assert Enum__Artefact__Sink.LOCAL_FILE  in caps.supported_sinks             # Laptop has writable disk

    def test__ci_profile_derives_from_laptop(self):
        with _EnvScrub():
            caps = Capability__Detector().build_capabilities(Enum__Deployment__Target.CI)
        assert caps.supports_persistent     is False                                # CI overrides laptop's True
        assert caps.max_session_lifetime_ms == 600_000                              # CI overrides laptop's 14_400_000
        assert Enum__Browser__Name.FIREFOX  in caps.available_browsers              # But keeps laptop's browser list

    def test__container_profile_equals_laptop(self):
        with _EnvScrub():
            detector = Capability__Detector()
            caps_c   = detector.build_capabilities(Enum__Deployment__Target.CONTAINER)
            caps_l   = detector.build_capabilities(Enum__Deployment__Target.LAPTOP)
        assert caps_c.json() == caps_l.json()                                       # Identical profile

    def test__vault_and_proxy_flags_follow_env(self):
        with _EnvScrub(**{ENV_VAR__SG_SEND_BASE_URL : 'http://vault.local' ,
                          ENV_VAR__DEFAULT_S3_BUCKET: 'my-bucket'          ,
                          ENV_VAR__DEFAULT_PROXY_URL: 'http://proxy:3128'  }):
            caps = Capability__Detector().build_capabilities(Enum__Deployment__Target.LAPTOP)
        assert caps.has_vault_access is True
        assert caps.has_s3_access    is True
        assert caps.proxy_configured is True


class test_detect(TestCase):

    def test__detect_populates_target_and_capabilities(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            d = Capability__Detector().detect()
        assert d.target()       == Enum__Deployment__Target.LAMBDA
        assert d.capabilities() is not None
        assert d.capabilities().supports_persistent is False                        # Lambda profile applied

    def test__detect_returns_self_for_chaining(self):
        with _EnvScrub():
            d = Capability__Detector()
            assert d.detect() is d                                                  # Chaining contract


class test_connectivity_check(TestCase):

    def test__healthy_when_vault_url_set(self):
        with _EnvScrub(**{ENV_VAR__SG_SEND_BASE_URL: 'http://vault.local'}):
            hc = Capability__Detector().connectivity_check()
        assert hc.check_name == 'connectivity'
        assert hc.healthy    is True
        assert 'vault.local' in str(hc.detail)

    def test__unhealthy_when_vault_url_missing(self):
        with _EnvScrub():
            hc = Capability__Detector().connectivity_check()
        assert hc.healthy is False


class test_extract_version_digits(TestCase):

    def test__parses_chrome_path_segment(self):
        d = Capability__Detector()
        assert d.extract_version_digits('chrome-1234')       == '1234'
        assert d.extract_version_digits('chromium-125.0.1')  == '125.0.1'
        assert d.extract_version_digits('no-digits-here')    == '0.0.0'             # FALLBACK_VERSION


class test_service_info(TestCase):

    def test__service_info_round_trips(self):                                       # Chromium version may be fallback in sandbox; structure must still be valid
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'}):
            info = Capability__Detector().detect().service_info()
        assert str(info.service_name)      == 'sg-playwright'
        assert info.deployment_target      == Enum__Deployment__Target.LAPTOP
        assert info.capabilities           is not None
        assert str(info.service_version).startswith('v')                            # Repo version file is 'v0.1.0'
