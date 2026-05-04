# v0.22.19 — Fractal Frontend: sg-layout Based Infrastructure UI

**Brief:** Frontend rebuild around fractal panels, plugin folders, no-modals
**Status:** PROPOSED — ready for Sonnet pickup
**Target version:** v0.22.19 (slice numbering will land in `team/comms/briefs/v0.22.19__fractal-frontend-ui/`)
**Date drafted:** 2026-04-29
**Author:** Architect (Opus session, agreed with project lead)
**Audience:** Sonnet (frontend track), Architect, Designer
**Source memo:** `team/humans/dinis_cruz/briefs/v0.22.19__dev-brief__fractal-frontend-infrastructure-ui.md`
**Backend counterpart:** `v0.22.19__backend-plugin-architecture/` (separate Sonnet track)

---

## What this brief is

A structural rebuild of the SP-CLI admin dashboard around five principles:

1. **Every screen is self-contained.** No modal dialogs. No popups. Each view is a panel that can be resized, collapsed, or rearranged.
2. **Everything is sg-layout.** Top-level layout contains sg-layouts. Those contain sg-layouts. Fractal nesting gives drag-and-drop, resizing, responsive behaviour for free.
3. **Everything is event-driven.** Components fire events. Other components listen. If nobody listens, the event is silently dropped.
4. **Feature toggles control everything.** Settings panel toggles plugins live. Disabled plugins disappear from the launcher.
5. **Frontend mirrors backend.** Per-plugin folders parallel the backend plugin folders. Common components live in `_shared/`.

After this brief lands:

1. The admin dashboard's top-level layout becomes **3 columns**: Left Navigation (Compute / Storage / Settings / Diagnostics) / Main Panel / Right Panel (Events Log + Vault Status + Active Sessions + Cost Tracker).
2. The launch flow stops being a modal. It becomes a **launcher panel inside the Compute view**.
3. Each plugin gets a **frontend folder** (`api_site/plugins/{name}/`) with its launcher card and its instance detail view. Instance detail views are **per-type sg-layouts** — Elastic gets Kibana embed; Playwright gets screenshot viewer; VNC fills the panel.
4. A **Settings panel** with feature toggles controls which plugins appear in the launcher.
5. A **`<sg-remote-browser>`** shared component (Neko-or-VNC iframe wrapper) is used by any plugin whose target service blocks iframe embedding.

After this brief explicitly does **NOT** land:

