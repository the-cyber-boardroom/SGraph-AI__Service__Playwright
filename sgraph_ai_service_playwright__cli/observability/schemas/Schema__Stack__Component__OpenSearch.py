# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Component__OpenSearch
# Amazon OpenSearch domain view for the observability stack. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Endpoint   import Safe_Str__AWS__Endpoint
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Int__Document__Count import Safe_Int__Document__Count


class Schema__Stack__Component__OpenSearch(Type_Safe):
    domain_name     : Safe_Str__Id                                                  # AWS domain identifier; matches stack name by convention
    engine_version  : Safe_Str__Id                                                  # Example: OpenSearch_3.5
    status          : Enum__Stack__Component__Status = Enum__Stack__Component__Status.UNKNOWN
    endpoint        : Safe_Str__AWS__Endpoint                                       # Hostname (no scheme, no path)
    dashboards_url  : Safe_Str__Id                                                  # Full https:// URL to the Dashboards UI (empty until endpoint known)
    document_count  : Safe_Int__Document__Count      = -1                           # -1 = not queried / query failed
