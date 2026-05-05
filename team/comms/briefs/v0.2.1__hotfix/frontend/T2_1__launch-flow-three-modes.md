# T2.1 — Launch flow: three creation modes + AMI picker + size + timeout + cost preview

⚠ **Tier 2 — contract violation.** Standalone PR. **Largest scope-cut to fix.**

## What's wrong

FV2.5 brief required:

- Three-mode selector (FRESH / BAKE_AMI / FROM_AMI).
- AMI picker (conditional reveal for FROM_AMI).
- Instance size + timeout fields.
- BAKE_AMI cost preview.
- Validation (FROM_AMI requires AMI).

What shipped: **FRESH-only `POST /api/nodes`** with no mode selector, no AMI picker, no cost preview. Marked done in the debrief.

## Tasks

1. **Find the launch form** — likely `components/sp-cli/sg-compute-launch-form/v0/v0.1/v0.1.0/sg-compute-launch-form.{js,html,css}` (post-FV2.12 rename).
2. **Add the mode selector** — radio or segmented control with FRESH / BAKE_AMI / FROM_AMI. Default: FRESH.
3. **Conditional reveal** via CSS-only show/hide (a class on the form root):
   - FRESH → stack-name + size + timeout + plugin extras.
   - BAKE_AMI → same + "name this AMI" field.
   - FROM_AMI → stack-name + AMI picker + size + timeout + plugin extras.
4. **Build `<sg-compute-ami-picker>`** under `_shared/` — dropdown of AMIs for the spec. Empty state ("No AMIs for this spec — try Fresh or Bake AMI mode"). Endpoint: `GET /api/amis?spec_id=<id>` — **if backend doesn't yet serve this**, ticket the backend (file a follow-up brief for the route) and ship the picker with a "loading… (backend route TBD)" placeholder. **Mark this PR PARTIAL** in that case.
5. **Cost preview banner** for BAKE_AMI — static estimate ("≈10 min build; ≈$0.05/GB/month storage"). Visual: an info banner that appears when BAKE_AMI is selected.
6. **Validation** — FROM_AMI without AMI selected → submit button disabled with inline error.
7. **Submit payload** — match `Schema__Stack__Create__Request__Base` (post-T2.6 backend Safe_Str primitives may rename fields; coordinate).
8. **Tests** — snapshot tests for all three modes; an interaction test that hides/shows the AMI picker.

## Acceptance criteria

- Mode selector renders FRESH / BAKE_AMI / FROM_AMI.
- AMI picker conditionally appears for FROM_AMI.
- Size + timeout fields always visible.
- Cost preview banner appears for BAKE_AMI.
- Submit blocked for invalid combinations.
- Snapshot tests cover all three modes.
- **Live browser smoke test:** FRESH launch works end-to-end (click → backend call → node appears in active list).

## "Stop and surface" check

If the AMI list endpoint isn't there yet: **STOP** and file the follow-up brief; ship the picker as PARTIAL with a clear placeholder. Don't silently skip.

## Live smoke test (acceptance gate)

Open the launch form in a browser. Click each of the three radios. The form re-renders correctly each time. Submit a FRESH launch. Backend `POST /api/nodes` is called. Node appears in the active list. Screenshot all three states; attach to PR.

## Source

Executive review Tier-2; frontend-early review §"Top contract violation (FV2.5 scope-cut)".
