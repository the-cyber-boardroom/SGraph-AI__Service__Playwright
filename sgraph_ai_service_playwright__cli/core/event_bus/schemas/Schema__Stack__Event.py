# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Event
# Standard payload for all *:stack.created / *:stack.deleted events.
# Emitted by each plugin's service at the success site of create/delete.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text            import Safe_Str__Text

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type                  import Enum__Stack__Type


class Schema__Stack__Event(Type_Safe):
    type_id     : Enum__Stack__Type
    stack_name  : Safe_Str__Text
    region      : Safe_Str__Text
    instance_id : Safe_Str__Text
    timestamp   : Safe_Str__Text
    detail      : Safe_Str__Text
