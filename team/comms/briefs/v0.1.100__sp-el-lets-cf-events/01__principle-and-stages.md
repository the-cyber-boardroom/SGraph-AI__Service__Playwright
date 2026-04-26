# 01 — Principle and stage mapping

## What changes vs slice 1

Slice 1 was metadata-only: `s3:ListObjectsV2` → typed records → bulk-post.
Slice 2 reads the `.gz` content: `s3:GetObject` → gunzip → parse TSV → typed
records → bulk-post.  The pipeline shape is identical; only the fetcher and
the parser are new.

The LETS principle still holds:

> **Persist Everything Important BEFORE Indexing Anything.**
> Elasticsearch is NOT the source of truth — the S3 bucket is.

Slice 2 doesn't change that.  Like slice 1, the `cloudfront-realtime/` S3
bucket remains the canonical Load layer.  Slice 2's data in Elastic is a
*recomputable projection* of that bucket's contents — `wipe` + re-`load`
gets you back to the same state.

---

## LETS stage map (slice 2)

| LETS | Brief stage | Slice 2 status | Notes |
|------|-------------|----------------|-------|
| **Load** | Stage 0 — raw capture | ✅ already done by AWS | Firehose → S3.  Same as slice 1. |
| (boundary) | Stage 1 — security cleaning | 🟡 minimal scope | URL-decode `cs_user_agent`; trim `cs_referer` query strings; classify bots.  No PII redaction (realtime-log config pre-stripped `c-ip` / `cookie` / query strings). |
| **Extract** | Stage 2 — structured extraction | 🟡 in scope | TSV → typed `Schema__CF__Event__Record` in memory. |
| **Transform** | Stage 3 — signal reduction | ❌ deferred | Kibana's query-time aggs handle rollups for slice 2. Add explicit Transform when cardinality bites. |
| (Index) | Stage 4 — load into Kibana | 🟡 in scope | New `Inventory__HTTP__Client.bulk_post_with_id()` reused; new index family `sg-cf-events-*`. |
| (Explore) | Stage 5 — Kibana usage | 🟡 in scope (one new dashboard) | "CloudFront Logs - Events Overview". |
| **Save** | Stage 6 — screenshot to vault | ❌ deferred | Same as slice 1; lands as a separate slice when both event + inventory dashboards need preserving. |

---

## What slice 2 is the smallest path to

Real questions that the inventory dashboard *cannot* answer but the events
dashboard *will*:

| Question | Panel that answers it |
|----------|----------------------|
| "What's the status code distribution? Any 5xx spikes?" | Status code over time (stacked bar) |
| "Are CloudFront Functions absorbing bot traffic before origin?" | Edge result type breakdown (donut) — `FunctionGeneratedResponse` vs `Hit` vs `Miss` vs `Error` |
| "Which URLs are getting hit the most?" | Top URIs (horizontal bar) |
| "Where's the traffic from?" | Country breakdown (donut, terms on `c_country`) |
| "What's the p50 / p95 / p99 latency?" | Time-taken percentiles over time (line) |
| "What's my cache hit ratio? Is it improving over time?" | Hit ratio over time (line, ratio of Hits / [Hits + Misses + Refreshes]) |
| "Bot vs human traffic split?" | Bot ratio (donut, terms on derived `is_bot` field) |

The inventory dashboard answers "is the pipeline alive?".  The events
dashboard answers "how is the site doing?".  Both useful, both ephemeral.

---

## What gets pre-stripped vs what we redact

The `sgraph-send-cf-logs` realtime-log export config (managed in AWS,
outside this codebase) has already removed:

- `c-ip` (client IP — high PII)
- `x-forwarded-for`
- `cs-cookie`
- `cs-uri-query` (URL query strings, often carry tokens / auth bits)

The fields that remain are operationally useful but vary in PII risk:

| Field | PII shape | Slice 2 treatment |
|-------|-----------|-------------------|
| `cs_user_agent` | Indirect — can fingerprint a browser/version combo | URL-decode; cap length at 500 chars; classify bot/human |
| `cs_referer` | Can leak source URL (e.g. internal links) | Strip query string portion (already pre-stripped per realtime-log config but defensive) |
| `cs_uri_stem` | The path itself; usually not PII | Keep as-is (it IS the data) |
| `c_country` | ISO alpha-2 country code | Keep as-is |
| `x_edge_location` | AWS POP code | Keep as-is |
| `ssl_cipher` / `ssl_protocol` | Capability fingerprint | Keep as-is |
| `time_taken` / `ttfb` / `origin_fbl` / `origin_lbl` | Latency, no PII | Keep as-is, normalise to `_ms` |

**Stage 1 in slice 2 = the URL-decode + trim + bot-classify pass.**  Real
work, but bounded.  Anything heavier (e.g. hashing user-agent strings)
waits for a source whose realtime-log config doesn't pre-strip.

---

## Per-event identity & idempotency

Slice 1 used `_id = etag` so re-loading the same prefix overwrote rather
than duplicated.  Slice 2 extends this:

```
_id = "{source_etag}__{line_index_in_file}"
```

Where:
- `source_etag` is the `.gz` file's ETag (32-hex md5)
- `line_index_in_file` is 0..N within the gunzipped TSV

Properties this gives us:
- Re-loading the same `.gz` file overwrites in place (etag stable per-file)
- Different `.gz` files never collide (different etag)
- Within one file, each line is uniquely identified
- The doc carries `source_etag` as a separate field too, so a join back to
  the inventory doc by etag is one term query

When a file is processed end-to-end, the loader updates the inventory doc
by etag (`POST /sg-cf-inventory-*/_update_by_query` filtered by etag) to
flip `content_processed: true` and stamp `content_extract_run_id`.  This
closes the manifest loop.
