# 05 — Acceptance, non-goals, and follow-ups

## Acceptance criteria

The slice is "done" when every box ticks against a freshly-launched
ephemeral Kibana stack:

- [ ] **One command loads today's events.** `sp el lets cf events load`
  with no flags fetches today's `.gz` files (resolved to today UTC's
  prefix), parses each TSV, ensures index template + data view +
  dashboard, bulk-posts every event, updates each file's inventory doc
  to `content_processed=true`, prints a Rich summary table.
- [ ] **`--from-inventory` works against the slice 1 manifest.** First
  time picks up every inventory doc with `content_processed=false`;
  second run finds an empty queue (same files, no double-processing).
- [ ] **The events dashboard opens and shows 6 populated panels** at the
  URL the load command printed, with no manual click-through.
- [ ] **Re-running `load` over the same prefix is idempotent.** Second
  invocation reports `events_indexed=0, events_updated={total}` (etag+
  line_index uniqueness collapses duplicates).
- [ ] **`wipe -y` followed by `wipe -y` is idempotent.** Second invocation
  reports `indices_dropped=0, data_views_dropped=0, saved_objects_dropped=0,
  inventory_reset_count=0`.
- [ ] **wipe-and-reload loop is clean.** `load → wipe -y → load` returns
  the same `events_indexed` count both times; the dashboard re-appears
  unchanged; the inventory's `content_processed` flags reset and re-flip.
- [ ] **`--prefix 2026/04` succeeds** (one month, ~10-12k files,
  ~1M events).  Memory stays bounded — the loader processes one file at
  a time, doesn't accumulate the whole month in memory.
- [ ] **Tests cover every service path with no mocks** — at least one
  unit test per service-class method + one regression test per known
  bug pattern (parser edge cases on "-" placeholders, empty/truncated
  gz, malformed TSV row).
- [ ] **Reality doc updated** — new `team/roles/librarian/reality/v0.1.31/11__lets-cf-events.md`
  declares the new commands + module + indices + dashboard exist.
- [ ] **Debrief filed** under `team/claude/debriefs/`, three-part
  convention, with cross-links to slice 1 and to the brief.
- [ ] **Existing 328 elastic tests stay green.**

---

## Non-goals (explicitly out of scope)

1. **Full PII redaction module.** The realtime-log config has already
   pre-stripped `c-ip`, `x-forwarded-for`, `cs-cookie`, `cs-uri-query`.
   Stage 1 in slice 2 is just URL-decode + trim + bot-classify.  Real
   PII work waits for a source whose realtime-log config doesn't
   pre-strip.
2. **Aggregation rollups (Stage 3).** Kibana query-time aggs handle the
   panels.  When p99 panel rendering slows past acceptable, consider a
   per-minute or per-hour rollup index.
3. **LETS Save layer.**  No `/save/{run_id}/` writes in this slice.
   Listed in slice 1's follow-ups; same scope here.
4. **FastAPI duality.**  Typer-only.  HTTP routes for `events` come with
   the FastAPI duality slice (also slice-1 follow-up).
5. **Lens panels in the auto-import.**  Vis Editor for the auto-imported
   dashboard (same migration-safety call as slice 1).  User can layer
   richer Lens dashboards on top via `sp el dashboard import` — that
   round trip is already proven.
6. **Multi-source generalisation.**  This slice is CloudFront-realtime-
   specific.  When slice N ships a second source (mitmproxy, sgraph-send),
   the parser stays per-source but the `Events__Loader` orchestrator
   structure can be the template.
7. **Inventory-doc backfill of events.** When the events index is
   rebuilt from scratch (after wipe), the inventory's
   `content_processed` is reset to `false` for everything by the
   wiper.  No "selectively rebuild only the missing event-doc-id
   ranges" smartness.
8. **Per-file retry.** A file that fails to parse aborts that file
   only — others continue.  No automatic retry queue.  Manual re-run
   handles it (etag-based dedup makes re-runs free).

---

## Open architectural questions

These are pinned for transparency.  All have a default decision; tagging
them so they're easy to revisit.

1. **In-memory vs streaming TSV parse.** The .gz files are tiny (~1.5KB
   compressed, maybe ~10KB uncompressed → ~100 events).  Default:
   in-memory.  When a future source (e.g. nginx access logs) has 100MB
   files, switch to streaming.

2. **Bulk-post batching across files.** Default: bulk-post per file
   (one batch per .gz).  Alternative: accumulate N files' events,
   bulk-post when buffer hits M docs.  In-file batching keeps the
   inventory-update tight (per file, after that file's bulk completes).
   Defer cross-file batching unless throughput becomes a problem.

3. **Inventory update timing.** Default: synchronous after each file
   bulk-post completes successfully.  Alternative: batch-update at
   end-of-run.  Synchronous is more correct (a crash mid-run leaves
   the manifest accurate); batch is faster.  Synchronous wins for
   slice 2's correctness-first stance.

4. **Bot classifier rule source.** Default: hardcoded regex list in
   `Bot__Classifier` (e.g. `wpbot`, `bingbot`, `Googlebot`,
   `crawler`, `spider`, `bot/`, etc.).  When the list grows past
   ~20 entries, move to a JSON file + loader.  Not worth the
   complexity for first cut.

5. **Time-taken precision.** CloudFront reports `time-taken` in
   seconds with 3-decimal precision.  We multiply by 1000 → ms
   integer.  Sub-millisecond precision is lost.  Acceptable —
   percentile dashboards don't care.

---

## Follow-up slices (sketched, not committed)

| Slice | Working title | Adds |
|-------|---------------|------|
| **3** | LETS Save layer | `lets/save/{run_id}/manifest.json` + Playwright dashboard screenshot → S3 vault. Decouples slice-1 / slice-2 dashboards from the live Kibana so analysis snapshots survive `sp el delete --all`. |
| **4** | FastAPI duality for `sp el lets` | Mirror every `sp el lets cf {inventory,events} {load,wipe,list,health}` verb as an HTTP route on `Fast_API__SP__CLI` so daily refreshes can be cron'd from GitHub Actions / Lambda. |
| **5** | Second source — `agent_mitmproxy audit log` | Pick up the existing NDJSON audit log → `sg-mitm-events-*` index, separate dashboard.  First chance to refactor the source-specific parts into a shared base. |
| **6** | Stage 3 — Transform precompute | Per-minute / per-hour rollup index when query latency on slice 2 events index becomes painful (probably at multi-month scale). |
| **7** | Explicit ES index template | Replace ES auto-mapping with an explicit template so field types are visible in code and the `.keyword` rule is enforced at write time.  Shared between inventory + events. |
| **8** | OpenSearch fork | License-clean alternative to Elastic 8.13.4.  ~50-line user-data swap.  Dashboard ndjson would need a re-export.  Same brief slot as the slice-1 follow-up. |
