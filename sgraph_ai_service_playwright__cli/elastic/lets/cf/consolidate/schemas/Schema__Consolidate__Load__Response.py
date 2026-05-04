# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Consolidate__Load__Response
# Returned by Consolidate__Loader.load().  Mirrors the shape of
# Schema__Events__Load__Response so the orchestrator (v0.1.102) can use a
# uniform summary pattern across all three load steps.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket        import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key           import Safe_Str__S3__Key


class Schema__Consolidate__Load__Response(Type_Safe):
    # ─── identity ─────────────────────────────────────────────────────────────
    run_id              : Safe_Str__Pipeline__Run__Id
    stack_name          : Safe_Str__Elastic__Stack__Name
    date_iso            : Safe_Str__Text
    bucket              : Safe_Str__S3__Bucket
    compat_region       : Safe_Str__Text
    queue_mode          : Safe_Str__Text                                             # 'from-inventory' | 's3-listing'

    # ─── counts ───────────────────────────────────────────────────────────────
    files_queued        : int = 0
    files_processed     : int = 0
    files_skipped       : int = 0
    events_consolidated : int = 0                                                    # Total events written to events.ndjson.gz
    bytes_total         : int = 0                                                    # Sum of source .gz sizes read
    bytes_written       : int = 0                                                    # Compressed bytes written to events.ndjson.gz
    inventory_updated   : int = 0                                                    # Inventory docs stamped with consolidation_run_id

    # ─── output ───────────────────────────────────────────────────────────────
    s3_output_key       : Safe_Str__S3__Key                                          # events.ndjson.gz S3 key; empty on dry_run

    # ─── timing ───────────────────────────────────────────────────────────────
    started_at          : Safe_Str__Text
    finished_at         : Safe_Str__Text
    duration_ms         : int = 0

    # ─── outcome ──────────────────────────────────────────────────────────────
    last_http_status    : int  = 0
    error_message       : Safe_Str__Text
    dry_run             : bool = False
