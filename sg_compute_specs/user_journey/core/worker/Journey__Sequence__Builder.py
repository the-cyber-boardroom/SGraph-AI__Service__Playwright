# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Journey__Sequence__Builder
#
# Turns a Schema__Journey__Definition into a substrate Schema__Sequence__Request:
# copies the journey steps, carries over browser/capture config when present, and
# injects X-SG-Run-Id into extra_http_headers so the mitmproxy per-run capture can
# group this run's flows. The proxy itself is configured by the worker container's
# env (SG_PLAYWRIGHT__DEFAULT_PROXY_URL), not here.
#
# HEADER__RUN_ID must match the mitmproxy run_capture_addon constant — a sync test
# asserts this so the two never drift.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Name            import Safe_Str__Http__Header__Name
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Value           import Safe_Str__Http__Header__Value

from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Request                         import Schema__Sequence__Request
from sg_compute_specs.playwright.core.schemas.session.Schema__Session__Credentials                       import Schema__Session__Credentials

HEADER__RUN_ID = 'X-SG-Run-Id'                                                      # must equal run_capture_addon.HEADER__RUN_ID


class Journey__Sequence__Builder(Type_Safe):                                        # journey definition → substrate request

    def build(self, journey, run_id) -> Schema__Sequence__Request:
        request = Schema__Sequence__Request()
        for step in journey.steps:                                                  # journey.steps is List[dict] (parsed downstream)
            request.steps.append(step)
        if journey.browser_config is not None:
            request.browser_config = journey.browser_config
        if journey.capture_config is not None:
            request.capture_config = journey.capture_config
        request.credentials = Schema__Session__Credentials()
        header_name  = Safe_Str__Http__Header__Name (HEADER__RUN_ID)
        header_value = Safe_Str__Http__Header__Value(str(run_id))
        request.credentials.extra_http_headers[header_name] = header_value
        return request
