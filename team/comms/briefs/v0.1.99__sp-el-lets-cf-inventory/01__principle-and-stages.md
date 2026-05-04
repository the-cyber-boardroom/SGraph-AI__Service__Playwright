# 01 — Principle and stage mapping

## Design principle

Following the LETS architecture (Dinis Cruz / ChatGPT Deep Research):

> **Persist Everything Important BEFORE Indexing Anything.**
> Elasticsearch is NOT the source of truth.  It is an index, a cache, a
> search layer, a visualisation layer.  The authoritative system is the
> object store.

For this slice, that principle has two consequences:

1. **The `cloudfront-realtime/` S3 bucket IS the Load layer.** AWS Firehose
   has been writing immutable, gzipped, date-partitioned objects there for
   weeks.  The slice does not re-copy or re-format them.  It treats the
   bucket as already-canonical raw input.
2. **The data inside Kibana is throwaway by design.** Every `load` has a
   matched `wipe`.  Either the index is rebuilt from S3 (re-run `load`) or
   the entire stack is rebuilt from an AMI (`sp el create-from-ami`) and
   then `load` is re-run.  No state lives only in Kibana.

The two together mean **slice 1 has no durable artifacts of its own.** S3
holds the canonical raw; Elastic holds the working copy; that's it. Slice 2
will introduce a Save layer that snapshots Kibana dashboards back to S3.

---

## LETS stages ↔ v0.22.18 brief stages

The v0.22.18 brief enumerates Stage 0–6.  LETS enumerates Load / Extract /
Transform / Save.  They are the same idea, two vocabularies; the table
reconciles them and pins which are *in scope* for this slice.

| LETS | v0.22.18 stage | Slice 1 status | Notes |
|------|----------------|----------------|-------|
| **Load** | Stage 0 — raw capture | ✅ already done by AWS | Firehose → S3, no work needed |
| (boundary) | Stage 1 — security cleaning | ⚪ no-op for this source | The realtime-log config has already pre-stripped `c-ip`, `x-forwarded-for`, cookies.  Nothing PII-bearing remains in the listing metadata.  Stage 1 gets a labelled passthrough. |
| **Extract** | Stage 2 — structured extraction | 🟡 in scope | S3 ListObjectsV2 response → typed `Schema__S3__Object__Record` in memory.  Key path → derived delivery date/hour/minute. |
| **Transform** | Stage 3 — signal reduction | ❌ deferred | Kibana's own aggregation handles per-hour/per-day rollups at query time for slice 1. Add explicit Transform when query cost becomes a problem. |
| (Index) | Stage 4 — load into Kibana | 🟡 in scope | `Elastic__HTTP__Client.bulk_post()` + `Kibana__Saved_Objects__Client.ensure_data_view()`.  Both already exist. |
| (Explore) | Stage 5 — Kibana usage | 🟡 in scope (one dashboard) | "CloudFront Logs - Inventory Overview" with 5 panels.  See `04__elastic-and-dashboard.md`. |
| **Save** | Stage 6 — screenshot to vault | ❌ deferred | The Save layer (artifacts → S3 vault) is slice 2.  Slice 1 lives entirely in memory + Elastic. |

The brief criterion #9 ("re-runnable from any stage's output") and #10
("Stages 0–3 must survive the destruction of any Elastic instance") are
both honoured: every doc in Elastic is a deterministic function of the S3
listing, so destroying Elastic is recoverable by re-running `load`.

---

## Why metadata-only on slice 1

Three reasons the *first* pass uses listing metadata only and never fetches
a `.gz`:

1. **Cost shape is different.** ListObjectsV2 is one paginated call per
   1,000 objects; GetObject is one round-trip per file.  For ~375 files/day
   the listing fits in one or two pages and no GetObject calls are needed.
2. **Stage 1 has no real work to do on metadata.** `c-ip` and `x-forwarded-for`
   live inside the `.gz` content; the listing surface is already PII-free.
   This lets us defer the cleaning module to slice 2 without faking it.
3. **The inventory itself is a useful manifest.** Once the inventory is in
   Elastic with a `content_processed` flag, slice 2 can iterate that manifest
   instead of re-listing S3 to decide what to fetch.  The manifest pays for
   itself even before slice 2 ships.

---

## What "Load" produces from the listing alone

For every object the S3 ListObjectsV2 response gives us:

- `Key` (full S3 key, includes the `cloudfront-realtime/YYYY/MM/DD/` prefix)
- `LastModified` (when Firehose flushed this batch — buffer-time threshold)
- `Size` (gzipped bytes)
- `ETag` (md5 of the object body)
- `StorageClass` (initially `STANDARD`)

From the **filename** we can derive (Firehose embeds the timestamp):

```
sgraph-send-cf-logs-to-s3-2-2026-04-25-00-00-20-e71885f4-7b8c-4d4f-a930-...gz
                            ^^^^^^^^^^^^^^^^^^^
                            delivery_year/month/day/hour/minute/second (UTC)
```

That gives us minute-level delivery timestamps without parsing any content.
The difference between `LastModified` and the filename timestamp is itself
useful — it's the Firehose buffer flush latency.
