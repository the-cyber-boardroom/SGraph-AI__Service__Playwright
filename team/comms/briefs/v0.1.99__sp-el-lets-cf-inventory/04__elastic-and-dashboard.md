# 04 — Elastic, Kibana, and the dashboard

## Naming convention

Mirrors the existing synthetic-data convention (`sg-synthetic`,
"Synthetic Logs Overview"), prefixed `sg-cf-inventory` so the two datasets
coexist in one Kibana without collisions.

| Artifact | Name | Notes |
|----------|------|-------|
| Index template | `sg-cf-inventory-template` | Matches `sg-cf-inventory-*`.  Defines the mapping for `Schema__S3__Object__Record`. |
| Index | `sg-cf-inventory-{YYYY-MM-DD}` | Daily rolling index keyed on `delivery_at`.  Cheap to drop one day. |
| Data view | `sg-cf-inventory` | Pattern `sg-cf-inventory-*`, time field `delivery_at`. |
| Dashboard | `CloudFront Logs - Inventory Overview` | Saved-object id `sg-cf-inventory-overview`. |
| Visualisations | `sg-cf-inv-vis-{slug}` | Deterministic ids per panel for idempotent re-import. |

The deterministic-id pattern is taken straight from the existing synthetic
dashboard work (debrief `02__what.md`, "Default 4-panel dashboard" section).

---

## Index mapping (slice 1)

Generated at `ensure_index_template` time; the mapping is the type-projected
form of `Schema__S3__Object__Record`.

Key fields and their ES types:

| Field | ES type | Reason |
|-------|---------|--------|
| `bucket` | `keyword` | exact-match aggregations |
| `key` | `keyword` (+ `text` sub-field for free search) | top-prefix terms aggregation |
| `last_modified` | `date` | when Firehose flushed |
| `delivery_at` | `date` | dashboard time field |
| `size_bytes` | `long` | sum / histogram |
| `etag` | `keyword` | also the `_id` |
| `storage_class` | `keyword` | terms agg |
| `source` | `keyword` | will gain values when slice 2 brings new sources |
| `delivery_year`/`month`/`day`/`hour`/`minute` | `integer` | flat aggregations |
| `firehose_lag_ms` | `long` | percentile aggs |
| `pipeline_run_id` | `keyword` | per-run filter in Discover |
| `loaded_at` | `date` | "when did we last refresh" filter |
| `schema_version` | `keyword` | mapping evolution audit |
| `content_processed` | `boolean` | slice 2 selector |
| `content_extract_run_id` | `keyword` | slice 2 lineage |

---

## "CloudFront Logs - Inventory Overview" — the 5 panels

Built programmatically by `CF__Inventory__Dashboard__Builder`, mirroring the
existing `Default__Dashboard__Generator` for synthetic data.  Legacy
`visualization` saved-object type (the debrief warned us off Lens).

| # | Panel title | Type | Aggregation | Operational signal |
|---|-------------|------|-------------|--------------------|
| 1 | Object count over time | line | `count()` over `date_histogram(delivery_at, hourly)` | "are logs arriving on schedule?" |
| 2 | Total bytes over time | stacked vertical bar | `sum(size_bytes)` over hourly histogram, split by `terms(delivery_day)` | volume-by-day glance |
| 3 | Object size distribution | histogram | `count()` bucketed on `size_bytes` (log-scale x-axis) | small-file vs big-file mix |
| 4 | Storage class breakdown | donut | `terms(storage_class)` | will become useful when lifecycle policies kick in; today shows STANDARD only |
| 5 | Top hourly partitions | horizontal bar | `terms(delivery_year/month/day/hour)`, top 20 by count | surfaces Firehose buffer behaviour — quiet hours have 1–3 files, busy hours have many |

Everything is answerable from listing metadata alone.  No content panels in
slice 1 (those land with slice 2).

A sixth panel — Firehose flush latency (`firehose_lag_ms` percentiles) —
is a strong candidate but adds a metric aggregation that needs verifying in
Kibana 8.13.4; deferred until slice-1 ships and we can check it against
real data.

---

## Doc identity and re-load semantics

`_id = etag` (S3 ETag is md5 of the object body for non-multipart uploads,
which Firehose uses for these <500 KB objects).  Three consequences:

1. **Idempotent re-loads** — running `load` over an overlapping prefix
   updates docs in place rather than duplicating.
2. **`objects_updated` is meaningful** — bulk response distinguishes
   `created` vs `updated` items; we surface the count.
3. **Slice 2 can update by id** — the content-extract pass updates the
   inventory doc by etag to flip `content_processed=true`.

The trade-off: if Firehose ever rewrites an object with the same content
under a new key, we'd dedupe across keys.  Listing inspection suggests this
doesn't happen (every key is unique), but slice 1 should log and surface
any etag collision rather than silently overwrite.  An alert-style log line
is enough; no recovery code.

---

## Pipeline-events index — *deferred*

The LETS doctrine (§13) recommends operational indices: `lets-pipeline-events`,
`lets-errors`, `lets-stage-metrics`.  These are stage-2 work.  Slice 1 emits
no operational events to Elastic — every per-run summary is in the
`Schema__Inventory__Load__Response` returned to the caller and implicitly
re-derivable from the data index by aggregating on `pipeline_run_id`.

When the Save layer lands (slice 2+), a `lets-pipeline-events` index with
per-stage docs becomes the right home for "what happened during run X"
beyond the docs that run produced.
