# 03 — Schemas and module layout

New subpackage parallel to slice 1's `inventory/`:
`sgraph_ai_service_playwright__cli/elastic/lets/cf/events/`.

The `cf/` parent already exists from slice 1 (with `inventory/` underneath).
Slice 2 adds `cf/events/` next to it.  Same one-class-per-file rule.

---

## Module tree

```
sgraph_ai_service_playwright__cli/elastic/lets/cf/events/
  enums/
    Enum__CF__Method                       GET / POST / PUT / DELETE / HEAD / OPTIONS / PATCH / OTHER
    Enum__CF__Protocol                     HTTP / HTTPS / WSS / WS / OTHER
    Enum__CF__Edge__Result__Type           Hit / Miss / RefreshHit / Error / LimitExceeded /
                                            Redirect / FunctionGeneratedResponse / OriginShieldHit / Other
    Enum__CF__SSL__Protocol                TLSv1.2 / TLSv1.3 / TLSv1.0 / TLSv1.1 / OTHER
    Enum__CF__Status__Class                INFORMATIONAL / SUCCESS / REDIRECTION /
                                            CLIENT_ERROR / SERVER_ERROR  (derived from sc_status // 100)
    Enum__CF__Bot__Category                HUMAN / BOT_KNOWN / BOT_GENERIC / UNKNOWN
                                            (derived from cs_user_agent regex match)
  primitives/
    Safe_Str__CF__Country                  ISO-3166 alpha-2 (2-char uppercase)
    Safe_Str__CF__Edge__Location           e.g. "HIO52-P4" — region+POP code
    Safe_Str__CF__Edge__Request__Id        opaque ~52-char base64-ish from CloudFront
    Safe_Str__CF__URI__Stem                URL path; reuses Safe_Str__S3__Key's char set
    Safe_Str__CF__User__Agent              URL-decoded; capped at 500 chars
    Safe_Str__CF__Referer                  capped, query-stripped
    Safe_Str__CF__Host                     hostname pattern
    Safe_Str__CF__Cipher                   ssl cipher name (alphanumeric + underscore)
    Safe_Str__CF__Content__Type            MIME type (e.g. "application/xml")
  schemas/
    Schema__CF__Event__Record              the indexed doc (~30 fields — see below)
    Schema__Events__Load__Request          prefix / all / max_files / from_inventory / run_id / stack / region / bucket / dry_run
    Schema__Events__Load__Response         per-file + aggregate counts + timing + kibana_url
    Schema__Events__Wipe__Response         indices_dropped + dv_dropped + so_dropped + inventory_reset_count
    Schema__Events__Run__Summary           per-run aggregation row for `list`
  collections/
    List__Schema__CF__Event__Record
    List__Schema__Events__Run__Summary
  service/
    S3__Object__Fetcher                    NEW boto3 boundary — get_object_bytes(bucket, key) → bytes (also: in-memory subclass for tests)
    Gzip__Decoder                          tiny utility — decompress(bytes) → str (testable seam)
    CF__Realtime__Log__Parser              TSV string → List__Schema__CF__Event__Record
    Stage1__Cleaner                        URL-decode user-agent, strip referer query, classify bot
    Bot__Classifier                        regex over cs_user_agent → Enum__CF__Bot__Category
    Inventory__Manifest__Reader            queries sg-cf-inventory-* for content_processed=false files; reused by --from-inventory
    Inventory__Manifest__Updater           POST _update_by_query to flip content_processed=true post-fetch
    Events__Loader                         orchestrator
    Events__Wiper                          orchestrator
    Events__Read                           list + health
    CF__Events__Dashboard__Builder         programmatic ndjson (Vis Editor, NOT Lens — same as slice 1)
    CF__Events__Dashboard__Ids             shared id constants
```

CLI: appended to the existing `scripts/elastic_lets.py`.  No additional
modification to `scripts/elastic.py` (the `lets` Typer app is already
mounted; we add `cf_app.add_typer(events_app, name='events')`).

---

## Schema__CF__Event__Record (the indexed doc)

The big one.  ~30 fields = ~26 from the TSV + 4 derived + standard pipeline
metadata.  Pure data.

