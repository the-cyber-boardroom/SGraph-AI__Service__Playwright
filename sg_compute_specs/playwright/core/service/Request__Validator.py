# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Request__Validator (v0.1.24 — stateless surface)
#
# All cross-schema validation in one place. Raises HTTPException(422) carrying
# a Schema__Error__Response payload on any rejection.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from fastapi                                                                                        import HTTPException

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.core.Schema__Error__Response                              import Schema__Error__Response
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Sink                                import Enum__Artefact__Sink
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Provider                             import Enum__Browser__Provider
from sg_compute_specs.playwright.core.schemas.enums.Enum__Deployment__Target                            import Enum__Deployment__Target
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Capabilities                     import Schema__Service__Capabilities
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sg_compute_specs.playwright.core.service.JS__Expression__Allowlist                                 import JS__Expression__Allowlist


SINK_FIELDS = ['screenshot', 'screenshot_on_fail', 'video', 'pdf',                  # Every capture_config field that carries a sink
               'har', 'trace', 'console_log', 'network_log', 'page_content']


class Request__Validator(Type_Safe):                                                # Cross-schema validation

    js_allowlist : JS__Expression__Allowlist

    def validate_browser_config(self                                          ,
                                browser_config : Schema__Browser__Config      ,
                                capabilities   : Schema__Service__Capabilities
                           ) -> None:
        if browser_config is None:                                                  # Stateless surface — callers may omit; defaults applied by the launcher
            return
        if browser_config.provider == Enum__Browser__Provider.CDP_CONNECT and not browser_config.cdp_endpoint_url:
            self.reject('cdp_missing_endpoint',
                        'cdp_endpoint_url required when provider is cdp_connect')

    def validate_step(self,
                      step         : Schema__Step__Base,
                      cap_config   : Schema__Capture__Config,
                      capabilities : Schema__Service__Capabilities,
                      target       : Enum__Deployment__Target
                 ) -> None:
        if step.action == Enum__Step__Action.EVALUATE:
            if not self.js_allowlist.is_allowed(step.expression):
                self.reject('evaluate_expression_not_allowed',
                            'JS expression not in trusted allowlist')

        self.validate_sink_configs(cap_config, capabilities, target)

    def validate_sink_configs(self,
                              cap_config   : Schema__Capture__Config,
                              capabilities : Schema__Service__Capabilities,
                              target       : Enum__Deployment__Target
                         ) -> None:
        for field_name in SINK_FIELDS:
            sink_config = getattr(cap_config, field_name)
            if not sink_config.enabled:
                continue
            if sink_config.sink not in capabilities.supported_sinks:
                self.reject('sink_incompatible_with_deployment',
                            f"Artefact sink '{sink_config.sink.value}' not available on "
                            f"deployment '{target.value}'. Supported: "
                            f"{[s.value for s in capabilities.supported_sinks]}",
                            capabilities=capabilities)
            if sink_config.sink == Enum__Artefact__Sink.VAULT and not sink_config.sink_vault_ref:
                self.reject('sink_missing_vault_ref',
                            f"sink_vault_ref required for '{field_name}' when sink=vault")
            if sink_config.sink == Enum__Artefact__Sink.S3 and not sink_config.sink_s3_bucket:
                self.reject('sink_missing_s3_bucket',
                            f"sink_s3_bucket required for '{field_name}' when sink=s3")

    def validate_step_ids_unique(self, steps: List[Schema__Step__Base]) -> None:
        ids = [str(s.id) for s in steps if s.id]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            self.reject('duplicate_step_ids', f'Duplicate step IDs: {dupes}')

    def validate_sequence_timeout(self,
                                  total_timeout_ms : int,
                                  capabilities     : Schema__Service__Capabilities
                             ) -> None:
        if total_timeout_ms > capabilities.max_session_lifetime_ms:
            self.reject('timeout_exceeds_deployment_limit',
                        f'Requested {total_timeout_ms}ms exceeds deployment max '
                        f'{capabilities.max_session_lifetime_ms}ms',
                        capabilities=capabilities)

    def reject(self,
               error_code    : str,
               error_message : str,
               capabilities  : Schema__Service__Capabilities = None
          ) -> None:
        raise HTTPException(422, Schema__Error__Response(
            error_code    = error_code    ,
            error_message = error_message ,
            capabilities  = capabilities  ,
        ).json())
