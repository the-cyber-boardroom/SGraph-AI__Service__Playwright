# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Seed__Response
# Result of `sp elastic seed NAME`. duration_ms is the wall-clock time the
# whole bulk-upload took (generation + HTTP round trips) — the user asked us
# to monitor this, so it's carried in the response and printed by the CLI.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
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
