# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Docker__List
# Returned by `sp docker list`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.docker.collections.List__Schema__Docker__Info import List__Schema__Docker__Info


class Schema__Docker__List(Type_Safe):
    region       : Safe_Str__AWS__Region
    stacks       : List__Schema__Docker__Info
    total        : int = 0
