# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__S3__Object__Record
# One LETS-inventory record produced from a single S3 ListObjectsV2 entry.
# This is the doc shape indexed into Elastic at sg-cf-inventory-{YYYY-MM-DD}.
# Three field groups:
#   1. Direct S3 fields                   — bucket, key, last_modified, ...
#   2. Derived from key path / filename   — source slug + delivery_{y/m/d/h/m}
#   3. Pipeline metadata + slice 2 hooks  — run id, schema version, processed
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__S3__Storage_Class    import Enum__S3__Storage_Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket   import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__ETag    import Safe_Str__S3__ETag
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key     import Safe_Str__S3__Key
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id


class Schema__S3__Object__Record(Type_Safe):
    # ─── direct from S3 ListObjectsV2 ─────────────────────────────────────────
    bucket           : Safe_Str__S3__Bucket
    key              : Safe_Str__S3__Key
    last_modified    : Safe_Str__Text                                               # ISO-8601 UTC; ES "date" type parses this directly
    size_bytes       : int                           = 0                            # gzipped bytes; 0 is a valid value (empty object)
    etag             : Safe_Str__S3__ETag                                           # md5 hex (or md5-N for multipart); used as Elastic _id
    storage_class    : Enum__S3__Storage_Class       = Enum__S3__Storage_Class.UNKNOWN

    # ─── derived from key path / filename ─────────────────────────────────────
    source           : Enum__LETS__Source__Slug      = Enum__LETS__Source__Slug.UNKNOWN
    delivery_year    : int                           = 0                            # From the Firehose-embedded timestamp in the filename
    delivery_month   : int                           = 0
    delivery_day     : int                           = 0
    delivery_hour    : int                           = 0
    delivery_minute  : int                           = 0
    delivery_at      : Safe_Str__Text                                               # ISO-8601 UTC reconstructed from the parts above
    firehose_lag_ms  : int                           = 0                            # last_modified - delivery_at; can be negative if filename rounds up

    # ─── pipeline metadata ────────────────────────────────────────────────────
    pipeline_run_id  : Safe_Str__Pipeline__Run__Id
    loaded_at        : Safe_Str__Text                                               # ISO-8601 UTC stamped once per run
    schema_version   : Safe_Str__Text                = Safe_Str__Text('Schema__S3__Object__Record_v1')   # Underscore separator — Safe_Str__Text would silently sanitise a "/" to "_"

    # ─── slice 2 hook (content-pass forward declaration) ──────────────────────
    content_processed       : bool                   = False                        # Slice 2 flips this to True when the .gz body has been parsed
    content_extract_run_id  : Safe_Str__Pipeline__Run__Id                           # Empty in slice 1; slice 2 stamps the extract run id
