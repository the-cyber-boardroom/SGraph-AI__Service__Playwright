# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Events__Wipe__Response
# Result of `sp el lets cf events wipe`. Mirrors inventory's wipe response
# but adds inventory_reset_count — tracking the slice-1 manifest reset.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


class Schema__Events__Wipe__Response(Type_Safe):
    stack_name              : Safe_Str__Elastic__Stack__Name
    indices_dropped         : int                       = 0                          # sg-cf-events-* indices removed
    data_views_dropped      : int                       = 0                          # Kibana data view "sg-cf-events-*" removed (0 or 1)
    saved_objects_dropped   : int                       = 0                          # Dashboard + visualisations removed
    inventory_reset_count   : int                       = 0                          # Inventory docs flipped from content_processed=true back to false
    duration_ms             : int                       = 0
    error_message           : Safe_Str__Text                                          # Empty on success
