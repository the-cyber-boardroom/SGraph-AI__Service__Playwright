# Code-review synthesis (2026-05-04)

This file distills the 6 reports that informed the v0.2 plan. Originals at `team/humans/dinis_cruz/claude-code-web/05/04/22/`:

- `00__executive-audit__sg-compute-migration.md` (264 lines) — top-level audit synthesis
- `backend-audit__sg-compute-migration.md` (257 lines) — phase-by-phase B1-B8 verification
- `frontend-audit__sg-compute-and-post-fractal-ui.md` (119 lines) — F1-F10 + post-fractal-UI verification
- `new-briefs-audit__sg-compute.md` (295 lines) — direction-of-travel mapping for the 9 new briefs
- `code-review__sg-compute-new.md` (222 lines) — quality of the new SDK + 12 specs
- `code-review__legacy-not-refactored.md` — what's still in legacy paths
- `code-review__frontend-implementation.md` (306 lines) — dashboard quality

---

## What was delivered

| Phase | Status | Notes |
|-------|--------|-------|
| B1 rename | ✅ | clean |
| B2 foundations | ✅ | Pod__Manager + Stack__Manager not built (deferred) |
| B3.0-B3.7 specs | ✅ × 8 | linux dropped intentionally; firefox tagged B3.7 |
| B4 control plane | ⚠ | endpoints exist; Routes__Compute__Nodes wired post-audit (`c5bc28e`); still missing Pod routes, Lambda handler |
| B5 CLI | ⚠ | root verbs; per-spec dispatcher missing |
| B6 host plane | ⚠ | content moved; legacy not deleted |
| B7.A mitmproxy | ⚠ | copy not move |
| B7.B playwright | ⚠ | copy not move |
| B8 PyPI build | ✅ | both wheels build |
| F1 terminology | ✅ | one residual string |
| F4 events (entity) | ⚠ | per-type namespace not migrated |
| F7 stacks placeholder | ✅ | |
| F8 host pods | ✅ | sidecar track, not original brief |
| F2/F3/F5/F6 | ❌ | backend-blocked |

## 6 critical gaps (now reframed for v0.2)

| Original gap | v0.2 phase |
|--------------|------------|
| G1 — `linux` dropped | NOT a gap — ratified as a design decision |
| G2 — B4 façade | BV2.3 (Pod__Manager), BV2.4 (route cleanup), BV2.5 (create_node + Lambda), BV2.5 (Lambda handler) |
| G3 — no per-spec `cli/` | BV2.6 |
| G4 — 5 dual-write trees | BV2.1, BV2.7, BV2.10, BV2.11, BV2.12 |
| G5 — capability enum unlocked | BV2.13 (header comment update) |
| G6 — F4 per-type half-done | FV2.9 |

## 5 emergent strategic themes

| Theme | Now captured in |
|-------|-----------------|
| A — Sidecar first-class | `architecture/03__sidecar-contract.md` + BV2.2 (Section__Sidecar) + BV2.15 (security hardening) |
| B — S3 / boto3 transparency | `architecture/01__architecture.md` §8 + BV2.16 (storage spec category) |
| C — Memory-FS dependency | Documented in s3_server's own repo; SDK side is just discovery (BV2.16) |
| D — Cross-repo extraction | `architecture/01__architecture.md` §9 + BV2.16 + ratified for storage specs only |
| E — Operation-mode taxonomy | Deferred to v0.3 — let s3_server validate first |

## Top risks from the new-code review

| Severity | Item | Phase |
|----------|------|-------|
| 🔴 R1 | Reflective CORS + credentials | BV2.15 |
| 🔴 R2 | Cookie `httponly=false` | BV2.15 |
| 🔴 R3 | SameSite=lax + reflective CORS | BV2.15 |
| 🔴 R4 | `: object = None` Type_Safe bypass (5 specs) | BV2.8 |
| 🔴 R5 | Specs have only thin tests | BV2.14 |
| ⚠ R6 | `unittest.mock.patch` in SDK tests | BV2.4 + BV2.14 |
| ⚠ R7 | Spec__Routes__Loader misses 3 specs | BV2.13 |
| ⚠ R8 | Pod__Manager + Routes__Compute__Pods missing | BV2.3 |
| ⚠ R9 | Logic in Routes__Compute__Nodes | BV2.4 |

## Top risks from the legacy review

- Only `__host/` is orphaned (BV2.1 deletes).
- `sgraph_ai_service_playwright/`, `__cli/`, `agent_mitmproxy/` are 100% load-bearing — pinned by `lambda_entry.py`, dockerfiles, scripts.
- `__cli/aws/`, `__cli/core/`, `__cli/catalog/`, `__cli/image/`, `__cli/ec2/` schemas are imported BY the new spec tree — structural dependency on legacy. **BV2.7 fixes.**
- `__cli/elastic/lets/` has no migration target — defer to v0.3.
- Drift detected: `__cli/elastic/Elastic__AWS__Client.py` (451 LOC) vs `sg_compute_specs/elastic/...` (243 LOC). Naive resync would lose features.
- Version drift: root `version` lags `pyproject.toml`.

## Top risks from the frontend review

- 3 patterns done well: three-file pattern, SgComponent base + onReady lifecycle, `_esc()` HTML escaping.
- 6 hardcoded plugin lists need centralising — **FV2.3**.
- 6 sites in `sp-cli-nodes-view.js` hardcode `'running'` — **FV2.1**.
- Zero ARIA / keyboard affordances on tabs + icon buttons + spec cards — **FV2.10**.
- `sp-cli-launch-form` calls `api.ipify.org` — **FV2.11**.
- Zero `/api/*` migration today — **FV2.2**.
- Zero per-spec UI under `sg_compute_specs/<name>/ui/` — **FV2.6**.
- `sp-cli-stacks-pane` is legacy and deletable — **FV2.11**.
- CLAUDE.md rule 9 (no underscore-prefix) violated everywhere in JS — accepted; rule will be amended to Python-only in v0.2 architecture rules.

## What this synthesis informs

Every finding above maps to a phase in `backend/` or `frontend/`. The plan is **reactive**, not aspirational — it closes the gaps that the review surfaced + the strategic themes that emerged.

For full verbatim findings, read the originals in `team/humans/dinis_cruz/claude-code-web/05/04/22/`.
