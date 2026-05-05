# T2.3 — Complete the `: object = None` cleanup; wire the CI guard

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

Two related issues from BV2.8:

1. **`bade2ad` "fix all : object = None bypasses"** only fixed Service / Health files. **~39 sites in `*__AWS__Client.py` files survived untouched** despite the commit message claiming completeness. Type_Safe is silently bypassed across the AWS client surface.
2. **`tests/ci/test_no_legacy_imports.py`** exists but is **not invoked by any GitHub workflow**. It would fail today (BV2.10 introduced 3 legacy imports under `sg_compute/control_plane/` that the guard catches — but no one runs the guard).

## Tasks

### Part 1 — finish the cleanup

1. `grep -rn ': object = None' sg_compute_specs/ sg_compute/` — list every site.
2. For each site: replace `object` with the concrete type (`Optional[T]`, where `T` is the actual class assigned). If it's genuinely heterogeneous, use a `Type_Safe` abstract base.
3. For each spec's `*__AWS__Client.py` — likely `aws_client : object = None` should become `aws_client : Optional[<Spec>__AWS__Client] = None` or pulled in from a shared base.
4. Run the spec tests; nothing should break.

### Part 2 — wire the CI guard

1. Find or create the GitHub Actions workflow that runs unit tests. Today: likely `.github/workflows/ci-pipeline.yml` or `ci-pipeline__dev.yml`.
2. Add a step before / alongside the unit-test step:
   ```yaml
   - name: Verify no legacy imports
     run: pytest tests/ci/test_no_legacy_imports.py -v
   ```
3. **Fix the 3 violations BV2.10 introduced** under `sg_compute/control_plane/` — find them with `pytest tests/ci/test_no_legacy_imports.py -v` and replace each legacy import with the new path (or shim accordingly per BV2.7).
4. Verify the workflow fails CI when a legacy import is added (test by adding one in a throw-away commit; revert).

## Acceptance criteria

- `grep -rn ': object = None' sg_compute_specs/ sg_compute/` returns zero hits.
- `pytest tests/ci/test_no_legacy_imports.py` passes.
- A GH workflow step runs the guard.
- Adding a legacy import (in a throw-away test) fails the workflow.

## "Stop and surface" check

If you find a `: object = None` site where the actual type is genuinely dynamic (e.g. multiple unrelated classes assigned at different times): **STOP**. Surface to Architect — this is a design smell that needs a polymorphic base, not an `object` escape hatch.

## Live smoke test

`pytest tests/ci/test_no_legacy_imports.py -v` → green. Add `from sgraph_ai_service_playwright__cli.foo import bar` to a sg_compute file → red.

## Source

Executive review Tier-2; backend-early review §"Bonus finding"; backend-late review §"BV2.8/BV2.10 — Top 2 security issue".
