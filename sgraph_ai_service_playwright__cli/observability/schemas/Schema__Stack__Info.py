# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Info
# Aggregate view of one observability stack (AMP + OpenSearch + AMG). Any
# component can be None when the underlying AWS resource is missing.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__Stack__Name     import Safe_Str__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region     import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP        import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana    import Schema__Stack__Component__Grafana


class Schema__Stack__Info(Type_Safe):
    name       : Safe_Str__Stack__Name
    region     : Safe_Str__AWS__Region
    amp        : Schema__Stack__Component__AMP        = None                       # None = AMP workspace absent
    opensearch : Schema__Stack__Component__OpenSearch = None                       # None = OS domain absent
    grafana    : Schema__Stack__Component__Grafana    = None                       # None = AMG workspace absent
