# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Health__Response
# Returned by `sp firefox health` / `sp firefox wait`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Stack__State    import Enum__Firefox__Stack__State
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name


class Schema__Firefox__Health__Response(Type_Safe):
    stack_name  : Safe_Str__Firefox__Stack__Name
    state       : Enum__Firefox__Stack__State = Enum__Firefox__Stack__State.UNKNOWN
    healthy     : bool = False
    message     : Safe_Str__Text
    elapsed_ms  : int  = 0
