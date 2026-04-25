# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Seed__Response
# Result of `sp elastic seed NAME`. duration_ms is the wall-clock time the
# whole bulk-upload took (generation + HTTP round trips) — the user asked us
# to monitor this, so it's carried in the response and printed by the CLI.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


class Schema__Elastic__Seed__Response(Type_Safe):
    stack_name         : Safe_Str__Elastic__Stack__Name
    index              : Safe_Str__Id
    documents_posted   : int              = 0
    documents_failed   : int              = 0
    batches            : int              = 0
    duration_ms        : int              = 0
    docs_per_second    : int              = 0                                       # Integer for Type_Safe simplicity — float precision not needed
    last_http_status   : int              = 0                                       # Most recent HTTP status code from _bulk; 0 if no request made
    last_error_message : Safe_Str__Diagnostic                                       # First non-OK response body (truncated); empty on success
    data_view_id       : Safe_Str__Text                                             # Kibana-generated UUID; empty when --no-data-view or creation failed
    data_view_created  : bool             = False                                   # True when this seed call created the data view; False when it already existed
    data_view_error    : Safe_Str__Diagnostic                                       # Empty on success / when --no-data-view; carries HTTP error otherwise
    dashboard_id       : Safe_Str__Text                                             # Deterministic id from Default__Dashboard__Generator; empty when --no-dashboard or import failed before the request
    dashboard_title    : Safe_Str__Text                                             # Human-readable name shown in the seed table
    dashboard_objects  : int              = 0                                       # How many saved objects were imported (panels + dashboard); 0 on failure
    dashboard_error    : Safe_Str__Diagnostic                                       # Empty on success / when --no-dashboard
