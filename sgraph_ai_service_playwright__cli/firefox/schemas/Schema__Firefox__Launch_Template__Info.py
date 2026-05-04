# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Launch_Template__Info
# One row in the launch-template list. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Launch_Template__Info(Type_Safe):
    lt_name      : Safe_Str__Firefox__Stack__Name
    lt_id        : Safe_Str__Text
    lt_version   : int = 0
    region       : Safe_Str__AWS__Region
    created_time : Safe_Str__Text
