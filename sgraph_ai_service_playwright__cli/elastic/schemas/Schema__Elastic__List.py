# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__List
# Response wrapper for Elastic__Service.list_stacks(). Region on the envelope
# so a serialised response records which region the listing was taken from.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info  import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region


class Schema__Elastic__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Elastic__Info
