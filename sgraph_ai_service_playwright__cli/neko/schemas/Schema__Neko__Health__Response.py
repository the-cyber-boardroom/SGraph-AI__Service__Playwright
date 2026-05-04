# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Neko__Health__Response
# Returned by `sp neko health` / `sp neko wait`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.neko.enums.Enum__Neko__Stack__State          import Enum__Neko__Stack__State
from sgraph_ai_service_playwright__cli.neko.primitives.Safe_Str__Neko__Stack__Name  import Safe_Str__Neko__Stack__Name


class Schema__Neko__Health__Response(Type_Safe):
    stack_name  : Safe_Str__Neko__Stack__Name
    state       : Enum__Neko__Stack__State = Enum__Neko__Stack__State.UNKNOWN
    healthy     : bool = False
    message     : Safe_Str__Text
    elapsed_ms  : int  = 0