- ❌ The user page (`/user/`) being rebuilt. **Admin first; user is a follow-up.**
- ❌ Neko adoption — only the `<sg-remote-browser>` abstraction with VNC behind it. Neko swap-in is gated by the backend's experiment doc.
- ❌ Cost Tracker as a working component (it's a placeholder with mocked data — real cost calculation needs backend changes).
- ❌ Vault Browser ("Storage" nav item) as a working component — placeholder until the vault-store backend is fleshed out.
- ❌ Replacement of `vault-bus.js` or the existing vault picker — those stay.
- ❌ Replacement of the existing top-bar (`<sp-cli-top-bar>`) — it stays, slotted into the new layout.

## How to read this series

| # | Doc | Read when | Approx size |
|---|---|---|---|
| `00` | [`00__README__frontend-fractal-ui.md`](00__README__frontend-fractal-ui.md) *(this file)* | First — orientation | ~150 lines |
| `01` | [`visual-design.md`](01__visual-design.md) | When designing or building any panel | ~400 lines |
| `02` | [`component-architecture.md`](02__component-architecture.md) | When wiring components, naming files, picking imports | ~350 lines |
| `03` | [`event-vocabulary.md`](03__event-vocabulary.md) | When choosing event names or wiring listeners | ~200 lines |
| `04` | [`feature-toggles.md`](04__feature-toggles.md) | When implementing the Settings panel and toggle logic | ~150 lines |
| `05` | [`implementation-plan.md`](05__implementation-plan.md) | When picking the next PR to ship | ~200 lines |

Total ~1,450 lines.

## Key decisions (made — do not relitigate)

| # | Decision | Rationale |
|---|---|---|
| 1 | **No modal dialogs anywhere.** Launch flow becomes a panel; confirmations become inline (the way `<sp-cli-stack-detail>` already does Delete confirm). | Source memo principle #5. Modals interrupt flow; sg-layout's whole point is many things visible at once. |
| 2 | **Top-level layout is 3 columns** (Left Nav, Main, Right Info). Each column itself uses sg-layout. | Source memo. The current 3-column admin layout (Catalog / Stacks+Activity / Vault Activity+Detail) maps neatly onto this — see doc 01 for the migration. |
| 3 | **Frontend plugin folders mirror backend conceptually, not physically.** Frontend stays in `api_site/`, structured as `api_site/plugins/{name}/...` mirroring `cli/{name}/`. No repo-wide reorg. | Discussed in agreement. Physical mirror would require restructuring the whole repo for limited UX gain. |
| 4 | **Per-type instance detail components.** `<sp-cli-elastic-detail>`, `<sp-cli-playwright-detail>`, etc. Replaces the current single `<sp-cli-stack-detail>` with type-specific composition. | Each compute type has a different centre of gravity (Kibana for Elastic, screenshots for Playwright, full-panel iframe for VNC). One generic component is mediocre at all of them. |
| 5 | **Shared sub-components live in `components/sp-cli/_shared/`.** Things like `<sp-cli-stack-header>`, `<sp-cli-stop-button>`, `<sp-cli-status-chip>` — used by every per-type detail. | "Components shared, layouts diverge." Each plugin's detail composes shared widgets in its own arrangement. |
| 6 | **`<sg-remote-browser>` is a core component, not a plugin one.** It wraps Neko or VNC in an iframe with the existing 5-state machine (`empty → not-running → cert → auth → ready`). Used by any plugin whose target blocks iframe embedding. | Source memo: "the remote browser is shared across plugins." Promotes the existing `<sp-cli-vnc-viewer>` 5-state pattern to a generic shared component. |
| 7 | **Feature toggles persist to the vault** (preference path `sp-cli/preferences.json` already exists). Read on page load; written on toggle change. | The vault is the persistent state layer per the previous brief. Reuse the same path. |
| 8 | **Existing components are preserved where possible.** `<sp-cli-top-bar>`, `<sp-cli-vault-picker>`, `<sp-cli-vault-activity>`, `<sp-cli-region-picker>`, `<sp-cli-launch-modal>` (renamed and refactored — see below), `<sp-cli-vnc-viewer>` (promoted to `<sg-remote-browser>`). | Don't rewrite what works. The brief is structural, not cosmetic. |
| 9 | **`<sp-cli-launch-modal>` is renamed `<sp-cli-launch-panel>` and rendered as a tab in the main panel, not a modal.** Click "Launch Linux" → a tab opens in the main panel containing the launch form. Submit → tab closes, stack appears in the stacks pane. | Direct application of decision #1. The component logic barely changes — just the rendering frame. |
| 10 | **The user page (`/user/`) is left alone in this brief.** Admin first. User page rebuild is a follow-up brief that can reuse all the components. | Scope discipline. The admin page is where the structural work matters most. |

## Layering rules (non-negotiable)

1. **No modals.** No `position: fixed; backdrop;` patterns. Anything that wants to be a modal becomes a tab in the main panel or an inline section in an existing panel.
2. **Components communicate via DOM events** with the `{family}:{action}` naming. New plugin-specific events use `sp-cli:{plugin}:{noun}.{verb}` (matching the backend convention).
3. **No imports between plugins.** `plugins/elastic/*` does not import from `plugins/vnc/*`. Cross-plugin communication via events.
4. **Shared components in `_shared/`.** Plugins import from `_shared/` and from Tools (`https://dev.tools.sgraph.ai/...`).
5. **Plugin discovery is data-driven.** The launcher renders cards based on the catalog response from the backend (`GET /catalog/types`). Adding a new compute type = backend adds a plugin = frontend reads the new entry from the catalog and discovers the matching frontend plugin folder.
6. **No new build toolchain.** Native ES modules, no bundler, three-file `SgComponent` pattern (existing rule).
7. **Vault is the persistence layer.** Preferences, feature-toggle settings, layout state all live in vault paths under `sp-cli/`.

## Acceptance for "this brief is done"

A reviewer should be able to confirm all of these:

1. The admin dashboard renders with **3 columns** at top level: Left Nav, Main, Right Info. Each column uses `<sg-layout>`.
2. The Left Nav has 4 items: **Compute, Storage, Settings, Diagnostics**. Clicking changes what the Main column displays.
3. **Compute view** (default) shows: Launcher cards row, Active Stacks pane.
4. Clicking **Launch** on a type card opens a **tab in the Main column** (NOT a modal) containing the launch form. Submitting the form closes the tab and the new stack appears in the stacks pane.
5. Clicking a stack row opens the **per-type detail** in a tab — Elastic detail looks different from Playwright detail looks different from VNC detail.
6. **Settings view** has feature toggles for each plugin. Toggling Neko on/off shows/hides its launcher card in the Compute view immediately, no page reload.
7. The toggle state persists across page reloads (read from / written to `sp-cli/preferences.json`).
8. **Right Info column** has 4 stacked panels: Events Log (live), Vault Status, Active Sessions, Cost Tracker (placeholder).
9. Events Log shows events firing in real time — at minimum: `vault:connected`, `sp-cli:plugin.toggled`, `sp-cli:stack.launched`, `sp-cli:stack.deleted`.
10. Disabling a plugin via Settings → its launcher card disappears, and any open detail tabs for that type are closed.
11. **No `position: fixed; z-index: 1000;` modal patterns** anywhere in the new code. `grep -r "position: fixed" components/sp-cli/` returns hits only in the existing `<sp-cli-launch-modal>` if it's not yet refactored — by end of brief, that's gone.
12. The frontend folder structure mirrors the backend: `api_site/plugins/{linux,docker,elastic,vnc,prometheus,opensearch,neko}/` with launcher card and detail components per plugin.
13. Each plugin's frontend folder contains: `card.js` (launcher card), `detail.js` (instance detail view), and a per-plugin events documentation file.
14. `<sg-remote-browser>` exists in `components/sp-cli/_shared/` and is used by at least the VNC plugin's detail view (via composition).
15. Existing components preserved: `<sp-cli-top-bar>`, `<sp-cli-vault-picker>`, `<sp-cli-vault-activity>`, `<sp-cli-region-picker>`. They slot into the new layout unchanged.

If any fails, the brief is not done.

## Effort estimate

Roughly 7–10 dev-days for one frontend developer:

- 1d — Top-level 3-column layout, Left Nav, Right Info column scaffold
- 1d — `_shared/` components (`sp-cli-stack-header`, `sp-cli-status-chip`, `sp-cli-stop-button`, `sp-cli-launch-form`)
- 1d — `<sg-remote-browser>` (promote `<sp-cli-vnc-viewer>` to generic, add Neko-fallback hooks)
- 0.5d — Launch flow rebuilt as tab-not-modal (`<sp-cli-launch-panel>`)
- 1d — Per-plugin frontend folders for the 6 existing types (linux/docker/elastic/vnc/prometheus/opensearch)
- 1d — Per-type instance detail views (Elastic with Kibana embed, Playwright with screenshot, VNC with full-panel)
- 1d — Settings panel with feature toggles + vault persistence
- 0.5d — Events Log right-panel component listening for `sp-cli:*` and `vault:*` events
- 0.5d — Vault Status, Active Sessions, Cost Tracker placeholders
- 0.5d — Compute / Storage / Diagnostics view shells (Storage and Diagnostics are stubs)
- 0.5d — Polish: ensure layout state persists, no console errors, smoke test
- 0.5d — Tests + acceptance walkthrough

The largest risks are:
- **Layout migration.** The current admin dashboard layout already uses sg-layout but in a different shape. The migration must preserve user-saved layouts (use a new `LAYOUT_KEY` value to invalidate the old one — already done before with `v3`).
- **Launch-as-tab UX.** Running through the launch flow without a modal is a behaviour change for operators. Make sure the tab closes after submit, the focus returns sensibly, the new stack is selected.
- **Per-type detail divergence.** The brief asks for **specific** Elastic/Playwright/VNC layouts. Avoid the temptation to make them generic — that defeats the point.

## What ships after this brief

In probable priority order:

1. **User page rebuild** using the same components and patterns.
2. **Storage view** (vault browser, S3 status) — once the backend supports it.
3. **Diagnostics view** (real-time API status, error log) — uses backend events.
4. **Cost Tracker** with real cost calculation — needs backend instrumentation.
5. **Per-instance FastAPI integration** (when the backend's per-instance brief lands) — exec console, instance-side log streaming.
6. **Neko swap-in** (when the backend's experiment recommends).

Each gets its own brief.

## Coordination with the backend track

The backend brief is being implemented in parallel. **Point of contact: `GET /catalog/types` response shape.** As long as it returns enabled plugins with their metadata, the frontend doesn't care whether the backend is plugin-driven or hand-mounted. So the two tracks don't block each other.

Optional new fields the frontend will use **if** the backend exposes them (degrade gracefully if absent):
- `stability: 'stable' | 'experimental' | 'deprecated'` — drives the "experimental" badge on Settings toggles
- `event_topics_emitted: list[str]` — for the Events Log filter dropdown

Both fields are optional. If the backend brief lands first, great. If the frontend brief lands first, those fields are absent and the UI just doesn't show that information.
