# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Events__Load__Response
# Result of `sp el lets cf events load`. Carries per-file + aggregate counts
# so the CLI can render a useful summary table (and so the FastAPI duality
# slice can return the same shape as JSON without rework).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket       import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix  import Safe_Str__S3__Key__Prefix


class Schema__Events__Load__Response(Type_Safe):
    run_id              : Safe_Str__Pipeline__Run__Id
    stack_name          : Safe_Str__Elastic__Stack__Name
    bucket              : Safe_Str__S3__Bucket
    prefix_resolved     : Safe_Str__S3__Key__Prefix
    queue_mode          : Safe_Str__Text                                            # "s3-listing" / "from-inventory" — for visibility in the response
    files_queued        : int                       = 0                             # How many .gz files were in the work queue
    files_processed     : int                       = 0                             # Successfully fetched + parsed + bulk-posted
    files_skipped       : int                       = 0                             # Errored or dry-run
    events_indexed      : int                       = 0                             # Sum of created across all bulk-posts
    events_updated      : int                       = 0                             # Sum of updated (etag+line_index dedup hits)
    bytes_total         : int                       = 0                             # Sum of compressed .gz byte counts
    inventory_updated   : int                       = 0                             # Inventory docs flipped to content_processed=true
    started_at          : Safe_Str__Text                                            # ISO-8601 UTC
    finished_at         : Safe_Str__Text
    duration_ms         : int                       = 0
    last_http_status    : int                       = 0
    error_message       : Safe_Str__Text                                            # Empty on success
    kibana_url          : Safe_Str__Url
    dry_run             : bool                      = False
