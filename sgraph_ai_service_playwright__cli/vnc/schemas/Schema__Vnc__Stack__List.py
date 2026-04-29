# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Stack__List
# Response wrapper for Vnc__Service.list_stacks. Region on the envelope so a
# serialised response records which region the listing was taken from.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info import List__Schema__Vnc__Stack__Info


class Schema__Vnc__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Vnc__Stack__Info
