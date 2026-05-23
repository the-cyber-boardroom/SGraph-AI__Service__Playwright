# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__TUI__Block_Group
# One row of the Blocks surface: blocked requests aggregated by (reason, rule, action)
# with a count. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action          import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer           import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Reason import Safe_Str__Sentinel__Reason
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id import Safe_Str__Sentinel__Rule_Id


class Schema__Sentinel__TUI__Block_Group(Type_Safe):
    reason  : Safe_Str__Sentinel__Reason
    rule_id : Safe_Str__Sentinel__Rule_Id
    layer   : Enum__Sentinel__Layer  = Enum__Sentinel__Layer.L1
    action  : Enum__Sentinel__Action = Enum__Sentinel__Action.DROP_403
    count   : int                    = 0
