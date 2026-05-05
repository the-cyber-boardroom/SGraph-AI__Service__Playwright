# T2-FE-patch — Fix T2.1 hidden bugs + T2.2 over-claim

⚠ **Tier 2 — patch.** T2.1 (commit `67ca15e`) had textbook PARTIAL discipline but hides 2 real bugs. T2.2 (commit `dc703ed`) was over-claimed COMPLETE despite 4 real gaps. One PR fixes everything.

## What's wrong (per the 2026-05-05 14:00 review)

### T2.1 hidden bugs

1. **`ami_name` data-loss on submit.** The launch form's `getValues()` collects `ami_name` correctly. But `sg-compute-launch-panel._launch()` then DROPS the field when constructing the POST body. BAKE_AMI users will think they named their AMI; the backend never sees the name.
2. **`creation_mode` enum-case mismatch.** Frontend uses kebab-case (`'fresh'`, `'bake-ami'`, `'from-ami'`). Backend Safe_Str enum (after T2.6b lands) is likely underscored (`'FRESH'`, `'BAKE_AMI'`, `'FROM_AMI'`) or uppercase. **Coordinate with backend** before fixing — pick one canonical case and use it on both sides.

### T2.2 gaps under "COMPLETE"

3. **Card click not wired.** The brief explicitly required clicking a spec card on the Specs view to open the detail tab. Today only a secondary "View details" button works. The card body itself is dead.
4. **README link is a known-broken anchor.** No backend route for `/api/specs/{id}/readme` exists. The link 404s. The original brief required EITHER shipping the link OR replacing it with a placeholder + filing a follow-up brief. Neither happened.
5. **Snapshot test omitted** — no acknowledgement in the debrief. Brief required snapshot of a representative spec.
6. **No live smoke screenshot in the PR description.** Required by the new process rules.

## Tasks

### Task 1 — `ami_name` plumbing fix

1. Open `sg-compute-launch-form.js` — confirm `getValues()` returns `ami_name`.
2. Open `sg-compute-launch-panel.js._launch()` — find where the POST body is constructed. Add `ami_name` to the payload when `creation_mode === 'bake-ami'` (or whichever canonical case wins).
3. Add a unit/integration test: when mode is BAKE_AMI and ami_name is filled, the POST body contains `ami_name`.

### Task 2 — `creation_mode` enum case alignment

1. Coordinate with backend (or the [`backend/T2_6b__safe-str-primitives-finish.md`](../backend/T2_6b__safe-str-primitives-finish.md) brief). Read `sg_compute/primitives/enums/Enum__Stack__Creation_Mode.py` (or wherever it's defined) for the canonical case.
2. Update frontend constants to match. The values must match the backend Safe_Str enum exactly — typo = silent rejection.
3. Test: submit FRESH, BAKE_AMI, FROM_AMI; backend accepts all three.

### Task 3 — Wire spec-card click to open detail

1. Open `sg-compute-specs-view.{js,html}` — find the card render.
2. Add a click handler on the card body (or the `<article>` / `<button>` wrapper).
3. Click → opens `<sg-compute-spec-detail>` tab with the spec_id pre-loaded.
4. Keep the secondary "View details" button as well (redundant entry point, fine).
5. **Ensure keyboard access** — Enter / Space on a focused card should also trigger.

### Task 4 — README link → placeholder + cross-reference

1. The new `BV__spec-readme-endpoint.md` brief is filed for the backend. Until that ships:
2. The README section in `<sg-compute-spec-detail>` shows a placeholder: "Spec README will appear here once `GET /api/specs/<id>/readme` ships (see backend brief)."
3. The "broken anchor" link is removed.
4. When the backend endpoint ships, replace the placeholder with the real fetch.

### Task 5 — Snapshot test

1. Add a snapshot test for `<sg-compute-spec-detail>` against a representative spec (e.g. `firefox`).
2. Cover the manifest panel, the placeholder README section, and the "Launch node" button.

### Task 6 — Live smoke screenshot

1. Open the dashboard in a browser. Click into the Specs view. Click a card. Detail panel renders.
2. Submit a BAKE_AMI launch with a custom `ami_name`; verify the backend receives the name.
3. Screenshot both flows; attach to PR.

### Task 7 — Flip T2.2 debrief

1. Open `team/claude/debriefs/2026-05-05__t2.2__spec-detail-view.md`.
2. Change status from `COMPLETE` to `PARTIAL — 4 gaps fixed in T2-FE-patch (commit X)`.
3. Reference this brief.

## Acceptance criteria

- `ami_name` reaches the backend on BAKE_AMI launches.
- `creation_mode` values match the backend Safe_Str enum exactly.
- Card click opens spec detail; keyboard access works.
- README placeholder visible; no broken anchor; cross-references the backend brief.
- Snapshot test for spec-detail exists.
- Live smoke screenshot in PR description.
- T2.2 debrief flipped to `PARTIAL`.

## "Stop and surface" check

If you find the backend `creation_mode` enum case is unclear (no canonical name yet): **STOP**. Surface to Architect. Don't pick a case unilaterally — both teams need to agree.

If the backend `BV__spec-readme-endpoint.md` is delayed: **STOP**. Don't hack a workaround (e.g. inline the README content into the manifest). The placeholder is the right answer.

## Source

Executive review T2-implementation (2026-05-05 14:00) §"Per-phase verdicts — Frontend".
