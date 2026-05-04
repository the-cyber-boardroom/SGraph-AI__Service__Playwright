# 2026-04-26 — `sp el lets cf events` (LETS slice 2) — 1 / 3 — Why we built this

This is part one of a three-part debrief on the second LETS slice.

| Part | File |
|------|------|
| 1 — **Why we built this** *(this doc)* | `2026-04-26__lets-cf-events__01-why.md` |
| 2 — What we built | `2026-04-26__lets-cf-events__02-what.md` |
| 3 — How to use it | `2026-04-26__lets-cf-events__03-how-to-use.md` |

---

## The problem

Slice 1 (`sp el lets cf inventory`) shipped earlier the same day and
gave us listing-metadata visibility into the CloudFront real-time S3
bucket — Kibana could answer "are logs arriving?" / "at what cadence?"
/ "any delivery gaps?".  But the *contents* of those `.gz` files —
status codes, edge result types, time-taken, country, user-agents —
were still invisible.  The user's framing was direct:

> *"the content of those gz is what I really want to see (since there
> is real vault in there)"*

Slice 1 had laid the groundwork: every inventory doc carried a
`content_processed: false` flag declared as a forward hook for "the
slice that does the content reads".  Slice 2 is that slice.

## What changes vs slice 1

| Aspect | Slice 1 (inventory) | Slice 2 (events) |
|--------|---------------------|------------------|
| S3 op | `ListObjectsV2` (1 call per 1000 objects) | `GetObject` per file (1:1 with files) |
| Stage 1 | No-op (CloudFront pre-stripped PII) | Real work — URL-decode UA, trim referer, classify bots |
| Index name | `sg-cf-inventory-{YYYY-MM-DD}` | `sg-cf-events-{YYYY-MM-DD}` (separate family) |
| Doc id | `_id = etag` (per file) | `_id = "{etag}__{line_index}"` (per event) |
| Dashboard | 5 panels (file metadata) | 6 panels (status / edge result / URIs / geography / latency / bots) |
| Manifest interaction | Writer of `content_processed: false` | Reader (`--from-inventory` mode) AND writer (flips to true after each file) |

The shapes are deliberately parallel.  Same Type_Safe foundations, same
matched-pair `load`/`wipe`, same read-only `list`/`health`, same
deterministic-id dashboard pattern, same legacy-Vis-Editor (NOT Lens)
auto-imported dashboard.  Slice 2 is the proof that the LETS framework
generalises across sources.

## Why the manifest pattern pays off here

