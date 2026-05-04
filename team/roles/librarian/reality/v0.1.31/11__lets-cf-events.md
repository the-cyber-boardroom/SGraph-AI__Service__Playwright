# 11 — `sp el lets cf events` (LETS slice 2) — 2026-04-26

CloudFront real-time logs LETS pipeline, slice 2 — content reads with full
TSV parsing, bot classification, per-event indexing.  Layered on top of
slice 1's inventory pipeline and consumes its `content_processed` manifest.

> Mirrors the LETS architecture at `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/`.
> Slice 2 reads the `.gz` files via `s3:GetObject`, gunzips in memory,
> parses TSV → typed records, indexes per-day with `_id =
> {source_etag}__{line_index}` for per-event idempotency, and updates
> slice 1's inventory manifest after each successful file.

---

## CLI surface — added under `sp el lets cf`

```
sp el lets cf events load   [--prefix YYYY[/MM[/DD]]] [--all] [--max-files N]
                             [--from-inventory] [--run-id ID] [--bucket B]
                             [--password P] [--region R] [--dry-run]
sp el lets cf events wipe   [-y] [--password P] [--region R]
sp el lets cf events list   [--top N] [--password P] [--region R]
sp el lets cf events health [--password P] [--region R]
```

Same auto-pick `[STACK_NAME]` convention as slice 1.

`--from-inventory` is the manifest-driven mode: pulls work queue from
`sg-cf-inventory-*` docs where `content_processed=false`.  This is
slice 1's forward-declared field finally having a reader.

---

## Module layout

`sgraph_ai_service_playwright__cli/elastic/lets/cf/events/`

