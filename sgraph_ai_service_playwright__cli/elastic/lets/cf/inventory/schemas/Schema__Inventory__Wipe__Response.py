# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Inventory__Wipe__Response
# Result of `sp el lets cf inventory wipe`. Counts what was actually removed
# so the CLI can render an honest "n indices, m saved objects dropped" line.
# Idempotency check: a second wipe on the same stack returns all-zeros.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


class Schema__Inventory__Wipe__Response(Type_Safe):
    stack_name           : Safe_Str__Elastic__Stack__Name
    indices_dropped      : int                       = 0                            # sg-cf-inventory-* indices removed
    data_views_dropped   : int                       = 0                            # Kibana data view "sg-cf-inventory" removed (0 or 1)
    saved_objects_dropped: int                       = 0                            # Dashboard + every visualisation saved-object removed (current + legacy)
    duration_ms          : int                       = 0
    error_message        : Safe_Str__Text                                           # Empty on success
