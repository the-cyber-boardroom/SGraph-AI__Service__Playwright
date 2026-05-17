---
title: "SG/Compute — Original Brief Pack"
file: README.md
moved_from: sg_compute/brief/
moved_at: 2026-05-17 (under M-006b)
status: HISTORICAL — original architecture brief, preserved as the design baseline. Current reality lives in `team/roles/librarian/reality/sg-compute/index.md`.
---

# SG/Compute — Original Brief Pack

These 8 numbered files were the founding architecture brief for the `sg_compute` SDK. They were originally co-located with code under `sg_compute/brief/`; the move to `team/comms/briefs/` (under M-006b on 2026-05-17) restores them to the standard WORK home and keeps the codebase strictly code-only.

For **what exists today**, read [`team/roles/librarian/reality/sg-compute/index.md`](../../../roles/librarian/reality/sg-compute/index.md) — it supersedes the aspirational content here. These files remain authoritative for **why** the design looks the way it does.

---

## Reading order

| # | File | Topic |
|---|---|---|
| 01 | `01__overview.md` | What SG/Compute is, brand name, core design principles |
| 02 | `02__architecture.md` | Layered architecture: platform / spec / pod / stack |
| 03 | `03__package_structure.md` | `sg_compute/`, `sg_compute_specs/`, helpers, CLI layout |
| 04 | `04__helpers_layer.md` | Shared primitives reused across specs |
| 05 | `05__stack_contract.md` | The Spec → Stack contract, manifest typing |
| 06 | `06__open_design_stack.md` | Pilot spec walkthrough (open_design) |
| 07 | `07__ollama_stack.md` | Pilot spec walkthrough (ollama) |
| 08 | `08__implementation_phases.md` | Phased rollout plan (B1 / B2 / BV2.x …) |

---

## See also

- [`team/roles/librarian/reality/sg-compute/index.md`](../../../roles/librarian/reality/sg-compute/index.md) — what exists today
- [`team/comms/briefs/v0.1.140__sg-compute__migration/`](../v0.1.140__sg-compute__migration/) — migration-phase briefs
- [`team/comms/plans/`](../../plans/) — multi-step plans referencing these briefs
