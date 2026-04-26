# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CF__Realtime__Log__Parser
# Parses a CloudFront real-time TSV string (the gunzipped contents of a .gz
# file) into a List__Schema__CF__Event__Record.  Combines TSV parsing AND
# the Stage 1 derivations (sc_status_class, bot_category, is_bot, cache_hit)
# in a single pass.
#
# TSV column order (26 columns; positions 0-indexed):
#   0  timestamp           Unix seconds.millis (float)
#   1  time-taken          seconds (float)
#   2  sc-status           int
#   3  sc-bytes            int
#   4  cs-method           string
#   5  cs-protocol         "http" / "https"
#   6  cs-host             hostname
#   7  cs-uri-stem         URL path
#   8  x-edge-location     POP code (e.g. "HIO52-P4")
#   9  x-edge-request-id   base64-ish
#  10  time-to-first-byte  seconds (float)
#  11  cs-protocol-version "HTTP/2.0" / "HTTP/1.1"
#  12  cs-user-agent       URL-encoded string
#  13  cs-referer          URL or "-"
#  14  x-edge-detailed-result-type "Hit" / "Miss" / "FunctionGeneratedResponse" / ...
#  15  ssl-protocol        "TLSv1.3" / ...
#  16  ssl-cipher          IANA cipher name
#  17  sc-content-type     MIME or "-"
#  18  sc-content-len      int or "-"
#  19  sc-range-start      int or "-"
#  20  sc-range-end        int or "-"
#  21  c-country           ISO-3166 alpha-2 or "-"
#  22  cs-accept-encoding  "gzip" / "br" / "-"
#  23  fle-status          field-level-encryption status; usually "-"
#  24  origin-fbl          float seconds or "-"
#  25  origin-lbl          float seconds or "-"
#
# The "-" placeholder is the standard CloudFront convention for "missing"; we
# normalise to:
#   - empty string for string fields
#   - 0 / -1 for numeric fields (per Schema__CF__Event__Record defaults)
#
# Lines that fail to parse (wrong column count, bad timestamp, etc.) are
# COUNTED but skipped — `parse()` returns (records, skipped_count) so the
# loader can surface the count without aborting the whole file.
#
# source_etag, source_bucket, source_key, line_index, pipeline_run_id,
# loaded_at are stamped by the caller (Events__Loader) — this parser only
# fills the per-line fields.
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.parse
from datetime                                                                       import datetime, timezone
from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category       import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type  import Enum__CF__Edge__Result__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method              import Enum__CF__Method
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Protocol            import Enum__CF__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__SSL__Protocol       import Enum__CF__SSL__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class       import Enum__CF__Status__Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record import Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier            import Bot__Classifier


CF_REALTIME_COLUMN_COUNT = 26                                                       # Expected column count per TSV row


# ─── module-level helpers ────────────────────────────────────────────────────

def gunzip(gzipped: bytes) -> str:                                                  # Decompress + decode UTF-8 (CF logs are ASCII-safe)
    import gzip
    if not gzipped:
        return ''
    return gzip.decompress(gzipped).decode('utf-8', errors='replace')


def parse_unix_to_iso(field: str) -> str:                                           # "1777075217.167" → "2026-04-21T08:00:17.167Z"
    try:
        seconds = float(field)
    except (ValueError, TypeError):
        return ''
    dt    = datetime.fromtimestamp(seconds, tz=timezone.utc)
    millis = int(round((seconds - int(seconds)) * 1000))
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + f'.{millis:03d}Z'


def parse_seconds_to_ms(field: str, default: int = 0) -> int:                       # "0.001" → 1; "0.924" → 924; "-" → default
    if not field or field == '-':
        return default
    try:
        return int(round(float(field) * 1000))
    except (ValueError, TypeError):
        return default


def parse_int_or(field: str, default: int = 0) -> int:                              # "302" → 302; "-" → default
    if not field or field == '-':
        return default
    try:
        return int(field)
    except (ValueError, TypeError):
        return default


def parse_dash_or(field: str) -> str:                                               # "-" → ""; otherwise unchanged
    if not field or field == '-':
        return ''
    return field


def status_class_from_int(sc_status: int) -> Enum__CF__Status__Class:               # 200 → SUCCESS, 404 → CLIENT_ERROR, etc.
    if sc_status >= 100 and sc_status < 200: return Enum__CF__Status__Class.INFORMATIONAL
    if sc_status >= 200 and sc_status < 300: return Enum__CF__Status__Class.SUCCESS
    if sc_status >= 300 and sc_status < 400: return Enum__CF__Status__Class.REDIRECTION
    if sc_status >= 400 and sc_status < 500: return Enum__CF__Status__Class.CLIENT_ERROR
    if sc_status >= 500 and sc_status < 600: return Enum__CF__Status__Class.SERVER_ERROR
    return Enum__CF__Status__Class.OTHER


CACHE_HIT_RESULT_TYPES = {Enum__CF__Edge__Result__Type.Hit,
                          Enum__CF__Edge__Result__Type.RefreshHit,
                          Enum__CF__Edge__Result__Type.OriginShieldHit}


def safe_enum(enum_cls, raw: str, default):                                         # "Hit" → Enum.Hit; "Garbage" → default; "-" → default
    if not raw or raw == '-':
        return default
    try:
        return enum_cls(raw)
    except (ValueError, KeyError):
        return default


