# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__OS__Health
# Health snapshot returned by `sp os health <name>` and the matching FastAPI
# route. Captures cluster status (green/yellow/red), node count, doc count,
# and the Dashboards reachability flag. Mirrors Schema__Elastic__Health__Response
# but uses OpenSearch's vocabulary.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name import Safe_Str__OS__Stack__Name


class Schema__OS__Health(Type_Safe):
    stack_name        : Safe_Str__OS__Stack__Name
    state             : Enum__OS__Stack__State    = Enum__OS__Stack__State.UNKNOWN
    cluster_status    : Safe_Str__Text                                              # 'green' | 'yellow' | 'red' | '' (unknown / unreachable)
    node_count        : int                       = -1                              # -1 ⇒ unreachable (couldn't probe); 0 is a valid 'no nodes yet'
    active_shards     : int                       = -1                              # Same convention: -1 ⇒ unreachable
    doc_count         : int                       = -1                              # Across all sg-* indices on the host
    dashboards_ok     : bool                      = False                           # True iff Dashboards UI returns 200 on its login page
    os_endpoint_ok    : bool                      = False                           # True iff /_cluster/health responds with cluster_status
    error             : Safe_Str__Text                                              # Set when any probe failed; empty otherwise
