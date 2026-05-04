# 06 — Implementation phases

Seven PR-sized phases.  Each ends with a working demo or a green test
suite — no half-finished phases on `dev`.  Total estimated effort ≈ 4.5
days for a single Dev.

---

## Side-effect analysis (verified against current code)

The slice touches exactly **one existing file** — `scripts/elastic.py` —
and the touch is one additive line.  Everything else is new.

| Area | Action | Verdict |
|------|--------|---------|
| `scripts/elastic.py` line ~1240 | `app.add_typer(lets_app, name='lets')` — sibling of the existing `ami` / `dashboard` / `data-view` add_typer lines | Additive only |
| `scripts/elastic_lets.py` *(new)* | Typer composition for `lets` and its sub-apps | All new |
| `sgraph_ai_service_playwright__cli/elastic/lets/...` *(new subpackage)* | Service classes, schemas, primitives, enums, collections | All new |
| `Elastic__HTTP__Client`, `Kibana__Saved_Objects__Client`, `Elastic__AWS__Client` | Imported as-is | Unmodified |
| Existing schemas / enums / primitives under `elastic/` | Imported, not modified | Unmodified |
| `scripts/elastic.py` command bodies | Unchanged | Unmodified |
| Existing 165 unit tests | Unchanged — no dependency on new modules | Stay green |
| `pyproject.toml` deps | No new dependencies (boto3, requests, Type_Safe all present) | Unmodified |
| `sp el wipe` semantics | Synthetic-data dataset — independent of `sg-cf-inventory-*` | No collision |
| Kibana saved-objects | `sg-cf-inventory-overview` ≠ `sg-synthetic-overview` | No collision |

> **Correction to brief 03.**  The Typer commands themselves live under
> `scripts/elastic_lets.py`, not under
> `sgraph_ai_service_playwright__cli/elastic/lets/`.  The CLI module holds
> only the Type_Safe schemas + service classes (testable, no Typer / no
> Console).  This matches the existing split between `scripts/elastic.py`
> and `sgraph_ai_service_playwright__cli/elastic/`.

---

## Phase 1 — Type_Safe foundations

**Builds:** all enums, primitives, schemas, collections from
[`03__schemas-and-modules.md`](03__schemas-and-modules.md).  Zero I/O, zero
Typer, zero boto3.

**Files:** ~15 new `.py` files under
`sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/{enums,primitives,schemas,collections}/`.

**Tests:** one test file per schema / enum / primitive / collection.
Construct with valid + invalid inputs.  Round-trip `.json()` ↔ `.from_json()`.

**Demo:** `pytest tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/`
green.  No CLI behaviour yet.

**Blocks:** every later phase imports from here.

---

## Phase 2 — S3 lister + filename parser

**Builds:** `S3__Inventory__Lister` (boto3 boundary), its `__In_Memory`
subclass, and the Firehose-filename → `delivery_at` parser.

**Files:** 2 service files +  1 helper for filename parsing + 2 test files.

**Tests:**
- Unit: in-memory subclass returns canned `ListObjectsV2` page sets;
  parser handles valid + malformed filenames.
- Smoke (gated on AWS credentials): real `ListObjectsV2` against
  `cloudfront-realtime/2026/04/25/` returns ≥1 record with all expected
  fields populated.

**Demo:** `pytest` green; smoke test prints first 3 records to confirm
shape.  No CLI yet.

**Blocks:** Phase 3 (loader uses the lister).

---

## Phase 3 — Loader + `sp el lets cf inventory load`

**Builds:**
- `Inventory__Loader.load()` — orchestrates: list → parse → ensure index
  template + data view → bulk-post.
- `scripts/elastic_lets.py` — Typer composition with `cf` and `inventory`
  sub-apps.
- The single-line registration in `scripts/elastic.py`.

**Files:** 1 new service file + 1 new scripts file + 1-line edit to
existing `scripts/elastic.py`.

**Tests:**
- Unit: `Inventory__Loader` against in-memory S3 + in-memory HTTP client.
  Asserts ensure-template / ensure-data-view / bulk-post calls in the
  right order with the right payloads.
- Smoke (gated on running stack + AWS): `sp el create-from-ami --wait` →
  `sp el lets cf inventory load` → assert N docs at the Kibana URL via
  `_search`.

**Demo:** `sp el lets cf inventory load` against a live stack →
today's CloudFront inventory visible in Kibana **Discover** at
`sg-cf-inventory-*`.  No dashboard yet — that's Phase 5.

**Blocks:** Phase 4 (wipe needs something to wipe), Phase 5
(dashboard ensure plugs into the same load path).

---

## Phase 4 — Wiper + `sp el lets cf inventory wipe`

**Builds:** `Inventory__Wiper.wipe()` + Typer command.

