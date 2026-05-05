# Reality — Changelog

**Format:** `Date | Domain file(s) updated | One-line description`

This is a pointer log, not a content log. For full delta detail, see the master index for that date in `team/roles/librarian/reviews/MM/DD/` (folder created on first review) or the linked domain `index.md`.

---

## 2026-05-05 (FV2.6 — docker pilot)

- `sg-compute/index.md` — UPDATED: `sg_compute_specs/docker/ui/{card,detail}/v0/v0.1/v0.1.0/` created; 6 files moved from `api_site/plugins/docker/` and `api_site/components/sp-cli/sg-compute-docker-detail/`; detail JS imports rewritten to absolute `/ui/` paths; `admin/index.html` script tags updated to `/api/specs/docker/ui/...`.

---

## 2026-05-05 (BV2.7)

- `sg-compute/index.md` — UPDATED: 14 new canonical modules (primitives, enums, event_bus, image); 46 spec files import-rewritten from `__cli.*` to `sg_compute.*`; CI guard added; 584 tests passing.

---

## 2026-05-05 (BV2.6)

- `sg-compute/index.md` — UPDATED: `Spec__CLI__Loader` + `Cli__Docker` pilot; `sg-compute spec docker <verb>` dispatcher; 19 new tests.

---

## 2026-05-05 (BV2.5)

- `sg_compute/control_plane/routes/Routes__Compute__Nodes.py` — UPDATED: added `POST /api/nodes` (`create_node`)
- `sg_compute/platforms/ec2/EC2__Platform.py` — UPDATED: `create_node` dispatches on `spec_id`; `_create_docker_node` live
- `sg_compute/control_plane/lambda_handler.py` — NEW: Mangum wrapper for Lambda deployment
- `sg_compute__tests/control_plane/test_lambda_handler.py` — NEW: 3 smoke tests. 235 passing.

---

## 2026-05-05 (BV2.2)

- `sg-compute/index.md` — UPDATED: `Section__Sidecar` added to platforms/ec2/user_data/; wired into all 10 spec User_Data__Builder classes (8 template-based, 2 parts-based); PLACEHOLDERS tuples updated; 17 new sidecar tests; 553 passing.

---

## 2026-05-05 (BV2.3)

- `sg-compute/index.md` — UPDATED: BV2.3 pod management added; `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 collections, `Routes__Compute__Pods` (6 endpoints), `Routes__Compute__Nodes` constructor injection. 246 tests passing.

---

## 2026-05-04 (BV2.4)

- `sg_compute/control_plane/routes/Routes__Compute__Nodes.py` — REFACTORED: constructor injection, typed schema returns, no business logic
- `sg_compute/control_plane/Fast_API__Compute.py` — UPDATED: platform field, `Exception__AWS__No_Credentials` handler registered
- `sg_compute/platforms/exceptions/` — NEW: `Exception__AWS__No_Credentials`
- `sg_compute/core/node/schemas/Schema__Node__List.py` — UPDATED: `total` and `region` fields added
- `sg_compute__tests/control_plane/test_Routes__Compute__Nodes.py` — REWRITTEN: zero mocks. Commit: 7ca8b96.

---

## 2026-05-04 (BV2.1)

- `host-control/index.md` — UPDATED: `sgraph_ai_service_playwright__host/` deleted (orphaned copy confirmed by legacy review); authoritative package is `sg_compute/host_plane/`; port corrected `:9000` → `:19009`; tests and pyproject.toml reference removed. Commit: `0517528`.

---

## 2026-05-02 (B3.0)

- `sg-compute/index.md` — UPDATED: B3.0 docker spec added; `sg_compute_specs/docker/` fully documented; Spec__Loader now returns 3 specs; 183 tests passing.

---

## 2026-05-02

- `sg-compute/index.md` — UPDATED: phase-2 (B2) foundations; primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver, Node__Manager, manifest.py for pilot specs; helpers moved to platforms/ec2/. 152 tests passing.
- `sg-compute/index.md` — NEW: SG/Compute domain placeholder; seeded by phase-1 (B1) rename commit. `ephemeral_ec2/` → `sg_compute/`; `sg_compute_specs/` introduced with pilot specs (ollama, open_design). Full domain content lands in phase-2 (B2).
- `index.md` — UPDATED: added `sg-compute/` domain row; domain count 10 → 11.
- `index.md` — NEW: master domain index created (reality document refactor begins; 10-domain tree introduced).
- `README.md` — UPDATED: explains the new fractal model and the migration shim.
- `host-control/index.md` — NEW: pilot domain migration; `sgraph_ai_service_playwright__host` package (container runtime abstraction, shell executor, three Routes__Host__* classes, EC2 boot wiring). Sourced from commit `11c2a08`.
- `host-control/proposed/index.md` — NEW: WebSocket shell streaming hardening, RBAC for host endpoints, runtime auto-detection feedback in UI.
- `../DAILY_RUN.md` — NEW: daily routine + backlog (B-001 … B-010 = per-domain migration queue + housekeeping).
- `../activity-log.md` — NEW: session-continuity stub with first entry.

---

## Entries before 2026-05-02

Reality was tracked as version-stamped monoliths under this folder. The most recent split was `v0.1.31/01..15__*.md` (2026-04-20 → 2026-04-29). Earlier monoliths: `v0.1.13`, `v0.1.24`, `v0.1.29` `__what-exists-today.md`. None of those had a per-update changelog entry; this changelog starts from the domain-tree introduction.

For history pre-2026-05-02, read the relevant `v0.1.31/NN__*.md` slice or the archived monolith.
