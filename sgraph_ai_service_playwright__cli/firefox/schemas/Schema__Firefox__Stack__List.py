# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Stack__List
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.collections.List__Schema__Firefox__Stack__Info import List__Schema__Firefox__Stack__Info
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Firefox__Stack__Info
    total  : int = 0
