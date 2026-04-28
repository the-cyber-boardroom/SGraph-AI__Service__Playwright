# 04 — Elastic and Dashboard

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Specify the new `sg-cf-consolidated-{date}` index family, its mapping, the data view, and the 1-panel dashboard. Mirror slice 2's `04__elastic-and-dashboard.md`.

---

## Sections to include

1. **Index naming** — `sg-cf-consolidated-{YYYY-MM-DD}`. One index per day, keyed on `consolidated_at[:10]`. Aligns with the existing `sg-cf-{inventory,events}-{date}` family.

2. **Index mapping** — explicit mapping for `Schema__Consolidated__Manifest`:
   - `run_id` (keyword)
   - `consolidated_at` (date) — index time field
   - `started_at`, `finished_at` (date)
   - `source_etags` (keyword)
   - `source_count`, `event_count`, `byte_count_input`, `byte_count_output` (long)
   - `compression_ratio` (float)
   - `parser_version`, `bot_classifier_version`, `consolidator_version` (keyword)
   - `s3_output_bucket`, `s3_output_key`, `s3_manifest_key` (keyword)
   - `compat_region` (keyword)

   Pre-create the index template (decision E-4 from the README) so auto-mapping doesn't kick in. Avoids the `.keyword` footgun documented in slice 2's reality doc.

3. **Data view** — `sg-cf-consolidated-*`, time field `consolidated_at`. Saved-object id deterministic so re-imports overwrite cleanly.

4. **Dashboard — "Consolidation runs over time"** — one panel:

   ```
   ┌─────────────────────────────────────────────────────────┐
   │  Consolidation runs over time                           │
   │  ─────────────────────────────                          │
   │  X-axis: consolidated_at (date histogram, daily bucket) │
   │  Y-axis-1: source_count (bar)                           │
   │  Y-axis-2: event_count (line, secondary axis)           │
   │  Tooltip: parser_version, run_id                        │
   └─────────────────────────────────────────────────────────┘
   ```

   Saved-object id: `sg-cf-consolidated-overview` (deterministic).

   Future panels (out of scope for v1): compression ratio over time, byte savings vs source, run duration trend.

5. **Dashboard auto-import on `consolidate load`** — same pattern as slices 1/2: builder class generates the ndjson, `Inventory__HTTP__Client` posts it to `/api/saved_objects/_import`. Hand-rolled `visualization` saved-object type (not Lens) — same reason as slice 2 (Lens has migration hooks that 500 on hand-rolled ndjson).

6. **Wipe** — 4-step matched pair:
   1. Delete every `sg-cf-consolidated-*` index by name (wildcard DELETE blocked by ES `action.destructive_requires_name=true`)
   2. Delete data view `sg-cf-consolidated-*`
   3. Delete dashboard saved-object + the 1 visualisation saved-object
   4. **`_update_by_query`** with `terms` filter — flips every `consolidation_run_id` back to empty in inventory, scoped to the source-etag list from the manifests being deleted (decision E-6 from §"Elastic optimisations")

7. **The S3 sidecar wipe** — separate from ES wipe. Deletes the `manifest.json` and `events.ndjson.gz` for the date subtree. The `lets-config.json` at the compat-region root is NOT deleted (decision #10).

8. **Health checks** (4):
   - Index template exists (`sg-cf-consolidated`)
   - Data view exists
   - Dashboard exists
   - Most recent run < 24h ago (warning if older, not failure)

---

## Source material

- README §"Architect's locked decisions" #6, #10, and §"Elastic optimisations"
- Slice 2 brief: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/04__elastic-and-dashboard.md` for shape
- Slice 2 reality doc on the `.keyword` mapping issue

---

## Target length

~100–120 lines, matching slice 2's `04__elastic-and-dashboard.md`.
