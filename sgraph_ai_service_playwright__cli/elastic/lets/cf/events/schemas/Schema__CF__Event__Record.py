# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Event__Record
# One CloudFront real-time log line, parsed and cleaned, indexed at
# sg-cf-events-{YYYY-MM-DD} keyed on the event's timestamp[:10].
# Five field groups:
#   1. Direct from the TSV (~26 fields)
#   2. Derived (Stage 1: status_class + bot_category + is_bot + cache_hit)
#   3. Source lineage (back-reference to inventory by source_etag)
#   4. Pipeline metadata
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

# Slice 1 primitives reused for source lineage:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket       import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__ETag         import Safe_Str__S3__ETag
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key          import Safe_Str__S3__Key

# Slice 2 enums:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category       import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type  import Enum__CF__Edge__Result__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method              import Enum__CF__Method
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Protocol            import Enum__CF__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__SSL__Protocol       import Enum__CF__SSL__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class       import Enum__CF__Status__Class

# Slice 2 primitives:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Cipher         import Safe_Str__CF__Cipher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Content__Type  import Safe_Str__CF__Content__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Country        import Safe_Str__CF__Country
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Edge__Location import Safe_Str__CF__Edge__Location
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Edge__Request__Id import Safe_Str__CF__Edge__Request__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Host           import Safe_Str__CF__Host
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Referer        import Safe_Str__CF__Referer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__URI__Stem      import Safe_Str__CF__URI__Stem
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__User__Agent    import Safe_Str__CF__User__Agent


class Schema__CF__Event__Record(Type_Safe):
    # ─── direct from CloudFront real-time TSV ────────────────────────────────
    timestamp           : Safe_Str__Text                                            # ISO-8601 UTC; ES "date" type parses directly. Derived from Unix seconds.millis (TSV col 1)
    time_taken_ms       : int                                = 0                    # TSV col 2 (seconds) * 1000
    sc_status           : int                                = 0
    sc_bytes            : int                                = 0
    cs_method           : Enum__CF__Method                   = Enum__CF__Method.OTHER
    cs_protocol         : Enum__CF__Protocol                 = Enum__CF__Protocol.OTHER
    cs_host             : Safe_Str__CF__Host
    cs_uri_stem         : Safe_Str__CF__URI__Stem
    x_edge_location     : Safe_Str__CF__Edge__Location
    x_edge_request_id   : Safe_Str__CF__Edge__Request__Id
    ttfb_ms             : int                                = 0                    # time-to-first-byte (seconds * 1000)
    cs_protocol_version : Safe_Str__Text                                            # "HTTP/2.0" / "HTTP/1.1"
    cs_user_agent       : Safe_Str__CF__User__Agent                                 # URL-decoded by Stage 1
    cs_referer          : Safe_Str__CF__Referer                                     # query-stripped by Stage 1
    x_edge_result_type  : Enum__CF__Edge__Result__Type       = Enum__CF__Edge__Result__Type.Other
    ssl_protocol        : Enum__CF__SSL__Protocol            = Enum__CF__SSL__Protocol.OTHER
    ssl_cipher          : Safe_Str__CF__Cipher
    sc_content_type     : Safe_Str__CF__Content__Type
    sc_content_len      : int                                = 0
    sc_range_start      : int                                = -1                   # -1 = "-" (not a range request)
    sc_range_end        : int                                = -1
    c_country           : Safe_Str__CF__Country
    cs_accept_encoding  : Safe_Str__Text                                            # "gzip" / "br" / "-"
    fle_status          : Safe_Str__Text                                            # field-level encryption status; usually "-"
    origin_fbl_ms       : int                                = -1                   # -1 = "-" (no origin call — request answered from edge)
    origin_lbl_ms       : int                                = -1

    # ─── derived (Stage 1 + parser-side) ─────────────────────────────────────
    sc_status_class     : Enum__CF__Status__Class            = Enum__CF__Status__Class.OTHER
    bot_category        : Enum__CF__Bot__Category            = Enum__CF__Bot__Category.UNKNOWN
    is_bot              : bool                               = False                # Convenience: bot_category in {BOT_KNOWN, BOT_GENERIC}
    cache_hit           : bool                               = False                # Convenience: x_edge_result_type in {Hit, RefreshHit, OriginShieldHit}

    # ─── source lineage (back-reference to inventory) ────────────────────────
    source_bucket       : Safe_Str__S3__Bucket                                      # Bucket the .gz came from
    source_key          : Safe_Str__S3__Key                                         # Full key of the .gz file
    source_etag         : Safe_Str__S3__ETag                                        # .gz file's ETag — joins back to inventory by inventory's _id
    line_index          : int                                = 0                    # 0..N within the .gz; combined with source_etag forms _id

    # ─── pipeline metadata ───────────────────────────────────────────────────
    pipeline_run_id     : Safe_Str__Pipeline__Run__Id
    loaded_at           : Safe_Str__Text                                            # ISO-8601 UTC stamped once per run
    schema_version      : Safe_Str__Text                     = Safe_Str__Text('Schema__CF__Event__Record_v1')
