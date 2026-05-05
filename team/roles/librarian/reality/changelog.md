# Reality — Changelog

**Format:** `Date | Domain file(s) updated | One-line description`

This is a pointer log, not a content log. For full delta detail, see the master index for that date in `team/roles/librarian/reviews/MM/DD/` (folder created on first review) or the linked domain `index.md`.

---

## 2026-05-05 (BV2.3)

- `sg-compute/index.md` — UPDATED: BV2.3 pod management added; `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 collections, `Routes__Compute__Pods` (6 endpoints), `Routes__Compute__Nodes` constructor injection. 246 tests passing.

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
