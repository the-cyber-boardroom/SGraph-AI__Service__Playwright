# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Pipeline__Run
# One LETS pipeline-run journal record.  Indexed into
# `sg-pipeline-runs-{YYYY-MM-DD}` with `_id = run_id`, so re-recording the
# same run overwrites in place (idempotent).  Captures everything needed to
# answer "what happened?" without re-running anything:
#   - identity   (run_id, source, verb, stack)
#   - inputs     (bucket, prefix, queue mode, dry_run)
#   - counts     (files / events / bytes / inventory flips)
#   - calls      (s3_calls, elastic_calls — Phase A counters persisted here)
#   - timing     (started_at, finished_at, duration_ms)
#   - outcome    (last_http_status, error_message)
#
# Pure data.  No methods.  Each loader builds one of these at the end of
# load() and hands it to Pipeline__Runs__Tracker.record_run().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket   import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.lets.runs.enums.Enum__Pipeline__Verb       import Enum__Pipeline__Verb


class Schema__Pipeline__Run(Type_Safe):
    # ─── identity ─────────────────────────────────────────────────────────────
    run_id           : Safe_Str__Pipeline__Run__Id                                    # Doubles as the Elastic _id
    source           : Enum__LETS__Source__Slug      = Enum__LETS__Source__Slug.UNKNOWN
    verb             : Enum__Pipeline__Verb          = Enum__Pipeline__Verb.UNKNOWN
    stack_name       : Safe_Str__Elastic__Stack__Name

    # ─── inputs ───────────────────────────────────────────────────────────────
    bucket           : Safe_Str__S3__Bucket                                           # Empty when verb has no S3 dimension (e.g. wipe verbs)
    prefix           : Safe_Str__S3__Key__Prefix                                      # Empty when full-bucket / from-inventory / wipe
    queue_mode       : Safe_Str__Text                                                 # 's3-listing' | 'from-inventory' | 'wipe' | '' (no queue)
    dry_run          : bool                          = False

    # ─── counts (verb-specific; default 0) ────────────────────────────────────
    files_queued      : int                          = 0
    files_processed   : int                          = 0
    files_skipped     : int                          = 0
    events_indexed    : int                          = 0
    events_updated    : int                          = 0
    inventory_updated : int                          = 0                             # Manifest flips (events-load); 0 elsewhere
    pages_listed      : int                          = 0                             # ListObjectsV2 pages (inventory-load); 0 elsewhere
    objects_indexed   : int                          = 0                             # Inventory docs created (inventory-load); 0 elsewhere
    objects_updated   : int                          = 0                             # Inventory docs overwritten (inventory-load); 0 elsewhere
    bytes_total       : int                          = 0

    # ─── Phase A call counters ───────────────────────────────────────────────
    s3_calls         : int                           = 0
    elastic_calls    : int                           = 0

    # ─── wipe-specific counts (0 elsewhere) ──────────────────────────────────
    indices_dropped       : int                      = 0
    data_views_dropped    : int                      = 0
    saved_objects_dropped : int                      = 0
    inventory_reset_count : int                      = 0                             # events-wipe resets manifest flags

    # ─── timing ───────────────────────────────────────────────────────────────
    started_at  : Safe_Str__Text                                                     # ISO-8601 UTC; ES "date" type parses directly
    finished_at : Safe_Str__Text                                                     # ISO-8601 UTC
    duration_ms : int                                = 0                             # Wall-clock; the loader fills this from time.time()

    # ─── outcome ──────────────────────────────────────────────────────────────
    last_http_status : int                           = 0
    error_message    : Safe_Str__Text                                                # Empty on success
    schema_version   : Safe_Str__Text                = Safe_Str__Text('Schema__Pipeline__Run_v1')   # Underscore separator (Safe_Str__Text would silently sanitise "/" to "_")
