# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Inventory__Load__Response
# Result of `sp el lets cf inventory load`. The CLI renders this into a Rich
# table; downstream automation (slice 4 FastAPI) returns it as JSON.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket   import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix


class Schema__Inventory__Load__Response(Type_Safe):
    run_id           : Safe_Str__Pipeline__Run__Id                                  # Echoed back so callers can correlate
    stack_name       : Safe_Str__Elastic__Stack__Name
    bucket           : Safe_Str__S3__Bucket
    prefix_resolved  : Safe_Str__S3__Key__Prefix                                    # The actual prefix used (may have been auto-resolved from "today UTC")
    pages_listed     : int                           = 0                            # Number of ListObjectsV2 pages consumed
    objects_scanned  : int                           = 0                            # Total objects seen
    objects_indexed  : int                           = 0                            # Bulk-post created
    objects_updated  : int                           = 0                            # Bulk-post updated (etag-id collision = same object, refreshed metadata)
    bytes_total      : int                           = 0                            # Sum of size_bytes across scanned objects
    started_at       : Safe_Str__Text                                               # ISO-8601 UTC
    finished_at      : Safe_Str__Text
    duration_ms      : int                           = 0
    last_http_status : int                           = 0                            # HTTP status of the final bulk-post call (0 if dry_run)
    error_message    : Safe_Str__Text                                               # Empty on success
    kibana_url       : Safe_Str__Text                                               # https://{ip}/app/dashboards (or Discover URL)
    dry_run          : bool                          = False                        # True = nothing was actually indexed