| Layer | Files |
|-------|-------|
| **enums** (6) | `Enum__CF__Method`, `Enum__CF__Protocol`, `Enum__CF__Edge__Result__Type`, `Enum__CF__SSL__Protocol`, `Enum__CF__Status__Class`, `Enum__CF__Bot__Category` |
| **primitives** (9) | `Safe_Str__CF__Country`, `Safe_Str__CF__Edge__Location`, `Safe_Str__CF__Edge__Request__Id`, `Safe_Str__CF__URI__Stem`, `Safe_Str__CF__User__Agent`, `Safe_Str__CF__Referer`, `Safe_Str__CF__Host`, `Safe_Str__CF__Cipher`, `Safe_Str__CF__Content__Type` |
| **schemas** (5) | `Schema__CF__Event__Record` (38 fields = 26 TSV + 4 derived + 5 lineage incl. `doc_id` + 3 pipeline metadata), `Schema__Events__Load__Request`, `Schema__Events__Load__Response`, `Schema__Events__Wipe__Response`, `Schema__Events__Run__Summary` |
| **collections** (2) | `List__Schema__CF__Event__Record`, `List__Schema__Events__Run__Summary` |
| **service** (10) | `S3__Object__Fetcher` (boto3 boundary for GetObject), `Bot__Classifier` (UA → category), `CF__Realtime__Log__Parser` (TSV → records + Stage 1 derivations), `Inventory__Manifest__Reader` (queries slice 1's manifest), `Inventory__Manifest__Updater` (`mark_processed` + `reset_all_processed`), `Events__Loader` (orchestrator), `Events__Wiper` (4-step idempotent reset incl. inventory manifest reset), `Events__Read` (list + health), `CF__Events__Dashboard__Builder` (6-panel ndjson, Vis Editor), `CF__Events__Dashboard__Ids` (shared id constants) |

CLI: `scripts/elastic_lets.py` — slice 2 added the `events` sub-app + 4
typer commands.  `scripts/elastic.py` is unchanged from slice 1
(the `lets` mount line was added then; slice 2 is purely additive to
`scripts/elastic_lets.py`).

---

## What the load pipeline does

1. **Resolve** stack via existing `Elastic__Service.get_stack_info()`
2. **Build queue** (two modes):
   - **S3-listing**: list `cloudfront-realtime/{prefix}/` via slice 1's
     `S3__Inventory__Lister`.  Default mode.
   - **`--from-inventory`**: query `sg-cf-inventory-*` for docs where
     `content_processed=false`, sorted by `delivery_at` desc.  Uses
     the slice-1 manifest as the work queue.
3. **Ensure** Kibana data view `sg-cf-events-*` (idempotent)
4. **Build & import** the dashboard ndjson (idempotent, overwrite=true)
5. **Per file**:
   - `s3:GetObject` → bytes
   - `gzip.decompress` → TSV string
   - `CF__Realtime__Log__Parser.parse()` → `List__Schema__CF__Event__Record`
     + skipped-line count.  Single pass: TSV split + URL-decode UA +
     trim referer + bot classify + status class derive + cache_hit
     flag.
   - Stamp `source_bucket`, `source_key`, `source_etag`, `line_index`,
     `doc_id` (= `{etag}__{idx}`), `pipeline_run_id`, `loaded_at` on
     each record
   - Group records by `timestamp[:10]` → daily-rolling indices
     `sg-cf-events-{YYYY-MM-DD}`
   - Bulk-post each per-day group with `id_field='doc_id'` for
     per-event idempotency
   - On success: `Inventory__Manifest__Updater.mark_processed(etag,
     run_id)` flips the inventory doc's `content_processed=true` and
     stamps `content_extract_run_id`

## What the wipe does (4-step idempotent reset)

1. Delete every `sg-cf-events-*` index (per-name, not wildcard — slice 1's
   bug-fix lesson)
2. Delete the data view `sg-cf-events-*`
3. Delete dashboard `sg-cf-events-overview` + the 6 visualisation
   saved-objects (deterministic ids from `CF__Events__Dashboard__Ids`)
4. **Reset inventory manifest** — `_update_by_query` flips every
   `content_processed=true` back to false so the next `events load
   --from-inventory` finds the full queue again

## Indices, data view, dashboard

| Artifact | Name |
|----------|------|
| Index | `sg-cf-events-{YYYY-MM-DD}` (daily rolling, keyed on each event's `timestamp[:10]`) |
| Data view | `sg-cf-events-*` (wildcard, time field `timestamp`) |
| Dashboard | `CloudFront Logs - Events Overview` (id `sg-cf-events-overview`) |
| Visualisations (6) | `sg-cf-evt-vis-{status-over-time, edge-result, top-uris, geographic, latency-percentiles, bot-vs-human}` |

Vis Editor (`visualization` saved-object type) — Lens deliberately avoided
for the auto-imported path; same migration-safety reasoning as slice 1.
The user has separately proven the round trip with hand-built Lens
dashboards (`sp el dashboard export` → `sp el dashboard import`) on slice 1.

---

## Test coverage

- **201 unit tests** under
  `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/`
- **Zero mocks** — every collaborator has an `*__In_Memory` subclass.
  New ones for slice 2:
  - `S3__Object__Fetcher__In_Memory` (canned bytes per (bucket, key))
  - `Inventory__Manifest__Reader__In_Memory` (canned unprocessed doc list)
  - `Inventory__Manifest__Updater__In_Memory` (records mark/reset calls)
  - `_Recording_HTTP_Client` (subclasses `Inventory__HTTP__Client__In_Memory`
    + adds `request()` override) — used for `Events__Read` health tests
    that need ES `_count` responses
- The user's two real CF log lines (`/enhancecp` and `/robots.txt` from
  the wpbot bot) live as golden fixtures in
  `test_CF__Realtime__Log__Parser.py` — every field of the parsed record
  is asserted.

531 total elastic tests pass (slice 1 untouched at 165, slice 2 at 201,
slice 1 LETS at 165 = wait that doesn't add up.  Actually: slice 1 base
elastic = 165, plus slice 1 LETS = 165, plus slice 2 LETS = 201 = 531
total).

---

## What does NOT exist yet (slice 3+)

- LETS Save layer (manifest + screenshot to S3 vault)
- FastAPI duality for `sp el lets`
- Multi-source registry (events is hardcoded to CloudFront-realtime TSV)
- Stage 3 Transform precompute (rollup indices)
- Explicit ES index template (relies on auto-mapping; the
  `.keyword` rule is a known footgun caught by regression tests)