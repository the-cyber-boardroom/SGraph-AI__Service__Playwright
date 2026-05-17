# 10 — `sp el lets cf inventory` (LETS slice 1) — 2026-04-26

CloudFront real-time logs LETS pipeline, slice 1 — listing-metadata only.
Layered on top of the v0.1.46 Ephemeral Kibana stack (`sp el`).

> Mirrors the LETS architecture described in `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/`.
> Slice 1 covers the **first vertical pass**: Load → Extract → (skip Transform)
> → Index → (Save: dashboard imported into Kibana).  No content reads from
> the `.gz` files — that is slice 2.

---

## CLI surface — added under `sp el`

```
sp el lets cf inventory load   [--prefix YYYY[/MM[/DD]]] [--all] [--max-keys N]
                                [--run-id ID] [--bucket B] [--password P]
                                [--region R] [--dry-run]
sp el lets cf inventory wipe   [-y] [--password P] [--region R]
sp el lets cf inventory list   [--top N] [--password P] [--region R]
sp el lets cf inventory health [--password P] [--region R]
```

All four verbs accept an optional positional `[STACK_NAME]`.  Auto-pick when a
single stack exists; prompts on multiple — same convention as other `sp el`
verbs.

---

## Module layout

`sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`

| Layer | Files |
|-------|-------|
| **enums** (3) | `Enum__S3__Storage_Class`, `Enum__LETS__Source__Slug`, `Enum__LETS__Stage` |
| **primitives** (5) | `Safe_Str__S3__Bucket`, `Safe_Str__S3__Key`, `Safe_Str__S3__Key__Prefix`, `Safe_Str__S3__ETag`, `Safe_Str__Pipeline__Run__Id` |
| **schemas** (5) | `Schema__S3__Object__Record` (the indexed doc), `Schema__Inventory__Load__Request`, `Schema__Inventory__Load__Response`, `Schema__Inventory__Wipe__Response`, `Schema__Inventory__Run__Summary` |
| **collections** (2) | `List__Schema__S3__Object__Record`, `List__Schema__Inventory__Run__Summary` |
| **service** (7) | `S3__Inventory__Lister` (boto3 boundary), `Inventory__HTTP__Client` (sibling HTTP boundary, ES bulk + delete + count + aggregate), `Run__Id__Generator`, `Inventory__Loader`, `Inventory__Wiper`, `Inventory__Read`, `CF__Inventory__Dashboard__Builder`, `CF__Inventory__Dashboard__Ids` |

CLI: `scripts/elastic_lets.py` — Typer composition (`lets > cf > inventory`)
mounted onto the parent `sp el` app via 2 lines added to `scripts/elastic.py`.

---

## What the load pipeline does

1. **Resolve** stack via `Elastic__Service.get_stack_info()` (existing) — gets `kibana_url`
2. **List** S3 via `boto3.s3.list_objects_v2` paginator — defaults to today UTC's prefix `cloudfront-realtime/{YYYY}/{MM}/{DD}/`
3. **Parse** each object's filename for the Firehose-embedded timestamp `(YYYY-MM-DD-HH-MM-SS-{uuid}.gz)`
4. **Build** a `Schema__S3__Object__Record` per object — bucket, key, last_modified, size_bytes, storage_class, etag (quotes stripped), source slug, derived delivery_{year/month/day/hour/minute}, derived `delivery_at` ISO, `firehose_lag_ms` (last_modified − delivery_at), `pipeline_run_id`, `loaded_at`, `content_processed: false` (slice-2 hook)
5. **Ensure** the Kibana data view `sg-cf-inventory-*` (idempotent — `Kibana__Saved_Objects__Client.ensure_data_view` reused from synthetic seed)
6. **Build & import** the dashboard ndjson via `CF__Inventory__Dashboard__Builder` — overwrite=true, idempotent
7. **Group** records by `delivery_at[:10]` and **bulk-post** each group to its dated index `sg-cf-inventory-{YYYY-MM-DD}` with `_id = etag` so re-loads dedupe at index time

In-memory pipeline only — no LETS `/raw/` or `/extract/` writes to disk in slice 1.  The S3 bucket is the persisted Load layer.

## What the wipe does (matched pair, idempotent)

1. **Delete** every `sg-cf-inventory-*` index via list-then-delete-by-name
   (wildcard DELETE blocked by ES default `action.destructive_requires_name=true`)
2. **Delete** both data view titles — current `sg-cf-inventory-*` and legacy
   pre-fix `sg-cf-inventory` (defensive, idempotent)
3. **Delete** dashboard saved-object `sg-cf-inventory-overview` + the 5
   visualisation saved-objects (deterministic ids from
   `CF__Inventory__Dashboard__Ids`)

## Indices, data view, dashboard

| Artifact | Name |
|----------|------|
| Index | `sg-cf-inventory-{YYYY-MM-DD}` (daily rolling, keyed on `delivery_at`) |
| Data view | `sg-cf-inventory-*` (wildcard pattern, time field `delivery_at`) |
| Dashboard | `CloudFront Logs - Inventory Overview` (id `sg-cf-inventory-overview`) |
| Visualisations (5) | `sg-cf-inv-vis-{count-over-time, bytes-over-time, size-distribution, storage-class-breakdown, top-hourly-partitions}` |

Legacy Vis Editor (`visualization` saved-object type) — Lens deliberately
avoided for the auto-imported path due to migration footguns documented in
the v0.1.46 sp-elastic-kibana debrief.  UI-built Lens dashboards exported
via `sp el dashboard export` and re-imported via `sp el dashboard import`
work fine — the dichotomy is "hand-authored vs UI-authored".

---

## Test coverage

- **150 unit tests** under `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`
- **Zero mocks** — every collaborator has an `*__In_Memory` subclass:
  `S3__Inventory__Lister__In_Memory`, `Inventory__HTTP__Client__In_Memory`,
  reused `Kibana__Saved_Objects__Client__In_Memory` (extended with `find()`
  and `import_objects()` overrides), reused `Elastic__AWS__Client__In_Memory`,
  `Deterministic__Run__Id__Generator`
- **Regression tests against the real HTTP path** — five tests exercise
  `delete_indices_by_pattern` and `count_indices_by_pattern` and
  `aggregate_run_summaries` directly via a `request()` override fed canned
  `Fake__Response` objects.  Caught the wildcard-DELETE bug for the future.

Existing 165 elastic tests stay green — slice 1 modifies one production line
(2 lines if you count the import) in `scripts/elastic.py`, plus additive-only
overrides in two test files.  No existing class touched.

---

## What does NOT exist yet (slice 2+)

- `.gz` content reads — every doc has `content_processed: false`
- Stage 1 cleaning module — the realtime-log config has already pre-stripped
  `c-ip` / `x-forwarded-for` / cookies, so listing metadata is PII-free
- Stage 3 Transform precompute — Kibana's own aggregations handle rollups
- LETS Save layer (manifest + screenshot to vault bucket)
- FastAPI duality — `sp el lets` is Typer-only in slice 1
- Multi-source registry — one source (`cf-realtime`) hardcoded for now