```
class Schema__CF__Event__Record(Type_Safe):

    # ─── direct from CloudFront real-time TSV (26 fields) ─────────────────
    timestamp           : Safe_Str__Text                                    # ISO-8601 UTC, derived from Unix seconds.millis (col 1)
    time_taken_ms       : int                                  = 0          # col 2 * 1000
    sc_status           : int                                  = 0
    sc_bytes            : int                                  = 0
    cs_method           : Enum__CF__Method                                  # default OTHER on unrecognised
    cs_protocol         : Enum__CF__Protocol
    cs_host             : Safe_Str__CF__Host
    cs_uri_stem         : Safe_Str__CF__URI__Stem
    x_edge_location     : Safe_Str__CF__Edge__Location
    x_edge_request_id   : Safe_Str__CF__Edge__Request__Id
    ttfb_ms             : int                                  = 0          # time-to-first-byte * 1000
    cs_protocol_version : Safe_Str__Text                                    # "HTTP/2.0" / "HTTP/1.1"
    cs_user_agent       : Safe_Str__CF__User__Agent                         # URL-decoded by Stage 1
    cs_referer          : Safe_Str__CF__Referer                             # query-stripped by Stage 1
    x_edge_result_type  : Enum__CF__Edge__Result__Type
    ssl_protocol        : Enum__CF__SSL__Protocol
    ssl_cipher          : Safe_Str__CF__Cipher
    sc_content_type     : Safe_Str__CF__Content__Type
    sc_content_len      : int                                  = 0
    sc_range_start      : int                                  = -1         # -1 = "-" (not a range request)
    sc_range_end        : int                                  = -1
    c_country           : Safe_Str__CF__Country
    cs_accept_encoding  : Safe_Str__Text                                    # "gzip" / "br" etc.
    fle_status          : Safe_Str__Text                                    # field-level encryption status; usually "-"
    origin_fbl_ms       : int                                  = -1         # -1 when "-" (no origin call)
    origin_lbl_ms       : int                                  = -1

    # ─── derived (Stage 1 + Stage 2) ──────────────────────────────────────
    sc_status_class     : Enum__CF__Status__Class                           # INFORMATIONAL / SUCCESS / REDIRECTION / CLIENT_ERROR / SERVER_ERROR
    bot_category        : Enum__CF__Bot__Category                           # HUMAN / BOT_KNOWN / BOT_GENERIC / UNKNOWN
    is_bot              : bool                                 = False      # convenience: bot_category in {BOT_KNOWN, BOT_GENERIC}
    cache_hit           : bool                                 = False      # x_edge_result_type in {Hit, RefreshHit, OriginShieldHit}

    # ─── source lineage (back-reference to inventory) ─────────────────────
    source_bucket       : Safe_Str__S3__Bucket                              # which bucket the .gz came from
    source_key          : Safe_Str__S3__Key                                 # which .gz key
    source_etag         : Safe_Str__S3__ETag                                # the .gz file's etag — joins back to inventory doc by _id
    line_index          : int                                  = 0          # 0..N within the .gz; combined with source_etag forms the _id

    # ─── pipeline metadata ────────────────────────────────────────────────
    pipeline_run_id     : Safe_Str__Pipeline__Run__Id
    loaded_at           : Safe_Str__Text
    schema_version      : Safe_Str__Text                                    # "Schema__CF__Event__Record_v1"
```

---

## Service-class responsibilities

| Class | Owns | Touches |
|-------|------|---------|
| `S3__Object__Fetcher` | `boto3.s3.get_object` for a single key | boto3 — sole new S3 boundary |
| `Gzip__Decoder` | `gzip.decompress(bytes) → str` + edge cases (empty, truncated) | stdlib only |
| `CF__Realtime__Log__Parser` | TSV string → `List__Schema__CF__Event__Record`; handles "-" → 0/-1, URL-encoded user-agent, etc. | None — pure data |
| `Stage1__Cleaner` | URL-decode + trim + bot-classify on each event | `Bot__Classifier` |
| `Bot__Classifier` | UA regex → `Enum__CF__Bot__Category` | None — pure data |
| `Inventory__Manifest__Reader` | `_search` for `content_processed=false` | reuses `Inventory__HTTP__Client.request()` (slice 1) |
| `Inventory__Manifest__Updater` | `_update_by_query` to flip `content_processed=true` | reuses `Inventory__HTTP__Client.request()` |
| `Events__Loader` | Orchestrator: queue → fetch → parse → clean → bulk-post → manifest update | every other class above; reuses `Inventory__HTTP__Client.bulk_post_with_id()` |
| `Events__Wiper` | Drop indices + data view + dashboard + reset manifest | reused HTTP + Kibana clients |
| `Events__Read` | Backs `list` / `health` | reused HTTP + Kibana clients |
| `CF__Events__Dashboard__Builder` | Produces dashboard ndjson programmatically | None — pure data |

---

## Test seams

Every external boundary gets an `*__In_Memory` subclass:

- `S3__Object__Fetcher__In_Memory` — fixture dict `{key: bytes}` returned by `get_object_bytes()`
- `Gzip__Decoder` — pure, no override needed (bytes-in / str-out)
- Reused `Inventory__HTTP__Client__In_Memory` — gains fixtures for the
  events-specific HTTP calls (`update_by_query`, `search`)
- Reused `Kibana__Saved_Objects__Client__In_Memory` — already has the
  needed `find` / `import_objects` overrides from slice 1
- `Bot__Classifier` — pure, tested with canned UA strings

Test file count estimate: ~30 (one per primitive/enum + one per schema +
one per service class).  Aiming for ~80-100 new unit tests.
