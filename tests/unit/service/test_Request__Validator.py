# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Request__Validator (spec §9)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from fastapi import HTTPException

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Sink_Config        import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.artefact.Schema__S3_Ref                        import Schema__S3_Ref  # noqa: F401  (reference for S3 sink later)
from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                     import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                     import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                      import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Provider                  import Enum__Browser__Provider
from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target                 import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                 import Step_Id
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities          import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click                      import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Evaluate                   import Schema__Step__Evaluate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate                   import Schema__Step__Navigate
from sgraph_ai_service_playwright.service.JS__Expression__Allowlist                       import JS__Expression__Allowlist
from sgraph_ai_service_playwright.service.Request__Validator                              import Request__Validator


def _caps(supports_persistent : bool = False,
          max_lifetime_ms     : int  = 900_000,
          supported_sinks     : list = None,
     ) -> Schema__Service__Capabilities:
    return Schema__Service__Capabilities(
        supports_persistent     = supports_persistent,
        max_session_lifetime_ms = max_lifetime_ms,
        available_browsers      = [Enum__Browser__Name.CHROMIUM],
        supported_sinks         = supported_sinks or [Enum__Artefact__Sink.INLINE],
    )


def _validator() -> Request__Validator:
    v = Request__Validator()
    v.js_allowlist = JS__Expression__Allowlist()                                    # deny-all by default
    return v


class test_validate_browser_config(TestCase):                                        # v0.1.24 — validator surface is now browser_config only (no session schemas)

    def test__none_is_accepted(self):                                               # Stateless callers may omit browser_config entirely
        v = _validator()
        v.validate_browser_config(None, _caps())                                    # No raise

    def test__cdp_missing_endpoint(self):
        v   = _validator()
        cfg = Schema__Browser__Config(provider         = Enum__Browser__Provider.CDP_CONNECT,
                                       cdp_endpoint_url = None                                )
        with pytest.raises(HTTPException) as exc:
            v.validate_browser_config(cfg, _caps())
        assert exc.value.status_code == 422
        assert 'cdp_missing_endpoint' in str(exc.value.detail)

    def test__cdp_with_endpoint_accepted(self):
        v   = _validator()
        cfg = Schema__Browser__Config(provider         = Enum__Browser__Provider.CDP_CONNECT                ,
                                       cdp_endpoint_url = 'http://localhost:9222/devtools'                   )
        v.validate_browser_config(cfg, _caps())                                     # No raise

    def test__default_chromium_accepted(self):
        v = _validator()
        v.validate_browser_config(Schema__Browser__Config(), _caps())               # No raise


class test_validate_step(TestCase):

    def test__evaluate_blocked_by_deny_all_allowlist(self):
        v    = _validator()
        step = Schema__Step__Evaluate(expression='document.title')
        with pytest.raises(HTTPException) as exc:
            v.validate_step(step, Schema__Capture__Config(), _caps(),
                            Enum__Deployment__Target.LAPTOP)
        assert 'evaluate_expression_not_allowed' in str(exc.value.detail)

    def test__evaluate_allowed_when_in_allowlist(self):
        v = _validator()
        v.js_allowlist = JS__Expression__Allowlist(allowed_expressions=['document.title'])
        step = Schema__Step__Evaluate(expression='document.title')
        v.validate_step(step, Schema__Capture__Config(), _caps(),
                        Enum__Deployment__Target.LAPTOP)                            # No raise

    def test__non_evaluate_step_bypasses_allowlist(self):                           # Non-EVALUATE steps should never touch the allowlist
        v    = _validator()
        step = Schema__Step__Navigate(url='https://example.com')
        v.validate_step(step, Schema__Capture__Config(), _caps(),
                        Enum__Deployment__Target.LAPTOP)                            # No raise


