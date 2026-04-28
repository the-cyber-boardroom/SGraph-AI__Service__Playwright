# 06 — Implementation Phases

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

This is the most-read doc in the brief — the Sonnet session uses it as their day-by-day work plan.

---

## Purpose of this doc

Six PR-sized phases. Each ends with a green test suite or a working demo. Each is independently shippable. Total estimated effort ≈ 6–7 days for a single Dev.

Mirror the structure of slice 2's `06__implementation-phases.md`: side-effect analysis table at the top, then per-phase **Builds / Files / Tests / Demo / Blocks / Effort**.

---

## Sections to include

### 1. Side-effect analysis (table at the top)

What changes vs additive-only across the codebase:

| Area | Action | Verdict |
|------|--------|---------|
| `scripts/elastic_lets.py` | +N lines for `consolidate_app` mount + 5 typer commands | Additive only |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/` *(new subpackage)* | All new | All new |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/` (slice 1) | **Unchanged** | Unchanged |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Events__Loader.py` | +N lines for `--from-consolidated` queue mode (decision #8) | Additive only |
| `Schema__S3__Object__Record` | Two new fields with backward-compat defaults (decision #7) | Additive only |
| `Enum__Pipeline__Verb` | One new enum value `CONSOLIDATE` | Additive only |
| `Inventory__HTTP__Client` | New optional parameters (E-1, E-2, E-5); keep-alive (E-3); terms-filter `_update_by_query` (E-6); body-size auto-split (E-5) — all backward compatible | Additive only — defaults preserve current behaviour |
| Existing 351 tests | Untouched — stay green | Green |

### 2. Phase 1 — Type_Safe foundations (1 day)

**Builds:** all enums, primitives, schemas, collections from `03__schemas-and-modules.md`. Zero I/O.

**Files:** ~25 new `.py` files under `sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/{enums,primitives,schemas,collections}/`. Plus the two new fields on `Schema__S3__Object__Record` and the new `CONSOLIDATE` value on `Enum__Pipeline__Verb`.

**Tests:** one test file per class. Construction with valid + invalid inputs. Round-trip `.json()`.

**Demo:** `pytest tests/unit/.../consolidate/` green. No CLI.

**Blocks:** every later phase imports from here.

**Effort:** 1 day.

### 3. Phase 2 — S3 write boundary + Inventory__HTTP__Client optimisations (1.5 days)

**Builds:**
- `S3__Object__Writer` (new boto3 boundary) + `S3__Object__Writer__In_Memory`
- `Inventory__HTTP__Client` gains optional `refresh`, `routing`, `max_bytes` parameters (E-1, E-2, E-5)
- `Inventory__HTTP__Client` gains a `requests.Session()` for keep-alive (E-3)
- `Inventory__HTTP__Client` gains a terms-filter `_update_by_query` path (E-6)

**Files:** 2 new service files (`S3__Object__Writer` + In_Memory) + 1 modified existing class (`Inventory__HTTP__Client`).

**Tests:**
- `S3__Object__Writer` round-trips bytes through the In_Memory subclass
- `S3__Object__Writer` surfaces `ClientError` as a Type_Safe error response (no raw boto3 exceptions leak)
- `Inventory__HTTP__Client` defaults preserve all existing behaviour (~10 new assertions)
- New optional params route through correctly (refresh=False shows up in URL; routing= shows up in URL)
- All existing 351 tests still green without modification

**Demo:** `pytest` green. Existing tests unchanged.

**Blocks:** Phase 3 (NDJSON writer uses S3 writer); Phase 4 (loader uses optimised HTTP client).

**Effort:** 1.5 days. The bulk-post body-size auto-split (E-5) is the trickiest single change — handles the boundary case where one doc is bigger than the cap (must not split mid-doc).

### 4. Phase 3 — NDJSON consolidation core + lets-config read/write (1 day)

**Builds:**
- `NDJSON__Writer` — `List__Schema__CF__Event__Record` → gzipped NDJSON bytes
- `NDJSON__Reader` — gzipped NDJSON bytes → `List__Schema__CF__Event__Record`
- `Manifest__Builder` — assembles `Schema__Consolidated__Manifest` from a run
- `Lets__Config__Reader` — validates a compat-region's `lets-config.json`, refuses incompatible regions (decision #5b)
- `Lets__Config__Writer` — writes `lets-config.json` at first use of a region

**Files:** 5 service files + 5 test files.

**Tests:**
- Round-trip a `List` of records → ndjson.gz bytes → identical `List` back
- Manifest carries source_etags + parser_version + event_count
- `Lets__Config__Reader` accepts a compatible region
- `Lets__Config__Reader` rejects an incompatible region with a typed error (parser_version mismatch, schema_version mismatch, …)
- `Lets__Config__Writer` produces the JSON shape from the README example exactly

**Demo:** `pytest` green.

**Blocks:** Phase 4 (loader uses all of these).

**Effort:** 1 day.

### 5. Phase 4 — Consolidate__Loader orchestrator (1.5 days)

**Builds:**
- `Consolidate__Loader` — pure logic, all collaborators injected
- `Consolidate__Wiper` — matched-pair wipe (S3 sidecar + ES index + dataview + dashboard + inventory flag reset)
- `Consolidate__Verifier` — drift / mismatch detection

**Loader flow:**
1. Resolve stack, run_id
2. Read or create `lets-config.json` at compat-region root (Phase 3 classes)
3. Read inventory manifest for the date where `consolidation_run_id` is empty
4. Loop: fetch each source `.gz` via `S3__Object__Fetcher`, parse via `CF__Realtime__Log__Parser`, accumulate into `List__Schema__CF__Event__Record`
5. Write `events.ndjson.gz` via `S3__Object__Writer` (Phase 3 NDJSON__Writer)
6. Write `manifest.json` sidecar via `S3__Object__Writer`
7. Index manifest doc into `sg-cf-consolidated-{date}` (with `refresh=False` — E-1)
8. `_update_by_query` flips `consolidation_run_id` on every source inventory doc — single call with `terms` filter (E-6)
9. Record one `Schema__Pipeline__Run` with verb `CONSOLIDATE`

**Tests:**
- Full happy path with in-memory collaborators
- Partial-failure path (one source `.gz` unfetchable — verify journal records the failure)
- Re-run-same-day-same-parser is byte-identical
- Re-run-same-day-newer-parser produces a sibling artefact (new compat region created)
- `Wiper` is matched and idempotent (run wipe twice, second is no-op)

**Demo:** `pytest` green; ~30+ unit tests for the loader/wiper alone.

**Blocks:** Phase 5 (events load uses the consolidated artefact).

**Effort:** 1.5 days. This is the densest phase — Sonnet may correctly want to split it in half (loader only first, then wiper+verifier). If they propose this, agree.

### 6. Phase 5 — events load --from-consolidated mode (1 day)

**Builds:** `Events__Loader` gains a third queue-build mode.

**Loader flow for `--from-consolidated`:**
1. Resolve consolidated manifest from S3 for the date
2. Read `lets-config.json` first; refuse incompat region with a clear error
3. Read NDJSON via `NDJSON__Reader` (Phase 3)
4. Bulk-post ONE call to `sg-cf-events-{date}` (with `refresh=False` + `routing={date}` — E-1, E-2)
5. Flip inventory `content_processed` for every source etag in the manifest in a single `_update_by_query` (E-6)

**Tests:**
- `--from-consolidated` reads Phase 4's output and produces the same `sg-cf-events-{date}` state as the per-file path
- Error if no consolidation manifest for the date
- Error if the compat region is incompatible (parser_version drift)

**Demo:** `pytest` green. Wall-time on a 21-file day < 0.5 second (vs ~9 sec today).

**Blocks:** Phase 6 (CLI surfaces this).

**Effort:** 1 day.

### 7. Phase 6 — CLI commands + dashboard + reality doc (0.5–1 day)

**Builds:**
- `scripts/elastic_lets.py`: `sp el lets cf consolidate {load,wipe,list,health,verify}`
- `Consolidated__Dashboard__Builder` (1 panel: "Consolidation runs over time")
- `team/roles/librarian/reality/v0.1.31/12__lets-cf-consolidate.md` (reality doc update)
- Final canonical version of this `06__implementation-phases.md` (updates this file)

**Demo:** end-to-end against a real Ephemeral Kibana stack:

```
sp el create-from-ami --wait
sp el lets cf inventory load
sp el lets cf consolidate load
sp el lets cf events load --from-consolidated
# Confirm sg-cf-events-2026-04-27 has the same doc count as the old path
sp el lets cf consolidate verify 2026-04-27
# Confirm no drift reported
sp el lets cf consolidate wipe 2026-04-27
sp el lets cf events load --from-consolidated
# Confirm clean error: "no consolidation manifest for date"
```

**Blocks:** PR ready for Architect review and merge.

**Effort:** 0.5–1 day depending on reality-doc thoroughness.

### 8. Phase 0 reminder

Phase 0 (this docs-expansion task) precedes Phase 1. Until docs 01–10 are Architect-approved, no code is written.

---

## Source material

- README §"Implementation phase outline" (the skeleton this doc expands)
- Slice 2 brief: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/06__implementation-phases.md` — closest analogue, mirror its shape
- Slice 1 brief: same file in v0.1.99 — slightly simpler, but useful comparison

---

## Target length

~220–280 lines, matching slice 2's `06__implementation-phases.md` (which is the longest doc in slice 2's brief).
