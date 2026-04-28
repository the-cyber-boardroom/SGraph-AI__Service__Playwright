# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__List
# Returned by `sp linux list`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.linux.collections.List__Schema__Linux__Info  import List__Schema__Linux__Info


class Schema__Linux__List(Type_Safe):
    region       : Safe_Str__AWS__Region
    stacks       : List__Schema__Linux__Info
    total        : int = 0