**Files:** 1 new service file + ~30 lines added to
`scripts/elastic_lets.py`.

**Tests:**
- Unit: against an in-memory HTTP client with a fake index + saved-objects
  state.  `wipe()` then `wipe()` produces zero counts the second time.
- Smoke: `load → wipe -y → load` returns identical doc count both passes.
  Confirms idempotency end-to-end.

**Demo:** the iteration loop `load → wipe -y → load` against a live
stack, ~10 seconds total.  Now Phase 5 dev can re-run freely.

**Blocks:** nothing — Phases 5 and 6 can develop in parallel after this.

---

## Phase 5 — Dashboard builder + auto-ensure on `load`

**Builds:**
- `CF__Inventory__Dashboard__Builder` — programmatic ndjson for the 5
  panels from [`04__elastic-and-dashboard.md`](04__elastic-and-dashboard.md).
- Hook into `Inventory__Loader.load()` to call
  `Kibana__Saved_Objects__Client.import_dashboard()` (idempotent) on every
  load.
- Hook into `Inventory__Wiper.wipe()` to remove the dashboard +
  visualisations (current and any legacy IDs).

**Files:** 1 new builder file + small edits to `Inventory__Loader` and
`Inventory__Wiper` from earlier phases.

**Tests:**
- Unit: builder produces deterministic ndjson; same inputs → same bytes.
- Unit: `Inventory__Wiper` removes dashboard + visualisations including
  legacy IDs (mirroring the synthetic-dashboard self-heal pattern).
- Smoke: `load` → open Kibana URL → 5 panels populated.

**Demo:** `sp el lets cf inventory load` → screenshot Kibana →
"CloudFront Logs - Inventory Overview" with 5 populated panels.

**Risk note:** the existing slice's debrief flags this as the highest-risk
area — Lens / saved-object-migration footguns cost real time.  Stick to
legacy `visualization` saved-object type from day one (per Default
Dashboard Generator's pattern).

**Blocks:** nothing.  Phase 6 can ship before this if needed.

---

## Phase 6 — Read verbs (`list` / `show` / `health`)

**Builds:** `Inventory__Read.list() / .show(run_id) / .health()` plus
Typer commands.

**Files:** 1 new service file + ~80 lines added to
`scripts/elastic_lets.py`.

**Tests:**
- Unit: against in-memory HTTP client with canned aggregation responses.
- Smoke: against a live stack with one prior `load`, verify each verb
  returns expected shape.

**Demo:** the full CLI surface from
[`02__cli-surface.md`](02__cli-surface.md) works.

**Blocks:** Phase 7 needs `health` for end-to-end smoke assertions.

---

## Phase 7 — Smoke, librarian, historian

**Builds:**
- End-to-end smoke test that exercises every example in
  [`02__cli-surface.md`](02__cli-surface.md): default `load`, prefixed
  `load`, `--all`, `--max-keys`, `--dry-run`, `wipe`, `list`, `show`,
  `health`.
- Reality-doc update under
  `team/roles/librarian/reality/v0.1.99/{NN}__lets-cf-inventory.md` —
  declares the new module + commands + indices + dashboard exist.
- Debrief at `team/claude/debriefs/2026-MM-DD__lets-cf-inventory__01-why.md`,
  `02-what.md`, `03-how-to-use.md` (single file is also acceptable for a
  smaller slice).
- Backfill commit hashes into the debrief index.

**Demo:** the slice closes per CLAUDE.md rules 26–28.  Reality doc
catches up to v0.1.99 (was stale at v0.1.31).

**Blocks:** nothing — slice ships.

---

## Sequencing diagram

```
              ┌── Phase 1 (Foundations)
              │
              ├── Phase 2 (S3 Lister) ──┐
              │                         │
              ├── Phase 3 (Loader + load) ──┐
              │                             │
              ├── Phase 4 (Wiper + wipe) ───┼── Phase 5 (Dashboard)
              │                             │
              │                             └── Phase 6 (Read verbs)
              │                                          │
              └─────────────── Phase 7 (Smoke + reality + debrief) ──┘
```

Phases 5 and 6 can run in parallel once Phase 4 lands.

---

## Effort estimate (Dev, single-headed)

| Phase | Work | Risk |
|-------|------|------|
| 1 | 0.5 day | Low |
| 2 | 0.5 day | Low |
| 3 | 1 day | Medium — first end-to-end touchpoint |
| 4 | 0.5 day | Low |
| 5 | 1 day | **Highest** — Lens / saved-object footguns |
| 6 | 0.5 day | Low |
| 7 | 0.5 day | Low |
| **Total** | **~4.5 days** | |

If the saved-object work in Phase 5 lands cleanly first try, the slice
ships in ≤4 days.  If it doesn't, expect Phase 5 to consume a second
day and the slice lands at ~5 days.
