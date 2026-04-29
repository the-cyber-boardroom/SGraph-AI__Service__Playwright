# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Summary
# Type-agnostic view of one running stack for the catalog cross-section list.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type


class Schema__Stack__Summary(Type_Safe):
    type_id        : Enum__Stack__Type
    stack_name     : Safe_Str__Text
    state          : Safe_Str__Text
    public_ip      : Safe_Str__Text
    region         : Safe_Str__Text
    instance_id    : Safe_Str__Text
    uptime_seconds : int = 0
