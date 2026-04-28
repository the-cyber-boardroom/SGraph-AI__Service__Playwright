# 05 — Acceptance Criteria and Out of Scope

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Specify what "done" looks like in measurable, demo-able terms. Capture the deferred items so future readers know what was deliberately left out and why.

---

## Sections to include

### 1. Acceptance criteria — measurable

Each criterion is a binary pass/fail. The Architect signs off only when every line is green.

| # | Criterion | How to verify |
|---|-----------|---------------|
| A-1 | `sp el lets cf consolidate load` completes successfully on a real Ephemeral Kibana stack with a real source date | Manual demo against the live SGraph-Send bucket |
| A-2 | The output `events.ndjson.gz` exists at `s3://.../lets/raw-cf-to-consolidated/{YYYY/MM/DD}/events.ndjson.gz` | `aws s3 ls` after the load |
| A-3 | The `manifest.json` sidecar exists alongside, with correct `source_count`, `event_count`, `parser_version` | `aws s3 cp` and visual inspection |
| A-4 | The `lets-config.json` at the compat-region root exists and validates against `Schema__Lets__Config` | Round-trip through `Lets__Config__Reader` succeeds |
| A-5 | `sp el lets cf events load --from-consolidated` produces the same `sg-cf-events-{date}` doc count as the per-file path | Run both paths against the same date, diff doc counts in ES |
| A-6 | The `--from-consolidated` wall-time on a 21-file day is under 0.5 second | Wall-clock measurement; Step__Timings printout |
| A-7 | Every source inventory doc has `consolidation_run_id` populated after consolidation | ES query for `consolidation_run_id != ""` count == source file count |
| A-8 | `consolidate wipe <date>` removes all consolidated artefacts AND clears the inventory flags AND leaves the source `cloudfront-realtime/` prefix untouched | `aws s3 ls` before/after; ES query for cleared flags |
| A-9 | `consolidate verify <date>` detects an artificially-corrupted manifest (mismatch between manifest.event_count and actual NDJSON line count) | Test with deliberately broken manifest |
| A-10 | `events load --from-consolidated` refuses to read from a compat-incompatible region with a clear error message | Test by manually editing `lets-config.json` to a bumped parser_version |
| A-11 | The 7 ES optimisations (E-1 to E-7) are implemented and individually testable | Tests assert callers pass `refresh=False`, `routing=...`, `terms`-filter `_update_by_query` |
| A-12 | All existing 351 tests pass without modification | `pytest tests/` green |
| A-13 | New tests: ~150–200 unit tests, zero mocks, all green | `pytest tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/` |
| A-14 | Reality doc `team/roles/librarian/reality/v0.1.31/12__lets-cf-consolidate.md` lands in the same PR | Git diff inspection |
| A-15 | The `Pipeline__Runs__Tracker` records one journal doc with verb `CONSOLIDATE` per `consolidate load` | ES query for `verb=CONSOLIDATE` matches run count |

### 2. Out of scope — explicit deferrals

Cross-reference the README §"What's NOT in this slice (deferred)" — restate each item with the deferred-to slice number where known:

| Deferred item | Deferred to | Reason |
|---------------|-------------|--------|
| Append-mode consolidation | v2 of consolidate (TBD) | End-of-day cron makes re-run-the-day acceptable |
| Per-hour granularity | unscheduled | Day-grain is the only path tested in v1 |
| Parquet output | unscheduled | NDJSON.gz only; revisit if columnar reads become a need |
| Multi-source registry | v0.1.103+ | Hardcoded to CF realtime logs; mitm/playwright/MCP are future briefs |
| `SG_Send__Orchestrator` | v0.1.102 | Composes inventory + consolidate + events into one `sync` verb |
| `sp el lets cf runs` (read-side journal CLI) | follow-up after v0.1.102 | Tracker writes happen in this slice; reads are a small subsequent slice |
| 58-occurrence `cloudfront-realtime` literal refactor | unscheduled | Separate slice, separate QA cycle |
| Firehose destination rename | revisit post-orchestrator | AWS-side change, downtime risk |
| Compress / Expand workflow types | v0.1.103+ | Vocabulary in this brief, no implementation |
| Scheduled / triggered execution | v0.1.103+ | Architecture enabled here, code later |
| Parallel S3 fetches | v0.1.102 follow-up | Consolidation removes the per-file count enough that this becomes nice-to-have |
| FastAPI routes | unscheduled | Consistent with `sp el` being CLI-only per v0.1.96 |

### 3. Sketch of v0.1.102 (the orchestrator brief)

Single paragraph. The `SG_Send__Orchestrator` composes `Inventory__Loader` + `Consolidate__Loader` + `Events__Loader` (the new `--from-consolidated` mode) into one `sync` verb. Shares ONE `Call__Counter` across all three. Records ONE `Schema__Pipeline__Run` summarising the whole pipeline. Returns a `Schema__SG_Send__Sync__Response` with all three sub-responses embedded. The `sync` becomes the cron-target / Lambda-target for v0.1.103+.

---

## Source material

- README §"What's NOT in this slice (deferred)"
- README §"Sign-off checklist"
- README §"Trigger model roadmap" (for the v0.1.103+ context)
- Slice 2 brief: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/05__acceptance-and-out-of-scope.md`

---

## Target length

~100–130 lines, matching slice 2's `05__acceptance-and-out-of-scope.md`.
