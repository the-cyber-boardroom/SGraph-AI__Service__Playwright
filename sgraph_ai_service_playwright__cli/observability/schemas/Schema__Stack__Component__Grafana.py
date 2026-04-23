# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Component__Grafana
# Amazon Managed Grafana workspace view for the observability stack. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Endpoint   import Safe_Str__AWS__Endpoint


class Schema__Stack__Component__Grafana(Type_Safe):
    workspace_id : Safe_Str__Id                                                     # AWS-issued workspace identifier (g-xxxxxx)
    name         : Safe_Str__Id                                                     # Human-readable workspace name
    status       : Enum__Stack__Component__Status = Enum__Stack__Component__Status.UNKNOWN
    endpoint     : Safe_Str__AWS__Endpoint                                          # Hostname (no scheme)
    url          : Safe_Str__Id                                                     # Full https:// URL (empty until endpoint known)
