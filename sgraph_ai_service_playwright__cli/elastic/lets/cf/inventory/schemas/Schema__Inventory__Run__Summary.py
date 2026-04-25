# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Inventory__Run__Summary
# What `sp el lets cf inventory list` returns — one row per distinct
# pipeline_run_id present in the data index, with quick stats. Derived from
# Elastic terms aggregations on pipeline_run_id; not a stored doc.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id


class Schema__Inventory__Run__Summary(Type_Safe):
    pipeline_run_id  : Safe_Str__Pipeline__Run__Id
    object_count     : int                           = 0                            # Docs in this run
    bytes_total      : int                           = 0                            # Sum of size_bytes for docs in this run
    earliest_loaded  : Safe_Str__Text                                               # min(loaded_at)
    latest_loaded    : Safe_Str__Text                                               # max(loaded_at) — typically same as earliest for a one-shot load
    earliest_delivery: Safe_Str__Text                                               # min(delivery_at)
    latest_delivery  : Safe_Str__Text                                               # max(delivery_at)
