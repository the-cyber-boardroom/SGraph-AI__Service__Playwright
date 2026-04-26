# 06 — Implementation phases

Seven PR-sized phases.  Each ends with a working demo or a green test
suite.  Total estimated effort ≈ 7 days for a single Dev (slice 1 was
~5 days for comparison; slice 2 is bigger because of the parser + the
content-processed inventory cross-link).

---

## Side-effect analysis

Slice 2 is **purely additive** — extends the existing `lets/cf/`
subpackage with a sibling `events/` folder, no production-source
modifications outside that folder.

| Area | Action | Verdict |
|------|--------|---------|
| `scripts/elastic.py` | **Unchanged** | Slice 1 already mounted the `lets` Typer app |
| `scripts/elastic_lets.py` | +N lines for `events_app` mount + 4 typer commands | Additive only |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/` *(new subpackage)* | All new | All new |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/` (slice 1) | **Unchanged** | Manifest reader/updater are in `events/`, they only call HTTP |
| `Inventory__HTTP__Client` (slice 1) | Reused, NOT modified | `bulk_post_with_id` already accepts any Type_Safe collection |
| `Kibana__Saved_Objects__Client` | Reused, NOT modified | Already has `find` / `import_objects` overrides in In_Memory |
| `Kibana__Saved_Objects__Client__In_Memory` (test) | May need additional method overrides for slice 2 | Additive |
| `Inventory__HTTP__Client__In_Memory` (test) | Gains fixtures for `_search` + `_update_by_query` | Additive |
| Existing 328 elastic tests | Untouched — stay green | Green |

---

## Phase 1 — Type_Safe foundations

**Builds:** all enums, primitives, schemas, collections from
[`03__schemas-and-modules.md`](03__schemas-and-modules.md).  Zero I/O.

**Files:** ~25 new `.py` files under
`sgraph_ai_service_playwright__cli/elastic/lets/cf/events/{enums,primitives,schemas,collections}/`.

**Tests:** one test file per class.  Construction with valid + invalid
inputs.  Round-trip `.json()`.

**Demo:** `pytest tests/unit/.../events/` green.  No CLI.

**Blocks:** every later phase imports from here.

**Effort:** 1 day.

---

## Phase 2 — TSV parser + S3 fetcher + gunzip

**Builds:**
- `S3__Object__Fetcher` (boto3 boundary) + `S3__Object__Fetcher__In_Memory`
- `Gzip__Decoder` (stdlib wrapper, testable seam)
- `CF__Realtime__Log__Parser` — TSV string → `List__Schema__CF__Event__Record`
- `Bot__Classifier` — UA regex → `Enum__CF__Bot__Category`
- `Stage1__Cleaner` — orchestrates URL-decode + referer-trim + bot-classify

**Files:** 5 service files + 1 in-memory subclass + ~5 test files.

