# T2.3 — A11y: keyboard nav for tablist + n=5 contrast pass + fix `--text-3`

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

FV2.10 brief required:

- ARIA tablist semantics on `sg-compute-nodes-view` tabs ✅ shipped
- **Keyboard nav: ←/→/Home/End for tab switching** ❌ NOT shipped (zero hits for `ArrowLeft`/`ArrowRight`/`Home`/`End` in nodes-view JS)
- Contrast check on **5 components** ❌ sampled n=1
- `--text-3` token (3.8:1) ❌ punted ("out of scope") — fails AA body text 4.5:1

ARIA roles were applied without the keyboard semantics they imply. Screen readers announce tabs as a tablist; users with no mouse can't navigate.

## Tasks

### Task 1 — Keyboard nav

1. **Find the nodes-view tab handler** — `components/sp-cli/sg-compute-nodes-view/v0/v0.1/v0.1.0/sg-compute-nodes-view.js` (or wherever the 6-tab logic lives).
2. **Add a `keydown` listener** on the tablist. Handle:
   - `ArrowLeft` → focus + activate previous tab (wrap around).
   - `ArrowRight` → next tab.
   - `Home` → first tab.
   - `End` → last tab.
   - `Enter` / `Space` on a focused tab → activate (default browser behaviour for `<button>` may cover this).
3. **Roving tabindex pattern** — only the active tab has `tabindex="0"`; others have `tabindex="-1"`. Update on tab switch.
4. **Test with keyboard only** — Tab into the tablist, arrow through all 6 tabs, Home + End, no mouse.

### Task 2 — Contrast pass on 5 components

1. **Pick 5 components** — `sg-compute-nodes-view`, `sg-compute-launcher-pane`, `sg-compute-settings-view`, `sg-compute-stacks-pane`, `sg-compute-launch-form`.
2. **Use a contrast tool** — Lighthouse (Chrome DevTools), axe DevTools, or a colour-contrast plugin. Sample text/background pairs.
3. **Report findings** in the PR description: per-component, per-pair, ratio, pass/fail.

### Task 3 — Fix `--text-3` token

1. **`shared/tokens.css`** — find `--text-3` (currently 3.8:1 against `--color-bg`).
2. **Adjust** to ≥ 4.5:1 for body text (WCAG AA). E.g. shift from `#888888` to `#a5a5a5` or similar — measure with the contrast tool.
3. **Verify across components** that the new value doesn't regress other usages.
4. **If a single token can't satisfy all use-cases**, split into `--text-3-on-dark`, `--text-3-on-light`, etc. Document the split.

## Acceptance criteria

- Keyboard nav works: Tab into tablist, ←/→/Home/End cycle through tabs.
- Roving tabindex correctly applied.
- 5-component contrast report attached to PR with pass/fail per pair.
- `--text-3` ≥ 4.5:1 against the relevant background.
- No regressions in other uses.

## "Stop and surface" check

If `--text-3` is used in too many contexts to fix without splitting tokens: **STOP** and surface to design — splitting tokens is a design call, not an A11y patch.

## Live smoke test (acceptance gate)

Open the nodes-view in a browser. Tab to the tablist. ←/→ cycles tabs. Home → first; End → last. No mouse used. Screenshot the keyboard interaction with focus rings visible. Run Lighthouse A11y audit on the dashboard — score should improve.

## Source

Executive review Tier-2; frontend-late review §"Missed requirement #1 + FV2.10 contrast".
