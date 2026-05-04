# FV2.10 — A11y pass on `sp-cli-nodes-view` tabs + icon buttons + spec cards

## Goal

Code review flagged: zero ARIA / keyboard affordances on the 6-tab node-detail panel; on icon-only buttons (◀ ↺ ✕ 👁 ⎘ 📋); on click-on-`<div>` spec cards in compute-view. No `:focus-visible` rules in any sampled CSS. Plus: `sp-cli-launch-form` calls third-party `api.ipify.org` (privacy/supply-chain concern — out of scope here, addressed in FV2.11).

This phase brings the dashboard to **WCAG AA baseline**.

## Tasks

1. **`sp-cli-nodes-view` tabs** — add ARIA tablist semantics:
   - Wrapper: `role="tablist"`.
   - Each tab button: `role="tab"`, `aria-selected="true|false"`, `aria-controls="<panel-id>"`, `tabindex="0"`.
   - Panels: `role="tabpanel"`, `aria-labelledby="<tab-id>"`.
   - Keyboard nav: `←` / `→` to switch tabs; `Home` / `End` for first/last.
2. **Icon-only buttons** — every `<button>` containing only an emoji or icon gets:
   - `aria-label="action description"` (e.g. `aria-label="Refresh node list"`).
   - `title=""` to match `aria-label` (browser tooltip).
3. **Spec cards in `sp-cli-compute-view`** — convert `<div>` cards to `<button>` (or add `role="button" tabindex="0"` and Enter/Space handlers).
4. **Focus styles** — add `:focus-visible` rules across components. Use `outline: 2px solid var(--color-accent); outline-offset: 2px`. **Don't** suppress focus.
5. **Contrast check** — sample 5 components for WCAG AA contrast (4.5:1 for normal text, 3:1 for large). Stability badges (`experimental` amber on dark bg) often fail; widen to 4.5:1 if needed.
6. **Test** — manual keyboard-only navigation across the dashboard. Every interactive element reachable via Tab; every action triggerable via keyboard.
7. **Snapshot tests** — update where ARIA attributes change the DOM.
8. Update reality doc / PR description.

## Acceptance criteria

- ARIA tablist + role attributes on `sp-cli-nodes-view`.
- Every icon-only button has `aria-label`.
- Spec cards are keyboard-actionable.
- `:focus-visible` rules visible everywhere.
- Manual keyboard-only smoke test passes.
- Contrast check report (5+ components verified).

## Open questions

- **Screen reader test.** Out of scope for v0.2; defer to v0.3.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** none. Run when capacity allows.

## Notes

A11y is a **continuous** quality bar — this phase establishes the baseline; future PRs maintain it. Add an ESLint rule (or pre-commit check) for `aria-label` on icon buttons if feasible.
