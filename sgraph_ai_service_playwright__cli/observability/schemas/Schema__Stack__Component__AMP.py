# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Component__AMP
# Amazon Managed Prometheus workspace view as surfaced to CLI + FastAPI callers.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status import Enum__Stack__Component__Status


class Schema__Stack__Component__AMP(Type_Safe):
    workspace_id     : Safe_Str__Id                                                 # AWS-issued workspace identifier (ws-xxxxxx)
    alias            : Safe_Str__Id                                                 # Human alias; matches the stack name by convention
    status           : Enum__Stack__Component__Status = Enum__Stack__Component__Status.UNKNOWN
    remote_write_url : Safe_Str__Id                                                 # Full AMP remote_write URL (reconstructed from region + workspace_id)
