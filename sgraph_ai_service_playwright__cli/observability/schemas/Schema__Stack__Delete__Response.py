# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Delete__Response
# Aggregate response for Observability__Service.delete_stack(). Holds one
# Schema__Stack__Component__Delete__Result per component (AMP, OpenSearch,
# AMG), even when the component was already missing. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.collections.List__Stack__Component__Delete__Result import List__Stack__Component__Delete__Result
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region                   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__Stack__Name                   import Safe_Str__Stack__Name


class Schema__Stack__Delete__Response(Type_Safe):
    name    : Safe_Str__Stack__Name
    region  : Safe_Str__AWS__Region
    results : List__Stack__Component__Delete__Result
