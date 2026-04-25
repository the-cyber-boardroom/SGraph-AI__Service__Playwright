# Brief: `sp el lets cf inventory` — first LETS slice on Ephemeral Kibana

**Version:** v0.1.99
**Date:** 2026-04-25
**Audience:** Architect (this brief), Dev, QA
**Status:** PROPOSED — nothing described here exists yet

---

## One-paragraph summary

The `sp el` Ephemeral Kibana stack is ready to receive its first real-world
data. CloudFront real-time logs have been landing in
`s3://745506449035--sgraph-send-cf-logs--eu-west-2/cloudfront-realtime/` for
weeks; we have no current visibility into volume, cadence, gaps, or size
distribution.  This slice ships the **first vertical pass of the LETS
pipeline** — `Load → Extract → (skip Transform) → Index → Save` — using only
the S3 listing metadata (no `.gz` content reads).  One command loads today's
inventory into a running Ephemeral Kibana, one command wipes it, and the
matched pair forms the smallest end-to-end demonstration of the LETS
philosophy on this codebase.

---

## File index

| File | Purpose |
|------|---------|
| `README.md` *(this file)* | Status, summary, decisions, file index |
| [`01__principle-and-stages.md`](01__principle-and-stages.md) | LETS principle + Brief stage 0–6 ↔ LETS L/E/T/S mapping |
| [`02__cli-surface.md`](02__cli-surface.md) | Commands, defaults, load/wipe semantics |
| [`03__schemas-and-modules.md`](03__schemas-and-modules.md) | Type_Safe schema list, module layout, service classes |
| [`04__elastic-and-dashboard.md`](04__elastic-and-dashboard.md) | Index naming, data view, dashboard panels |
| [`05__acceptance-and-out-of-scope.md`](05__acceptance-and-out-of-scope.md) | Acceptance criteria, non-goals, slice 2/3 sketch |
| [`06__implementation-phases.md`](06__implementation-phases.md) | Side-effect analysis + 7 PR-sized phases for Dev pickup |

Why split into a folder: the reality doc moved to per-concern files at v0.1.31
for the same reason — easier to edit one section without re-reading the
whole thing, natural review boundary per role.  This is the first cross-role
brief to follow that pattern; if it works the convention can spread.

---

## Decisions pinned in conversation

| # | Question | Decision |
|---|----------|----------|
| 1 | CLI namespace | `sp el lets cf inventory {verb}` — nested under `sp el` since the work is scoped to a stack |
| 2 | First-slice scope | In-memory pipeline.  No `lets/raw/` or `lets/extract/` writes to disk.  S3 bucket is the persisted Load layer; Extract is recomputable. |
| 3 | Data is ephemeral inside Kibana too | Every `load` has a matched `wipe`.  `load → look → wipe → load` is the first-class developer loop. |
| 4 | Default `load` scope | **Today (UTC)** — one day of filenames per run.  Deterministic re-runs match LETS §16. |
| 5 | Per-file processed status | A flag on the inventory doc itself (`content_processed: bool`).  No parallel tracking index.  Single source of truth per file. |
| 6 | Doc identity | `_id = etag` so re-loads over an overlapping prefix overwrite rather than duplicate.  `pipeline_run_id` becomes informational. |
| 7 | Brief location | `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/` (split folder) |

---

## Cross-references

- LETS doctrine — pasted into the v0.22.18 conversation; canonical source TBD
  (probably going into `library/docs/research/`).
- Ephemeral Kibana slice — `team/claude/debriefs/2026-04-25__sp-elastic-kibana__01-why.md`,
  `02-what.md`, `03-how-to-use.md`.
- Existing Type_Safe / boundary rules — `.claude/CLAUDE.md`.
- Existing Elastic CLI module — `sgraph_ai_service_playwright__cli/elastic/`
  (the `sp el` subpackage).  This slice adds a sibling subpackage at
  `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`.

---

## Status updates

| Date | Note |
|------|------|
| 2026-04-25 | Brief filed. No code written. Awaiting architectural sign-off + Dev pickup. |
