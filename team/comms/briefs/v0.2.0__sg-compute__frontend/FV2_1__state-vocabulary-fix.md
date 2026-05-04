# FV2.1 — Centralise node-state vocabulary

## Goal

Code review found **6 sites** in `sp-cli-nodes-view.js` hardcoding `state === 'running'`. Once the backend ships `Schema__Node__Info` with the canonical `Enum__Node__State` values (verified by BV2.2), the moment the value is `'ready'` or `'READY'`:

- Boot-log polling never stops.
- Row colour breaks.
- Auto-tab-switch never fires.

This is a **latent bug**. Fix it by centralising state knowledge in one helper module.

## Tasks

1. Create `sgraph_ai_service_playwright__api_site/shared/node-state.js`:
   ```js
   // Single source of truth for node-state vocabulary.
   // Mirrors Enum__Node__State on the backend.
   
   export const NODE_STATE = {
       BOOTING:     'BOOTING',
       READY:       'READY',
       TERMINATING: 'TERMINATING',
       TERMINATED: 'TERMINATED',
       FAILED:      'FAILED',
   }
   
   export function isRunning(state) {
       // Tolerant of legacy values during transition.
       return state === NODE_STATE.READY || state === 'ready' || state === 'running'
   }
   
   export function stateClass(state) {
       // Returns CSS class — 'state-ready', 'state-booting', etc.
       return `state-${(state || 'unknown').toLowerCase()}`
   }
   
   export function stateLabel(state) {
       // Returns operator-friendly label — 'Ready', 'Booting', etc.
       return (state || 'unknown').toLowerCase().replace(/^./, c => c.toUpperCase())
   }
   ```
2. **In `sp-cli-nodes-view.js`** — replace every `state === 'running'` with `isRunning(state)`. Replace every state-comparison or state-string-display with the helpers. Code review identified 6 sites; verify with grep.
3. **Sweep other components** for state-string hardcoding: `sp-cli-stacks-pane.js`, `sp-cli-compute-view.js`, any `*-detail.js`. Replace.
4. **CSS** — define `.state-booting`, `.state-ready`, `.state-terminating`, `.state-terminated`, `.state-failed` classes in `admin/admin.css` (or a shared `state.css`). Use semantic colours from `tokens.css` (`--color-success` for ready, `--color-warning` for booting/terminating, `--color-danger` for failed).
5. **Test** — manually verify against a running node + a booting node + a terminated node. Boot-log poll cessation works on both `'ready'` and legacy `'running'`.

## Acceptance criteria

- `shared/node-state.js` exists with `NODE_STATE`, `isRunning`, `stateClass`, `stateLabel`.
- `grep -rn "=== 'running'\|=== 'pending'" sgraph_ai_service_playwright__api_site/` returns zero hits (or only inside `node-state.js` itself for back-compat).
- Manual smoke test passes for the three states.
- Snapshot tests updated.

## Open questions

- **Canonical state values.** BV2.2 documents `Enum__Node__State` values. Mirror the casing exactly (`BOOTING`, `READY`, etc.). If they're lowercase, update the helper.

## Blocks / Blocked by

- **Blocks:** none — this is a defensive fix.
- **Blocked by:** none. Run any time. **Recommended first** because it's tight, unblocked, and removes a latent bug.

## Notes

The helper is **deliberately tolerant** of legacy values during the transition window. Once BV2.2 confirms canonical values are returned by `/api/nodes`, the helper can be tightened in a follow-up.
