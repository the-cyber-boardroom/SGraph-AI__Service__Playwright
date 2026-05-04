# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Error__Response (spec §5.10)
#
# Used as the HTTPException detail body. `capabilities` is surfaced when the
# error is a "cannot satisfy" type (e.g. sink_incompatible_with_deployment)
# so callers can adjust their request without a round-trip.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key

from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Capabilities                     import Schema__Service__Capabilities


class Schema__Error__Response(Type_Safe):                                           # HTTPException detail body
    error_code              : Safe_Str__Key                                         # e.g. "sink_incompatible_with_deployment"
    error_message           : Safe_Str__Text
    trace_id                : Safe_Str__Trace_Id = None
    capabilities            : Schema__Service__Capabilities = None                  # Surfaced for "cannot satisfy" errors
