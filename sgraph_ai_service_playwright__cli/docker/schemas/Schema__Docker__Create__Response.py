# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Docker__Create__Response
# Returned by `sp docker create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info          import Schema__Docker__Info


class Schema__Docker__Create__Response(Type_Safe):
    stack_info    : Schema__Docker__Info
    message       : Safe_Str__Text
    api_key_name  : Safe_Str__Text
    api_key_value : Safe_Str__Text
    elapsed_ms    : int = 0
