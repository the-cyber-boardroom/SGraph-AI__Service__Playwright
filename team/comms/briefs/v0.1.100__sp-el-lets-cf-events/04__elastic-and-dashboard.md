# 04 — Elastic, Kibana, and the dashboard

## Naming

Mirrors slice 1's convention with `events` instead of `inventory`.  Both
families coexist in the same Kibana without collisions.

| Artifact | Name | Notes |
|----------|------|-------|
| Index | `sg-cf-events-{YYYY-MM-DD}` | Daily rolling, keyed on each event's `timestamp[:10]` (NOT loaded_at — same lesson as slice 1's bug fix) |
| Data view | `sg-cf-events-*` | Wildcard pattern, time field `timestamp` |
| Dashboard | `CloudFront Logs - Events Overview` | Saved-object id `sg-cf-events-overview` |
| Visualisations | `sg-cf-evt-vis-{slug}` | Deterministic ids — same idempotent re-import pattern |

The two index families are independent — `sp el lets cf inventory wipe`
does NOT touch `sg-cf-events-*`, and vice versa.

---

## Index mapping (slice 2)

ES auto-mapping covers most fields.  String fields needing terms aggs use
the `.keyword` sub-field (lesson from slice 1's storage_class bug — the
regression test in slice 1 will catch any new offenders during dashboard
tests).

Key fields and types:

| Field | ES type | Reason |
|-------|---------|--------|
| `timestamp` | `date` | Dashboard time field |
| `time_taken_ms` / `ttfb_ms` / `origin_fbl_ms` / `origin_lbl_ms` | `long` | percentile + sum aggs |
| `sc_status` | `integer` | terms agg directly (numeric, no `.keyword` needed) |
| `sc_status_class` | `keyword` (auto + `.keyword`) | terms agg uses `.keyword` |
| `sc_bytes` / `sc_content_len` | `long` | sum aggs |
| `cs_method` / `cs_protocol` / `x_edge_result_type` / `ssl_protocol` / `bot_category` | enum strings → `text` + `.keyword` | terms aggs use `.keyword` |
| `cs_host` / `cs_uri_stem` / `cs_user_agent` / `cs_referer` / `c_country` | strings → `text` + `.keyword` | terms aggs use `.keyword` |
| `is_bot` / `cache_hit` | `boolean` | filters + ratios |
| `source_etag` | `keyword` | join back to inventory by id |
| `source_key` / `source_bucket` | `keyword` | per-file aggregations (was slice 1's responsibility but useful here too) |
| `pipeline_run_id` / `loaded_at` / `schema_version` | as in slice 1 | |

Slice 2 will probably want an explicit index template eventually — the
auto-mapping rule about `.keyword` for terms aggs is a known footgun.
Explicit template is listed in slice 1's "open follow-ups" and could be
shared between slices.  Out of scope for slice 2 first cut.

---

## "CloudFront Logs - Events Overview" — proposed panels

Six panels for the first cut.  Same 2x2 + full-width-row layout as slice 1
plus one extra row.  All Vis Editor (NOT Lens) — same migration-safety
reasoning as slice 1.

| # | Panel | Type | Aggregation | Operational signal |
|---|-------|------|-------------|--------------------|
| 1 | Status code distribution over time | stacked vertical bar | `count()` over `date_histogram(timestamp, hourly)`, split by `terms(sc_status_class.keyword)` | "any 5xx spike?" / "did the 4xx ratio change?" |
| 2 | Edge result type breakdown | donut | `terms(x_edge_result_type.keyword)` | "what fraction of requests hit cache vs origin vs Functions?" |
| 3 | Top URIs by request count | horizontal bar | `terms(cs_uri_stem.keyword, top 25)` | "what's getting hammered?" |
| 4 | Geographic distribution | donut | `terms(c_country.keyword, top 20)` | "where's the traffic from?" |
| 5 | Time-taken percentiles over time | line | `percentiles(time_taken_ms, [50, 95, 99])` over `date_histogram(timestamp, hourly)` | "p99 latency drift" |
| 6 | Bot vs human ratio over time | stacked bar | `count()` over `date_histogram(timestamp, hourly)`, split by `terms(bot_category.keyword)` | "what % of traffic is bots?" |

Layout (48-column canvas):
```
+--------+--------+
|   1    |   2    |
+--------+--------+
|   3    |   4    |
+--------+--------+
|   5    |   6    |
+--------+--------+
```

Three rows of two panels, each 24w × 12h.

Bonus panels deferred to slice 2.5 (or user adds via Lens):
- Cache hit ratio over time (line, `cache_hit:true / total`)
- Origin latency vs total time (overlapping line)
- HTTP method distribution (donut)
- 4xx/5xx by URI (table)

---

## Doc identity (recap from §01)

`_id = "{source_etag}__{line_index}"` — etag of the .gz file plus 0-based
line number within it.  Properties:

- Same `.gz` re-fetched → same `_id` → ES updates in place
- Different `.gz` files → different etag → different `_id`, no collision
- `source_etag` also a separate field on the doc → join back to inventory
  by terms(source_etag) → can answer "which .gz files generated more than
  N events?" easily

---

## Inventory cross-link

The events loader updates inventory docs:

```
POST /sg-cf-inventory-*/_update_by_query?refresh=true
{
  "query": { "term": { "etag": "<the-file-etag>" } },
  "script": {
    "lang": "painless",
    "source": "ctx._source.content_processed = true; ctx._source.content_extract_run_id = params.run_id;",
    "params": { "run_id": "20260427T...-cf-realtime-events-load-..." }
  }
}
```

Done once per file processed (not per event).  Cheap.

The inventory's `health` check (slice 1) gains a complementary "events
coverage" view via the events `health` check's `inventory-link` row:
"X of Y inventory docs have content_processed=true".

---

## Pipeline-events index — still deferred

Same as slice 1: no `lets-pipeline-events` operational index in slice 2.
Loader summary lives in the response only.  When a Save layer ships
(slice 3+), the `pipeline_run_id` becomes the join key into a richer
operational store.