class test_validate_sink_configs(TestCase):

    def test__sink_rejected_when_not_in_capabilities(self):
        v    = _validator()
        caps = _caps(supported_sinks=[Enum__Artefact__Sink.INLINE])                 # Lambda-like: no LOCAL_FILE
        cap  = Schema__Capture__Config(
                   screenshot = Schema__Artefact__Sink_Config(enabled=True,
                                                              sink=Enum__Artefact__Sink.LOCAL_FILE))
        with pytest.raises(HTTPException) as exc:
            v.validate_sink_configs(cap, caps, Enum__Deployment__Target.LAMBDA)
        assert 'sink_incompatible_with_deployment' in str(exc.value.detail)

    def test__vault_sink_requires_vault_ref(self):
        v    = _validator()
        caps = _caps(supported_sinks=[Enum__Artefact__Sink.VAULT])
        cap  = Schema__Capture__Config(
                   screenshot = Schema__Artefact__Sink_Config(enabled=True,
                                                              sink=Enum__Artefact__Sink.VAULT,
                                                              sink_vault_ref=None))
        with pytest.raises(HTTPException) as exc:
            v.validate_sink_configs(cap, caps, Enum__Deployment__Target.LAMBDA)
        assert 'sink_missing_vault_ref' in str(exc.value.detail)

    def test__s3_sink_requires_bucket(self):
        v    = _validator()
        caps = _caps(supported_sinks=[Enum__Artefact__Sink.S3])
        cap  = Schema__Capture__Config(
                   screenshot = Schema__Artefact__Sink_Config(enabled=True,
                                                              sink=Enum__Artefact__Sink.S3,
                                                              sink_s3_bucket=None))
        with pytest.raises(HTTPException) as exc:
            v.validate_sink_configs(cap, caps, Enum__Deployment__Target.LAMBDA)
        assert 'sink_missing_s3_bucket' in str(exc.value.detail)

    def test__disabled_sink_is_skipped(self):
        v    = _validator()
        caps = _caps(supported_sinks=[Enum__Artefact__Sink.INLINE])
        cap  = Schema__Capture__Config(
                   screenshot = Schema__Artefact__Sink_Config(enabled=False,
                                                              sink=Enum__Artefact__Sink.LOCAL_FILE))
        v.validate_sink_configs(cap, caps, Enum__Deployment__Target.LAMBDA)         # No raise — disabled sinks aren't checked


class test_validate_step_ids_unique(TestCase):

    def test__rejects_duplicates(self):
        v     = _validator()
        steps = [Schema__Step__Navigate(url='https://a.com', id=Step_Id('step-1')),
                 Schema__Step__Click   (selector='#btn'   , id=Step_Id('step-1'))]
        with pytest.raises(HTTPException) as exc:
            v.validate_step_ids_unique(steps)
        assert 'duplicate_step_ids' in str(exc.value.detail)
        assert 'step-1'             in str(exc.value.detail)

    def test__accepts_unique_ids(self):
        v     = _validator()
        steps = [Schema__Step__Navigate(url='https://a.com', id=Step_Id('step-1')),
                 Schema__Step__Click   (selector='#btn'   , id=Step_Id('step-2'))]
        v.validate_step_ids_unique(steps)                                           # No raise

    def test__skips_empty_ids(self):                                                # Parser will backfill empty ids with the index
        v     = _validator()
        steps = [Schema__Step__Navigate(url='https://a.com'),                       # id defaults to None
                 Schema__Step__Click   (selector='#btn'   )]
        v.validate_step_ids_unique(steps)                                           # No raise


class test_validate_sequence_timeout(TestCase):

    def test__accepts_within_limit(self):
        v = _validator()
        v.validate_sequence_timeout(100_000, _caps(max_lifetime_ms=900_000))        # No raise

    def test__rejects_over_limit(self):
        v = _validator()
        with pytest.raises(HTTPException) as exc:
            v.validate_sequence_timeout(1_000_000, _caps(max_lifetime_ms=900_000))
        assert 'timeout_exceeds_deployment_limit' in str(exc.value.detail)


class test_reject_carries_capabilities(TestCase):                                   # The error payload surfaces caps when provided

    def test__error_payload_round_trips(self):
        v    = _validator()
        caps = _caps()
        try:
            v.reject('custom_code', 'x', capabilities=caps)
        except HTTPException as exc:
            assert exc.status_code == 422
            assert exc.detail['error_code']    == 'custom_code'
            assert exc.detail['error_message'] == 'x'
            assert exc.detail['capabilities']   is not None
