# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Component__Delete__Result
# Per-component outcome when deleting a stack. resource_id carries the AWS id
# of what was (or would have been) deleted; error_message is populated on
# FAILED outcomes only. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Component__Delete__Outcome import Enum__Component__Delete__Outcome
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Kind     import Enum__Stack__Component__Kind


class Schema__Stack__Component__Delete__Result(Type_Safe):
    kind          : Enum__Stack__Component__Kind
    outcome       : Enum__Component__Delete__Outcome = Enum__Component__Delete__Outcome.NOT_FOUND
    resource_id   : Safe_Str__Id                                                    # AWS-issued id of the targeted resource (empty if nothing matched)
    error_message : Safe_Str__Text                                                  # Populated on FAILED outcomes; empty otherwise