def clean_referer(raw: str) -> str:                                                 # Strip query string portion (defensive — CF config may have already done this)
    cleaned = parse_dash_or(raw)
    if not cleaned:
        return ''
    q_pos = cleaned.find('?')
    if q_pos >= 0:
        cleaned = cleaned[:q_pos]
    return cleaned[:1024]                                                            # Cap to fit Safe_Str__CF__Referer's max_length


def clean_user_agent(raw: str) -> str:                                              # URL-decode and cap
    decoded = parse_dash_or(raw)
    if not decoded:
        return ''
    decoded = urllib.parse.unquote(decoded)
    return decoded[:500]


def normalise_country(raw: str) -> str:                                             # Uppercase before construction (Safe_Str__CF__Country regex requires uppercase)
    cleaned = parse_dash_or(raw)
    return cleaned.upper() if cleaned else ''


def normalise_edge_location(raw: str) -> str:
    cleaned = parse_dash_or(raw)
    return cleaned.upper() if cleaned else ''


def normalise_cipher(raw: str) -> str:
    cleaned = parse_dash_or(raw)
    return cleaned.upper() if cleaned else ''


# ─── parser class ────────────────────────────────────────────────────────────

class CF__Realtime__Log__Parser(Type_Safe):
    bot_classifier : Bot__Classifier

    @type_safe
    def parse(self, tsv_text: str) -> Tuple[List__Schema__CF__Event__Record, int]:  # (records, lines_skipped)
        records         = List__Schema__CF__Event__Record()
        lines_skipped   = 0
        if not tsv_text:
            return records, 0

        for line_index, raw_line in enumerate(tsv_text.split('\n')):
            line = raw_line.rstrip('\r')
            if not line.strip():                                                     # Skip empty / whitespace-only lines (e.g. trailing newline)
                continue
            cols = line.split('\t')
            if len(cols) != CF_REALTIME_COLUMN_COUNT:
                lines_skipped += 1
                continue
            try:
                record = self.row_to_record(cols)
                record.line_index = len(records)                                     # Index within the records we successfully parsed (NOT the raw line index, which would include skipped lines)
            except Exception:                                                        # Defensive: any parsing error → skip the row, keep going
                lines_skipped += 1
                continue
            records.append(record)
        return records, lines_skipped

    def row_to_record(self, cols: list) -> Schema__CF__Event__Record:               # Single TSV row → typed Record (no line_index / no source lineage / no pipeline metadata yet)
        sc_status     = parse_int_or(cols[2], 0)
        cs_user_agent = clean_user_agent(cols[12])
        edge_result   = safe_enum(Enum__CF__Edge__Result__Type, cols[14], Enum__CF__Edge__Result__Type.Other)
        bot_cat       = self.bot_classifier.classify(cs_user_agent)

        return Schema__CF__Event__Record(timestamp           = parse_unix_to_iso(cols[0])                                ,
                                          time_taken_ms       = parse_seconds_to_ms(cols[1], 0)                            ,
                                          sc_status           = sc_status                                                  ,
                                          sc_bytes            = parse_int_or(cols[3], 0)                                   ,
                                          cs_method           = safe_enum(Enum__CF__Method, cols[4], Enum__CF__Method.OTHER) ,
                                          cs_protocol         = safe_enum(Enum__CF__Protocol, cols[5], Enum__CF__Protocol.OTHER),
                                          cs_host             = parse_dash_or(cols[6]).lower()                              ,    # Hostnames are case-insensitive; lowercase to match Safe_Str__CF__Host
                                          cs_uri_stem         = parse_dash_or(cols[7])                                      ,
                                          x_edge_location     = normalise_edge_location(cols[8])                            ,
                                          x_edge_request_id   = parse_dash_or(cols[9])                                      ,
                                          ttfb_ms             = parse_seconds_to_ms(cols[10], 0)                            ,
                                          cs_protocol_version = parse_dash_or(cols[11])                                     ,
                                          cs_user_agent       = cs_user_agent                                               ,
                                          cs_referer          = clean_referer(cols[13])                                     ,
                                          x_edge_result_type  = edge_result                                                 ,
                                          ssl_protocol        = safe_enum(Enum__CF__SSL__Protocol, cols[15], Enum__CF__SSL__Protocol.OTHER),
                                          ssl_cipher          = normalise_cipher(cols[16])                                  ,
                                          sc_content_type     = parse_dash_or(cols[17]).lower()                             ,    # Lowercase for Safe_Str__CF__Content__Type's regex
                                          sc_content_len      = parse_int_or(cols[18], 0)                                   ,
                                          sc_range_start      = parse_int_or(cols[19], -1)                                  ,
                                          sc_range_end        = parse_int_or(cols[20], -1)                                  ,
                                          c_country           = normalise_country(cols[21])                                 ,
                                          cs_accept_encoding  = parse_dash_or(cols[22])                                     ,
                                          fle_status          = parse_dash_or(cols[23])                                     ,
                                          origin_fbl_ms       = parse_seconds_to_ms(cols[24], -1)                           ,
                                          origin_lbl_ms       = parse_seconds_to_ms(cols[25], -1)                           ,
                                          # Stage 1 derivations:
                                          sc_status_class     = status_class_from_int(sc_status)                            ,
                                          bot_category        = bot_cat                                                     ,
                                          is_bot              = bot_cat in (Enum__CF__Bot__Category.BOT_KNOWN, Enum__CF__Bot__Category.BOT_GENERIC),
                                          cache_hit           = edge_result in CACHE_HIT_RESULT_TYPES                       )
