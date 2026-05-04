# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: Schema__OS__Health
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.opensearch.enums.Enum__OS__Stack__State                       import Enum__OS__Stack__State
from sg_compute_specs.opensearch.primitives.Safe_Str__OS__Stack__Name               import Safe_Str__OS__Stack__Name


class Schema__OS__Health(Type_Safe):
    stack_name     : Safe_Str__OS__Stack__Name
    state          : Enum__OS__Stack__State = Enum__OS__Stack__State.UNKNOWN
    cluster_status : Safe_Str__Text
    node_count     : int  = -1
    active_shards  : int  = -1
    doc_count      : int  = -1
    dashboards_ok  : bool = False
    os_endpoint_ok : bool = False
    error          : Safe_Str__Text
