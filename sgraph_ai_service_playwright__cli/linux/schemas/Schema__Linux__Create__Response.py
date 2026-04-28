# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__Create__Response
# Returned by `sp linux create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info            import Schema__Linux__Info


class Schema__Linux__Create__Response(Type_Safe):
    stack_info   : Schema__Linux__Info
    message      : Safe_Str__Text
    elapsed_ms   : int = 0
