# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__List
# Response wrapper for Observability__Service.list_stacks(). Carrying the
# region on the envelope means a serialised response tells you which region
# the listing was taken from, which matters because stack names are not
# globally unique.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region  import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Info     import List__Stack__Info


class Schema__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Stack__Info
