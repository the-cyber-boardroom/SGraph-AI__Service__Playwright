# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Consolidated__Manifest
# Per-day sidecar written alongside `events.ndjson.gz` at:
#   lets/raw-cf-to-consolidated/{YYYY/MM/DD}/manifest.json
#
# Decision #5c: run-specific data lives here; compat-region metadata lives in
# `lets-config.json` at the region root.  Two separate concerns, two files.
# Decision #6: also dual-persisted as a doc in `sg-cf-consolidated-{date}`.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket        import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key           import Safe_Str__S3__Key


class Schema__Consolidated__Manifest(Type_Safe):
    # ─── identity ─────────────────────────────────────────────────────────────
    run_id                 : Safe_Str__Pipeline__Run__Id                              # Doubles as the Elastic _id (decision #6)
    date_iso               : Safe_Str__Text                                          # "YYYY-MM-DD" — the date being consolidated

    # ─── source counts ────────────────────────────────────────────────────────
    source_count           : int = 0                                                 # Number of source .gz files consumed
    event_count            : int = 0                                                 # Total parsed events written to events.ndjson.gz

    # ─── output location ──────────────────────────────────────────────────────
    bucket                 : Safe_Str__S3__Bucket
    s3_output_key          : Safe_Str__S3__Key                                       # Key of the events.ndjson.gz artefact
    bytes_written          : int = 0                                                 # Compressed bytes written

    # ─── version stamps ───────────────────────────────────────────────────────
    parser_version         : Safe_Str__Text
    bot_classifier_version : Safe_Str__Text
    compat_region          : Safe_Str__Text                                          # "raw-cf-to-consolidated"

    # ─── timing ───────────────────────────────────────────────────────────────
    consolidated_at        : Safe_Str__Text                                          # ISO-8601 UTC; start of consolidation run
    started_at             : Safe_Str__Text
    finished_at            : Safe_Str__Text

    schema_version         : Safe_Str__Text = Safe_Str__Text('Schema__Consolidated__Manifest_v1')
