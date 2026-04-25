# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Import__Result
# Result of POST /api/saved_objects/_import. Kibana returns:
#   { success: bool, successCount: N, errors?: [...] }
# We summarise it for the CLI: how many landed, how many failed, and the
# first error message so the user can act without parsing JSON themselves.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Kibana__Import__Result(Type_Safe):
    success        : bool                = False
    success_count  : int                 = 0
    error_count    : int                 = 0
    http_status    : int                 = 0
    first_error    : Safe_Str__Diagnostic                                           # Empty when success_count > 0 and no errors
