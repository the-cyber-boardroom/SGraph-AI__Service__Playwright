# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Dashboard__Result
# Result of ensure_default_dashboard: the dashboard id (deterministic, set by
# Default__Dashboard__Generator), a `created` flag distinguishing "we
# imported it" from "it already existed", the HTTP status, and a diagnostic
# line on failure. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Kibana__Dashboard__Result(Type_Safe):
    id           : Safe_Str__Text                                                   # Empty when the import failed before we knew the id
    title        : Safe_Str__Text
    object_count : int                = 0                                           # How many saved objects were imported (panels + dashboard)
    created      : bool               = False                                       # True when at least one object was newly created this run
    http_status  : int                = 0
    error        : Safe_Str__Diagnostic