Re-listing S3 every time the user wants to fetch some events is wasteful
and fragile (S3 listing isn't free, and ordering across pages can drift).
The manifest pattern lets the events pipeline iterate the inventory
(which IS in Elastic, fast, queryable) and only fetch what hasn't been
processed yet.

Real workflow that emerges:

```
# Daily refresh (could run from cron / GH Actions / Lambda):
sp el lets cf inventory load                                    # mark new files content_processed=false
sp el lets cf events    load --from-inventory --max-files 100   # process only the new ones
```

After the first day this is incremental — the inventory load adds
~375 new docs; the events load processes them and flips them to
`content_processed=true`.  Tomorrow's run finds only tomorrow's batch.

## Alternative paths considered

| Option | Why it didn't fit |
|--------|-------------------|
| **Combine inventory + events into one verb** | Loses the "Stages 0-3 are throwaway-recoverable" property — if events fails mid-load, you'd lose track of where you got to.  Splitting them gives a real manifest. |
| **Lambda-based stream consumer** | Permanent service.  Anti-thesis of ephemeral cluster.  Same reasoning as slice 1. |
| **Re-list S3 every time** (no manifest) | Wasteful + ordering drift across pages + can't easily express "process only what's new" |
| **Single bulk-post per .gz file (no per-day grouping)** | Loses the daily-rolling-index property.  Multi-day prefix (`--prefix 2026/04/`) would write all events to one index. |
| **Lens dashboard from code** | Hand-rolled Lens NDJSON has migration footguns (slice 1 debrief, also confirmed independently when the user built a Lens dashboard in the UI and round-tripped it via export/import — works because Kibana's exporter writes the right migration metadata; hand-rolled doesn't).  Vis Editor stays the safe choice for code-generated dashboards. |

## What "good" looks like

The slice is "done" when:

- [x] One command loads today's events from S3 into Kibana
- [x] One command wipes everything events-related AND resets the
      inventory manifest so re-runs are clean
- [x] `events load → events wipe -y → events load` returns to
      identical state both times
- [x] `--from-inventory` mode works against the slice-1 manifest;
      the next run after exhausting the queue finds files-queued=0
- [x] The auto-imported dashboard renders 6 populated panels with
      no manual click-through
- [x] Per-event idempotency: re-loading the same `.gz` produces
      `events-updated={total}, events-indexed=0` on the second run
- [x] Test coverage for every service path with no mocks (201 tests)
- [x] No regression in the 165 existing elastic tests OR the 165
      slice-1 LETS tests
- [x] Side-effect surface unchanged from slice 1 (`scripts/elastic.py`
      still has only the +2 lines slice 1 added; slice 2 is purely
      additive to `scripts/elastic_lets.py`)

All boxes ticked.

## Real-world validation during the slice

The user smoke-tested live during phases 4-6 against a real Ephemeral
Kibana stack with real CloudFront logs:

- **Phase 4 smoke**: `events load --prefix cloudfront-realtime/2026/04/25/
  --max-files 50` indexed **565 events from 50 .gz files in 12 seconds**
  (laptop → eu-west-2).  Bot classifier correctly tagged `wpbot/1.4` as
  `BOT_KNOWN`.  Real users on `workspace.sgraph.ai` correctly tagged
  `HUMAN`.
- **Phase 5 (manifest mode)**: After resetting and running `events load
  --from-inventory --max-files 5`, the loader correctly:
  - Detected `queue-mode: from-inventory`
  - Picked the 5 most-recent unprocessed inventory docs (sorted by
    `delivery_at` desc)
  - Indexed 7 events from those 5 files (turned out to be quiet-period
    files with sub-2-event averages)
  - Reported `inventory-flips: 5` — slice 1's `content_processed`
    field had its first real writes
- **Phase 6 (dashboard auto-import)**: every load now imports the
  6-panel events dashboard idempotently.

## Open follow-ups

Things considered and explicitly punted, in rough priority order:

1. **LETS Save layer (slice 3)** — `lets/save/{run_id}/manifest.json`
   + Playwright dashboard screenshot → S3 vault.  Decouples slices 1
   + 2 dashboards from the live Kibana so analysis snapshots survive
   `sp el delete --all`.  Pairs naturally with this slice (which has
   per-run summaries that would benefit from durable archival).

2. **FastAPI duality for `sp el lets`** — mirror every command as an
   HTTP route on `Fast_API__SP__CLI` so the daily refresh recipe
   (inventory load → events load --from-inventory) becomes a
   GitHub-Actions / Lambda cron job rather than a developer task.

3. **Second source** — pick: `agent_mitmproxy` audit log,
   `sgraph-send` app logs, or another CloudFront distribution.
   First chance to refactor the source-specific parser into a
   pluggable interface.  The Type_Safe schema layer is largely
   ready.

4. **Stage 3 — Transform precompute** — when query latency on the
   events index becomes painful (probably at multi-month scale),
   materialise per-minute / per-hour rollup indices.  Currently
   Kibana query-time aggs handle the panels at <565-events scale
   without complaint.

5. **Explicit ES index template** — replace ES auto-mapping with
   an explicit template so field types are visible in code.
   Would have caught the `.keyword` issue at write-time rather than
   in the dashboard render.  Slice 1's open follow-up too —
   shared work between slices.

6. **Per-doc batching across files** — slice 2 bulk-posts per file.
   For very small `.gz` files (avg 2 events) this is wasteful;
   accumulate-then-flush would reduce HTTP overhead.  Defer until
   throughput becomes a concern.

7. **Bot classifier rule loader** — currently hardcoded ~28 named
   bots + 5 generic indicators.  When the list grows past ~50,
   move to a JSON file + reloader.  Out of scope for slice 2.

8. **Lens panels on the auto-import** — UI-built Lens dashboards
   round-trip safely via `dashboard export/import` (proven in slice
   1).  In a future slice we could swap specific panels (treemaps
   are particularly useful) to Lens by exporting from a UI-built
   reference and shipping the JSON as a fixture.

See part 2 for the full inventory and part 3 for the user-facing
recipes.