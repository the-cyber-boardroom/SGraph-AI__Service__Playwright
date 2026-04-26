# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Events__Run__Summary
# What `sp el lets cf events list` returns — one row per distinct
# pipeline_run_id present in the events index, with quick stats. Derived
# from Elastic terms aggregations on pipeline_run_id; not a stored doc.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id


class Schema__Events__Run__Summary(Type_Safe):
    pipeline_run_id  : Safe_Str__Pipeline__Run__Id
    event_count      : int                           = 0                              # Docs in this run
    file_count       : int                           = 0                              # Distinct source_etag values seen — # of .gz files this run processed
    bytes_total      : int                           = 0                              # Sum of sc_bytes across docs in this run
    earliest_event   : Safe_Str__Text                                                 # min(timestamp)
    latest_event     : Safe_Str__Text                                                 # max(timestamp)
    earliest_loaded  : Safe_Str__Text                                                 # min(loaded_at)
    latest_loaded    : Safe_Str__Text                                                 # max(loaded_at)
