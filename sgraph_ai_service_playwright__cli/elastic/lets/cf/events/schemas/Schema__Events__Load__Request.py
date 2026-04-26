# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Events__Load__Request
# Inputs for `sp el lets cf events load`. Same default-empty semantics as the
# inventory load — service auto-resolves bucket / prefix / run_id when empty.
# Adds `from_inventory` flag for the manifest-driven path (slice 1's
# content_processed=false hits become the work queue).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket       import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix  import Safe_Str__S3__Key__Prefix


class Schema__Events__Load__Request(Type_Safe):
    bucket           : Safe_Str__S3__Bucket                                         # The CloudFront-realtime bucket; service has a default
    prefix           : Safe_Str__S3__Key__Prefix                                    # Empty + not from_inventory → today UTC's prefix
    all              : bool                          = False                        # Full-bucket scan (S3 listing mode); ignored when from_inventory
    max_files        : int                           = 0                            # 0 = unlimited; otherwise stop after N FILES (NOT events)
    from_inventory   : bool                          = False                        # When set, work queue comes from sg-cf-inventory-* docs where content_processed=false
    skip_processed   : bool                          = False                        # When set, query sg-cf-events-* for distinct source_etag values FIRST and filter them out of the queue. Avoids re-fetching .gz files whose events are already indexed. Cheap (one ES aggregation) vs. the cost of unnecessary GetObjects.
    run_id           : Safe_Str__Pipeline__Run__Id                                  # Empty → service auto-generates
    stack_name       : Safe_Str__Elastic__Stack__Name                               # Empty → auto-pick
    region           : Safe_Str__AWS__Region                                        # Empty → AWS default chain
    dry_run          : bool                          = False                        # Build the queue, skip the fetch + parse + bulk-post + manifest-update
