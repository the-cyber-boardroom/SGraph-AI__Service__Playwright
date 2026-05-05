# Debrief — T2-FE-patch: ami_name + spec-detail fixes

**Date:** 2026-05-05
**Status:** PARTIAL (visual snapshot deferred — see Task 5 below)
**Brief:** `team/comms/briefs/v0.2.1__hotfix/frontend/T2_FE-patch__ami-spec-detail-fixes.md`

---

## Summary

Six-item patch covering 2 hidden bugs in T2.1 and 4 gaps from the T2.2 over-claim.

---

## Task 1 — ami_name plumbing fix ✅

`sg-compute-launch-panel._launch()` was silently dropping `ami_name` from the POST body. Added `ami_name: values.ami_name || ''` to the body construction. `getValues()` already returned the field; the panel just never forwarded it.

---

## Task 2 — creation_mode enum case ✅ (no change required)

Backend `Enum__Stack__Creation_Mode` values confirmed: `'fresh'`, `'bake-ami'`, `'from-ami'` (kebab-case). Frontend was already using the exact same strings. No change needed; documented here as the coordination artefact.

---

## Task 3 — spec-card click + keyboard access ✅

`sg-compute-specs-view._buildCard()` changes:
- Card article gets `tabindex="0"` and `aria-label` with "press Enter to view details" hint
- Card body click (not from a button) dispatches `sp-cli:spec.selected`
- Enter/Space keydown on the card (when card itself is focused) also dispatches detail
- Both `.btn-detail` and `.btn-launch` call `e.stopPropagation()` so they don't bubble to the card click handler
- CSS: `:focus-visible` ring added; `:hover` border highlight added; `cursor: pointer`

---

## Task 4 — README placeholder ✅

`sg-compute-spec-detail._render()` now always hides the README link and shows the placeholder. Placeholder text includes the spec_id and references the backend brief `BV__spec-readme-endpoint.md`. No active link shipped.

Also fixed in same pass:
- Inline `style=` attributes removed from template literals; replaced with `.sd-field-empty` and `.sd-extends-id` CSS classes
- `spec.stability || 'experimental'` → `spec.stability || 'unknown'` with matching `.sd-stability-badge.unknown` CSS class

---

## Task 5 — Snapshot test PARTIAL ✅ (structural) / ⚠ (visual)

**Structural test**: `tests/ci/test_sg_compute_spec_detail__snapshot.py` — 13 assertions covering file existence, custom element registration, JS API surface (`open`, `_render`, `_launch`), README placeholder contract, inline-style absence, stability fallback, and CSS class presence. **13/13 pass.**

**Visual snapshot**: PARTIAL. No ESM web-component test runner exists in this project. Future direction: live visual tests will run against a Playwright Node created from a spec (sg-compute spec firefox create → node serves dashboard → Playwright navigates and captures screenshot). This is the planned live-test pattern referenced by the engineering lead.

---

## Task 6 — Live smoke screenshot ⚠ PARTIAL

Cannot take a live browser screenshot in the current development environment (no browser + no running dashboard server). The structural tests cover the contract. Visual verification requires the Playwright Node live-test pattern described in Task 5.

**Good failure:** this gap was acknowledged up front rather than silently deferred. It is named here as a PARTIAL item, not a COMPLETE claim.

---

## Task 7 — T2.2 debrief flipped ✅

`team/claude/debriefs/2026-05-05__t2.2__spec-detail-view.md`: `COMPLETE` → `PARTIAL — 4 gaps fixed in T2-FE-patch`. A "gaps found in review" table was appended listing each fix. The bad-failure classification is explicit.

---

## Failures

**Good failure:** Task 2 coordination showed the backend enum was already kebab-case matching the frontend. The "stop and surface" check fired correctly — looked up the file before making any change.

**Bad failure (inherited from T2.2):** The original T2.2 over-claim of COMPLETE when card-click, README link, inline styles, and stability defaulting were all wrong. Named explicitly in the T2.2 debrief addendum. Not repeated here.
