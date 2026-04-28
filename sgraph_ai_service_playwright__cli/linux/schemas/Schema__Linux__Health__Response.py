# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__Health__Response
# Returned by `sp linux health`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__Linux__Stack__Name import Safe_Str__Linux__Stack__Name


class Schema__Linux__Health__Response(Type_Safe):
    stack_name   : Safe_Str__Linux__Stack__Name
    state        : Enum__Linux__Stack__State = Enum__Linux__Stack__State.UNKNOWN
    healthy      : bool = False
    ssm_reachable: bool = False
    message      : Safe_Str__Text
    elapsed_ms   : int  = 0
