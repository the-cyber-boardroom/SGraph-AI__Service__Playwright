# T3.4 — Centralise `INSTANCE_TYPES` / `REGIONS` / `MAX_HOURS` / `COST_TABLE`

⚠ **Tier 3 — integration cleanup.** Standalone PR.

## What's wrong

These four constants are hardcoded in **two places** that have **already drifted**:

- `sg-compute-compute-view.js:13-15,29-32`
- `sg-compute-launch-form.js:3-5`

Adding a new instance type or region requires a hand-sync. They've already disagreed.

## Tasks

1. **Pick a single owner.** Recommend `shared/launch-defaults.js` — module-level constants exported as a frozen object.
2. **Move the canonical definitions there.** Document them with comments noting source-of-truth (e.g. AWS region list, AWS instance-type tiers, etc.).
3. **Refactor both consumers** to import from `shared/launch-defaults.js`. Delete the local copies.
4. **Future-proof** — file a follow-up brief T3.4b: catalogue-driven instance types per spec (different specs may need different sizes; e.g. firefox needs more RAM than docker). Don't implement now; ticket only.
5. **Tests** — verify both consumers render correctly post-refactor.

## Acceptance criteria

- `shared/launch-defaults.js` exists with the canonical constants.
- Both consumers import from it; no local copies.
- Snapshot tests still pass.
- Follow-up brief filed for catalogue-driven instance types.

## Live smoke test

Open the launch form. Open the compute view. Both show the same instance types, regions, max hours.

## Source

Executive review Tier-3; frontend-early review §"Top hardcoded-data issue (FV2.5)".
