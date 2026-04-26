# Brief: `sp el lets cf events` — second LETS slice (content reads)

**Version:** v0.1.100
**Date:** 2026-04-26
**Audience:** Architect (this brief), Dev, QA
**Status:** PROPOSED — nothing described here exists yet

---

## One-paragraph summary

Slice 1 (`sp el lets cf inventory`) gave us listing-metadata of the
CloudFront real-time S3 bucket — Kibana now answers "are logs arriving?"
and "at what cadence?" but cannot answer "what's actually in them?".  Slice
2 reads each `.gz` via S3 GetObject, gunzips in memory, parses the TSV into
`Schema__CF__Event__Record`, applies a minimal Stage 1 cleaning module
(URL-decode, bot classification), and bulk-posts to a separate `sg-cf-events-*`
index family with its own dashboard.  Per-event idempotency: `_id =
{etag}__{line_index}`.  Per-file lineage: each successfully-parsed file
flips its inventory doc's `content_processed: true` (the slice-1 hook
finally pays off).

---

## File index

| File | Purpose |
|------|---------|
| `README.md` *(this file)* | Status, summary, decisions, file index |
| [`01__principle-and-stages.md`](01__principle-and-stages.md) | LETS mapping for events; what changes vs slice 1 |
| [`02__cli-surface.md`](02__cli-surface.md) | Four verbs, the `--from-inventory` manifest pattern |
| [`03__schemas-and-modules.md`](03__schemas-and-modules.md) | Schema__CF__Event__Record (~25 fields), module tree |
| [`04__elastic-and-dashboard.md`](04__elastic-and-dashboard.md) | Index naming, mapping, ~6-panel dashboard |
| [`05__acceptance-and-out-of-scope.md`](05__acceptance-and-out-of-scope.md) | Acceptance criteria, non-goals, slice 3 sketch |
| [`06__implementation-phases.md`](06__implementation-phases.md) | 7 PR-sized phases for Dev pickup |

---

## Key decisions for sign-off

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Separate command tree** — `sp el lets cf events {load,wipe,list,health}`, not a flag on `inventory` | Per the user's call: separate commands, separate index, separate dashboards.  Slice 1 stays as the inventory-only baseline. |
| 2 | **Separate index family** — `sg-cf-events-{YYYY-MM-DD}`, parallel to `sg-cf-inventory-{YYYY-MM-DD}` | Different schema, different cardinality (~100x more docs per day), different lifecycle (events get rolled up first). |
| 3 | **Separate dashboard** — `sg-cf-events-overview` saved-object id | Different panels (status codes, geography, edge result types, cache hit ratio). |
| 4 | **`_id = {etag}__{line_index}`** | Per-line uniqueness within a file + per-file dedup across loads.  Same etag-as-id idempotency property as slice 1, extended to line granularity. |
| 5 | **Update inventory `content_processed` after each file** | The slice-1 hook (`Schema__S3__Object__Record.content_processed`) finally has a writer.  Slice 2 doc consumes the inventory manifest. |
| 6 | **`--from-inventory` flag on `load`** — work-queue mode | Iterate inventory docs where `content_processed=false` instead of re-listing S3.  Pays off the manifest pattern. |
| 7 | **Stage 1 cleaning is real this time but minimal** | URL-decode `cs_user_agent`; trim `cs_referer` to host-only; classify bots via UA regex.  No PII redaction needed (the realtime-log config already pre-stripped `c-ip` / `cs-cookie` / `cs-uri-query`). |
| 8 | **Brief location** — `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/` | Mirrors v0.1.99 split-folder convention. |

---

## What's NOT in slice 2 (deferred)

- Full PII redaction module (would only have work to do on a different
  source whose realtime-log config doesn't pre-strip)
- LETS Save layer (manifest.json + dashboard screenshot to S3 vault)
- FastAPI duality (Typer-only for now, same as slice 1)
- Lens-based dashboard panels (Vis Editor for the auto-imported one;
  hand-built Lens dashboards layered on top via `sp el dashboard import`)
- Aggregation-level rollups (let Kibana query-time aggregations handle it
  until cardinality becomes a problem)

---

## Cross-references

- Slice 1 brief — `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/`
- Slice 1 debrief — `team/claude/debriefs/2026-04-26__lets-cf-inventory__{01-why,02-what,03-how-to-use}.md`
- LETS doctrine — captured inline in slice 1's `01__principle-and-stages.md`
- Existing module to extend — `sgraph_ai_service_playwright__cli/elastic/lets/cf/`
  (slice 2 adds a sibling `events/` subpackage to slice 1's `inventory/`)

---

## Status updates

| Date | Note |
|------|------|
| 2026-04-26 | Brief filed.  No code written.  Awaiting sign-off + Dev pickup. |
