# 30 — Migration Phases (sequencing across both teams)

**Audience:** Conductor / Architect / UI Architect — and both Sonnet teams when planning their next session.

This document is the **timing layer**. It says which phase blocks which, where the parallel paths live, and what "done" looks like for each.

The backend plan ([`10__backend-plan.md`](10__backend-plan.md)) and frontend plan ([`20__frontend-plan.md`](20__frontend-plan.md)) are the **what**; this is the **when**.

---

## Phase ledger

| # | Backend phase | Frontend phase | Blocks | Parallel? | Risk |
|---|---------------|----------------|--------|-----------|------|
| 1 | Phase 1 — Rename `ephemeral_ec2/` → `sg_compute/`; move pilot specs to `sg_compute_specs/` | F1 — Terminology in user-facing labels | Phase 2 (B); F2 (FE depends on B4) | **Yes** — these can run in parallel; FE only touches labels in the legacy tree | Low |
| 2 | Phase 2 — Foundational base classes; `platforms/ec2/`; refactor pilot specs | — | Phase 3, 4 | No (FE waits for B4 / B6) | Low-medium |
| 3 | Phase 3.0 — `docker` spec migration (proof-of-contract). Then 3.1-3.8 one per session. | — | Phase 4 needs at least 3.0; no full block on later 3.x | Mostly — multiple specs can migrate in parallel sessions if Architect signs off | Medium per spec |
| 4 | Phase 4 — Control plane FastAPI (`Fast_API__Compute`) | — | F2, F3, F5 | No | Medium |
| 5 | Phase 5 — `sg-compute` CLI command | — | (operator-facing only; doesn't block FE) | **Yes** with FE phases | Low |
| 6 | Phase 6 — Move host plane; rename containers → pods | F8 (post-host-plane URL update) | — | Low |
| 7 | Phase 7.A — `agent_mitmproxy` fold; 7.B — Playwright service fold | — | — | **Yes** (7.A and 7.B independent) | Medium |
| 8 | Phase 8 — PyPI publish setup | — | (releasable artefact) | No | Medium |
| — | — | F2 — API client migration | F3, F5 | After B4 | Medium |
| — | — | F3 — Specs view in left nav | — | After F2 | Low |
| — | — | F4 — Wire-event vocabulary `stack.*` → `node.*` | F9 | **Yes** with F2/F3 | Low-medium |
| — | — | F5 — Catalogue-loader replaces `PLUGIN_ORDER` | F6 | After F2 | Medium |
| — | — | F6 — Per-spec UI co-located with specs | — | After B3.x + F5 | Medium per spec |
| — | — | F7 — Stacks placeholder view | — | **Yes** | Low |
| — | — | F8 — Host pods URL update | — | After B6 | Low |
| 9 | — | F9 — Cosmetic prefix rename `sp-cli-*` → `sg-compute-*` | F10 | After F4 | Medium-high (sweep risk) |
| 10 | — | F10 — Move dashboard into `sg_compute/frontend/` | (release) | After F9 | Medium |

---

## Critical path

The shortest path from "today" to "PyPI-publishable" is:

**B1 → B2 → B3.0 → B4 → F2 → B5 → B6 → F8 → B7.A + B7.B → B8.**

Anything not on this path can be parallelised.

Estimated cadence at one phase per session per team (conservative):

| Week | Backend session | Frontend session |
|------|-----------------|-----------------|
| 1 | B1 (rename + restructure) | F1 (terminology labels) |
| 2 | B2 (foundations) | (idle / planning F2) |
| 3 | B3.0 (docker spec migration) | (idle) |
| 4 | B4 (control plane) | F2 (API client) — can start mid-week 3 if B4 partial |
| 5 | B5 (CLI) | F3 (specs view) |
| 6 | B3.1 (linux) + B3.2 (podman) | F4 (events) + F5 (catalogue loader) |
| 7 | B3.3 (vnc) + B3.4 (neko) | F6 (per-spec UI co-locate, first 2 specs) |
| 8 | B3.5 + B3.6 (prometheus, opensearch) | F6 (cont.) |
| 9 | B3.7 (elastic) + B6 (host plane) | F8 (pods URLs) |
| 10 | B7.A (mitmproxy) + B7.B (playwright) | F7 (stacks placeholder) |
| 11 | B3.8 (firefox) | F9 (cosmetic rename) |
| 12 | B8 (PyPI build) | F10 (move dashboard into sg_compute/frontend/) |

12 weeks is a realistic floor. Slippage on per-spec migrations or unexpected coupling can easily add 3-4 weeks.

---

## Exit criteria per phase (what "done" means)

### B1 — Rename
- Tree exists; `ephemeral_ec2/` does not; `sg_compute/`, `sg_compute_specs/` exist.
- Existing tests at new paths still pass.
- Brief files inside `sg_compute/brief/` updated.
- One PR merged to dev.

### B2 — Foundations
- Type_Safe primitives, enums, schemas, `Platform` interface, `Spec__Loader`, `Spec__Resolver`, `Node__Manager` all exist.
- Pilot specs (`ollama`, `open_design`) refactored onto the new bases; their tests pass.
- Reality doc has the `sg-compute/` domain seeded.

### B3.0 — Docker spec migration
- `sg_compute_specs/docker/` is a real spec; manifest validates; tests pass.
- Legacy `sp-cli docker create` works via shim (deprecation warning).

### B3.1+ — One per remaining legacy spec
- Spec migrated; manifest validates; tests pass.
- Compatibility shim left at the legacy path.

### B4 — Control plane
- `Fast_API__Compute` serves `/api/{nodes,pods,specs,stacks,health}`.
- Per-spec routes mounted under `/api/specs/{id}/...`.
- Integration test passes.

### B5 — CLI
- `sg-compute --help` lists 4 verbs.
- `sg-compute spec list` works.
- `sg-compute spec docker create` end-to-end works.

### B6 — Host plane
- `sg_compute/host_plane/` exists; `sgraph_ai_service_playwright__host/` removed (or shimmed).
- Routes path `/containers/*` → `/pods/*`.
- Tests at new location pass.

### B7.A / B7.B — Folds
- `agent_mitmproxy/` → `sg_compute_specs/mitmproxy/` (7.A).
- `sgraph_ai_service_playwright/` → `sg_compute_specs/playwright/core/` (7.B).
- Both visible in the catalogue; both still functional (mitmproxy admin FastAPI starts; Playwright Lambda packaging works).

### B8 — PyPI build
- `python -m build` produces 2 wheels.
- `pip install` in fresh env succeeds.
- `sg-compute spec list` works against installed package.
- Optional: TestPyPI publish.

### F1 — Terminology
- Zero "Plugin" / single-instance "Stack" labels in the UI.
- Snapshot tests updated.

### F2 — API client
- Dashboard works against `Fast_API__Compute` end-to-end.
- Feature flag toggles back to legacy.
- Field renames done.

### F3 — Specs view
- Left nav "Specs" item exists; clicking renders a catalogue grid.
- Spec detail tab works.

### F4 — Events
- New event names dispatched; old names dispatched alongside (back-compat).
- `FAMILIES` map updated.

### F5 — Catalogue loader
- `PLUGIN_ORDER` and friends replaced by `spec-catalogue.js`.
- Adding a backend spec without UI change = card appears.

### F6 — Per-spec UI co-location
- Per migrated spec: card + detail live under `sg_compute_specs/{name}/ui/`.
- Dashboard fetches them dynamically.

### F7 — Stacks placeholder
- Left nav "Stacks" item exists; placeholder view renders.

### F8 — Host pods URLs
- Every `/containers/*` URL replaced with `/pods/*`.

### F9 — Cosmetic prefix rename
- Zero `sp-cli-*` references in the active component tree.
- All snapshot tests pass.
- Manual smoke test of every view.

### F10 — Dashboard move
- `sgraph_ai_service_playwright__api_site/` removed; `sg_compute/frontend/` lives.
- All script paths in the served HTML updated.

---

## Parallel opportunities

These are the windows where both teams can move at once without stepping on each other:

- **Week 1-2**: B1+B2 (backend) and F1 (frontend, label sweep) run in parallel. F1 only touches strings in the legacy tree — backend doesn't care.
- **Week 4-5**: F2 (API client) and B5 (CLI) are independent — backend can build the operator CLI while frontend wires the dashboard to the new endpoints.
- **Week 6**: F4 (events) and F5 (catalogue loader) can run as one combined frontend session; backend continues B3.x specs.
- **Week 7-8**: B3.x and F6 form a pipeline — each migrated spec unlocks one F6 sub-phase. Backend leads, frontend follows by one cycle.
- **Week 11**: F9 (cosmetic rename) is a self-contained sweep; backend can run B8 in parallel.

---

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| **Per-spec migration drag** — 8 specs at one per session = 8 weeks of B3.x | Parallelise: 2 backend Sonnet sessions per week if multiple branches don't conflict. The specs are well-isolated; conflicts unlikely. |
| **F9 sweep regression** | Run a full UI snapshot suite before merging; manual smoke test every view; ship behind a feature flag if necessary. |
| **PyPI publish surprises** | Ship to TestPyPI first; test `pip install` in CI before any real publish. |
| **Lambda packaging breakage in B7.B** | Keep the Lambda deploy CI workflow green throughout — phase 7.B's PR runs the full Lambda smoke test. |
| **Compatibility shim drift** — legacy `sp-cli` calls keep working but tests for the shim are not enforced | Add a shim test per migrated spec: `assert sp_cli.legacy_path imports from sg_compute_specs.<name>`. |
| **Reality doc rot during the migration** | The Librarian's daily run picks up doc updates. Add a backlog item B-013 "track each phase's reality doc update" in `team/roles/librarian/DAILY_RUN.md`. |

---

## Definition of "complete"

The migration is **complete** when:

1. `sg-compute` is on PyPI as a real published package.
2. `sg-compute-specs` is on PyPI with at least the 8 legacy specs + 2 incubation specs (open_design, ollama).
3. The dashboard is served from `sg_compute/frontend/` with `sg-compute-*` component naming.
4. The legacy `sgraph_ai_service_playwright*` packages are reduced to compatibility shims (or removed entirely).
5. The reality doc tree under `team/roles/librarian/reality/` reflects the new domain layout (`sg-compute/`, `sg-compute-specs/<spec>/`).
6. The `Conductor` and `Architect` have signed off on the post-migration architecture review.

After that: extract to `sgraph-ai/SG-Compute` repository (out of scope for this brief).
