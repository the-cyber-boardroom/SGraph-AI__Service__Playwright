# v0.1.140 — Post-Fractal-UI: Frontend Cleanup & Extensions

**Status:** PROPOSED
**Owner:** Dev (UI) + UI Architect (review)
**Audience:** the frontend team
**Paired with:** [`team/comms/briefs/v0.1.140__post-fractal-ui__backend/`](../v0.1.140__post-fractal-ui__backend/) — items 01, 02, 03 here block on the matching backend contracts there.
**Source:** UI Architect orientation review at `team/humans/dinis_cruz/claude-code-web/05/01/15/ui-architect__pass-1__code-and-implementation.md` and `…__pass-2__scope-and-new-briefs.md`.

---

## Why this brief exists

The fractal-UI rebuild is ~70-75% landed at v0.1.140. The remaining work splits into:

- **Three contract-blocked items.** The dashboard cannot finish until the backend publishes the matching contracts. These are sequenced behind the four backend topics (manifest, launch payload, firefox endpoints, vault writes).
- **Two unblocked items.** A cleanup pass (linux→podman residue, deprecated components, sg-remote-browser embedding, card-label consistency, plugin-folder structure) that the frontend team can do now without backend coordination, plus a governance decision on out-of-brief additions (firefox plugin, API nav item).

Each topic is a separate file with a consistent shape: Goal / Today / Required output / Acceptance / Open questions / Paired-with.

---

## Items in this brief

| # | Topic | File | Backend counterpart | Blocked? |
|---|-------|------|----------------------|---------|
| 1 | Plugin manifest loader (delete the 5-place duplication) | `01__plugin-manifest-loader.md` | `backend/01__plugin-manifest-endpoint.md` | YES |
| 2 | Launch flow — three creation modes | `02__launch-flow-three-modes.md` | `backend/02__stack-creation-payload-modes.md` | YES |
| 3 | Firefox configuration column (5 sub-panels) | `03__firefox-configuration-column.md` | `backend/03__firefox-config-endpoints.md` + `04__vault-write-contract.md` | YES |
| 4 | Cleanup pass | `04__cleanup-pass.md` | — | NO — start now |
| 5 | Governance — out-of-brief additions, event vocabulary | `05__governance-decisions.md` | — | NO — decision-only |

---

## Constraints

- No build toolchain. Native ES modules. Every component is `.js` + `.html` + `.css` siblings under `{name}/v0/v0.1/v0.1.0/`.
- Every component extends the imported `sg-component` base from the Tools URL referenced in existing components.
- Custom-element naming: `sp-cli-{kebab}` for SP-CLI; `sg-{kebab}` for promoted-to-Tools generics.
- Events dispatched on `document` with `{ bubbles: true, composed: true }`. No reaching into shadow DOM from the page controller.
- Preferences live in the user vault under `sp-cli/preferences.json` via `settings-bus.js` (`schema_version: 2`).
- Briefs folder is human-only — agents do not write there. Implementation notes go to `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/`.

---

## Lifecycle

1. Each topic file lands as a UI Architect review under `team/roles/ui-architect/reviews/MM/DD/` (folder to be created — see UI Architect ROLE.md proposal in pass-2 of the orientation review).
2. Frontend Dev implements; merges land on `dev` after green tests.
3. Items 1-3 unblock as the matching backend brief lands. Items 4-5 can land in parallel from day one.
4. Each merged item is added to the UI fragment of the reality doc (`team/roles/librarian/reality/v{version}/...`) and this brief is moved to `team/comms/briefs/archive/` with the closing-commit hash appended.
