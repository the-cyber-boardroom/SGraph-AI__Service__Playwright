# BV2.7 — Migrate Tier-1 `__cli/` sub-packages → `sg_compute/`

## Goal

Legacy code review found the new `sg_compute_specs/` tree imports from `sgraph_ai_service_playwright__cli/{aws, core, image, catalog, ec2 schemas, observability primitives}`. This means the new tree has a **structural dependency on the legacy tree** — it's not actually independent. This phase breaks the cycle.

## Tasks

1. **Migrate `__cli/aws/`** → `sg_compute/platforms/ec2/aws/` (per Architect ratification — AWS helpers belong inside the EC2 platform, not at the SDK root). Use `git mv` to preserve history.
2. **Migrate `__cli/core/`** primitives that the spec tree imports → `sg_compute/core/<area>/` (extend existing core dirs).
3. **Migrate `__cli/image/`** → `sg_compute/image/`. Image-related primitives (e.g. `Schema__Image__Id`).
4. **Migrate `__cli/catalog/`** → `sg_compute/catalog/`.
5. **Migrate `__cli/ec2/schemas/` + `Ec2__Service` + `Ec2__AWS__Client`** → `sg_compute/platforms/ec2/`. The legacy review flagged `__cli/ec2/` has data classes the spec tree imports.
6. **Migrate `__cli/observability/` primitives** referenced by specs → `sg_compute/observability/primitives/`.
7. **Update imports** in every `sg_compute_specs/<name>/` spec — replace `from sgraph_ai_service_playwright__cli.X import Y` with `from sg_compute.X import Y`.
8. **Leave the legacy `__cli/` paths intact** for now — BV2.12 converts them to shims. Old imports from outside the spec tree (scripts, etc.) keep working.
9. Update reality doc.

## Acceptance criteria

- `grep -rln 'from sgraph_ai_service_playwright__cli' sg_compute/ sg_compute_specs/` returns zero hits (when run from the repo root).
- All tests green — `pytest sg_compute__tests/` and per-spec `tests/`.
- No new test failures in the legacy `tests/` tree (the legacy tree should be unaffected).
- Reality doc has the migration entries.

## Open questions

- **Naming for `__cli/aws/`.** Architect ratified `sg_compute/platforms/ec2/aws/` — confirm before this phase starts. Alternative `sg_compute/aws/` is rejected.

## Blocks / Blocked by

- **Blocks:** BV2.8 (CI guard relies on the cycle being broken first), BV2.10 + BV2.11 (further cleanup phases).
- **Blocked by:** BV2.4 (route refactor) is recommended first because some `__cli/aws/` files have shared helpers used by both legacy and new code paths — easier to refactor when the new tree is stable.

## Notes

This is the most disruptive phase in v0.2.x backend. **Recommend pairing with the Architect for the entire session.** Use `git mv` to preserve history; sample the imports in batches before committing.
