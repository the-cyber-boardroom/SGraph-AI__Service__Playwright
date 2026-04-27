# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__OS__Stack__List
# Response wrapper for OpenSearch__Service.list_stacks. Region on the envelope
# so a serialised response records which region the listing was taken from.
# Mirrors Schema__Elastic__List.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.opensearch.collections.List__Schema__OS__Stack__Info import List__Schema__OS__Stack__Info


class Schema__OS__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__OS__Stack__Info