**Tests:**
- Parser fixtures from real CF log lines (the user pasted 2 lines earlier
  in the conversation — they're our golden TSV samples)
- Bot classifier against canned UAs (wpbot, bingbot, Mozilla, curl, ...)
- Gzip decoder against a tiny in-memory gzipped string + edge cases
  (empty, truncated, not-gzip)
- Fetcher in-memory subclass round-trips canned bytes

**Demo:** `pytest` green.  `python -c "from CF__Realtime__Log__Parser import parse; print(parse(SAMPLE_TSV))"` shows 2 records with all fields populated.

**Blocks:** Phase 3 (loader uses parser + fetcher).

**Effort:** 1.5 days.  TSV parser is the trickiest single class — handles
"-" placeholders, URL-encoded UAs, optional fields.

---

## Phase 3 — Manifest reader + updater + loader

**Builds:**
- `Inventory__Manifest__Reader.list_unprocessed(top_n)` — `_search` query
  on `sg-cf-inventory-*` for `content_processed=false`
- `Inventory__Manifest__Updater.mark_processed(etag, run_id)` —
  `_update_by_query` on the same index pattern
- `Events__Loader.load(request, base_url, ...)` — orchestrator: queue →
  fetch → parse → clean → bulk-post → manifest update.  Two queue modes
  (S3 list vs from-inventory).

**Files:** 3 new service files + ~3 test files.

**Tests:**
- Manifest reader against in-memory HTTP client returning canned `_search`
  responses
- Manifest updater against in-memory HTTP client
- Loader end-to-end against ALL in-memory subclasses + fixture S3 bytes;
  asserts the fetch → parse → bulk-post → manifest-update sequence

**Demo:** `pytest` green.  No CLI yet.

**Blocks:** Phase 4 (CLI uses loader).

**Effort:** 1.5 days.

---

## Phase 4 — `sp el lets cf events load` CLI

**Builds:**
- `events_app` Typer composition
- 1-line `cf_app.add_typer(events_app, name='events')` in
  `scripts/elastic_lets.py`
- `cmd_events_load` with all the flags from
  [`02__cli-surface.md`](02__cli-surface.md)
- `build_events_loader()` factory

**Files:** ~80 lines added to `scripts/elastic_lets.py`.  No new files.

**Tests:** unit tests for the helper-builder (similar to
`build_inventory_loader`).  CLI subprocess tests skipped (same as slice 1).

**Demo:** `sp el lets cf events --help` and `sp el lets cf events load
--help` render correctly; live `sp el lets cf events load --dry-run`
against a real stack reports "would have processed N files".

**Blocks:** Phase 6 onwards (real load needed for read-side tests).

**Effort:** 0.5 day.

---

## Phase 5 — `events wipe` CLI + service

**Builds:**
- `Events__Wiper.wipe()` — drops events indices + data view + dashboard
  saved-objects + resets `content_processed=true → false` in inventory
- `cmd_events_wipe` in `scripts/elastic_lets.py`

**Files:** 1 new service file + 1 test file + ~30 lines in
`scripts/elastic_lets.py`.

**Tests:** unit tests against in-memory clients; assert all four
delete/reset operations called.

**Demo:** the iteration loop `events load → events wipe -y → events load`
returns identical event count both times.  After wipe, the inventory's
`content_processed` flags are all back to false.

**Effort:** 0.5 day.

---

## Phase 6 — `events list` + `events health` CLI + service + dashboard

**Builds:**
- `Events__Read.list_runs()` and `health()`
- `CF__Events__Dashboard__Builder` — programmatic ndjson, 6 panels (see
  [`04__elastic-and-dashboard.md`](04__elastic-and-dashboard.md))
- `CF__Events__Dashboard__Ids` — shared id constants
- Hook the dashboard import into `Events__Loader.load()` (same pattern
  as slice 1's Phase 5)
- `cmd_events_list` and `cmd_events_health` in `scripts/elastic_lets.py`

**Files:** 3 new service files + ~6 test files + ~80 lines in
`scripts/elastic_lets.py`.

**Tests:**
- `Events__Read` against in-memory clients
- Dashboard builder ndjson shape (mirrors slice 1's tests, plus the
  string-terms-uses-keyword regression test)
- Loader integration: dashboard import called

**Demo:** `events list` shows runs in a Rich table; `events health` shows
4-row status table including the bonus `inventory-link` coverage row;
opening Kibana → Dashboards → "CloudFront Logs - Events Overview" shows
6 populated panels.

**Risk note:** dashboard import is the highest-risk step (Lens migration
footguns).  Vis Editor stays the safe choice.

**Effort:** 1.5 days.

---

## Phase 7 — Smoke + reality + debrief

**Builds:**
- End-to-end smoke test exercising every CLI example from
  [`02__cli-surface.md`](02__cli-surface.md)
- Reality-doc update at `team/roles/librarian/reality/v0.1.31/11__lets-cf-events.md`
- Three-part debrief at `team/claude/debriefs/2026-MM-DD__lets-cf-events__{01-why,02-what,03-how-to-use}.md`
- Update debrief index

**Effort:** 0.5 day.

---

## Sequencing diagram

```
              ┌── Phase 1 (Foundations)
              │
              ├── Phase 2 (Parser + Fetcher)
              │
              ├── Phase 3 (Manifest readers + Loader service)
              │
              ├── Phase 4 (events load CLI)
              │
              ├── Phase 5 (Wiper + wipe CLI) ──┐
              │                                │
              │                                ├── Phase 6 (Read verbs + Dashboard)
              │                                │
              │                                └── Phase 7 (Smoke + reality + debrief)
```

Phases 5 and 6 can run in parallel after Phase 4 lands.

---

## Effort summary

| Phase | Work | Risk |
|-------|------|------|
| 1 — Foundations | 1 day | Low (mechanical) |
| 2 — Parser + Fetcher | 1.5 days | Medium (TSV edge cases) |
| 3 — Loader + Manifest | 1.5 days | Medium (manifest update_by_query) |
| 4 — load CLI | 0.5 day | Low |
| 5 — Wiper + wipe CLI | 0.5 day | Low |
| 6 — Read + Dashboard | 1.5 days | **Highest** (Lens / saved-object footguns) |
| 7 — Smoke + reality + debrief | 0.5 day | Low |
| **Total** | **~7 days** | |
