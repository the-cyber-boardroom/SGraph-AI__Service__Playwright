# 05 — Implementation Plan

**Status:** PROPOSED
**Read after:** all of `00`–`04`
**Audience:** Sonnet planning the PR sequence

---

## What this doc gives you

The PR sequence in dependency order, files touched per PR, acceptance per PR. Roughly 7 PRs, 7–10 dev-days for one frontend developer.

## Pre-flight

Working from a clean branch off `dev`:

```bash
git checkout dev && git pull
git checkout -b claude/v0_22_19_frontend_fractal_ui
```

Read these existing files before starting — they're the patterns you're building on:

| File | Read for |
|---|---|
| `sgraph_ai_service_playwright__api_site/admin/admin.js` | Current page controller pattern (event wiring, `_loadData`, layout handling) |
| `sgraph_ai_service_playwright__api_site/admin/index.html` | Existing top-bar slot + sg-layout root pattern |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-vnc-viewer/v0/v0.1/v0.1.0/sp-cli-vnc-viewer.js` | The 5-state machine you're promoting to `<sg-remote-browser>` |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launch-modal/v0/v0.1/v0.1.0/sp-cli-launch-modal.js` | Logic to preserve when refactoring to `<sp-cli-launch-panel>` |
| `sgraph_ai_service_playwright__api_site/shared/vault-bus.js` | Existing vault helpers (`vaultReadJson`, `vaultWriteJson`, `isWritable`) |
| Reality doc `team/roles/librarian/reality/v0.1.31/14__sp-cli-ui-sg-layout-vnc-wiring.md` | What's currently shipped on the SP-CLI UI surface |

## Pull the test vault

The previous brief's empirical-verification section established a live test vault. Reuse it:

```bash
pip3 install sgit-ai --break-system-packages
mkdir -p sp-cli-test && cd sp-cli-test
sgit --base-url https://dev.send.sgraph.ai clone beam-idle-0930
# Vault key: beam-idle-0930
# Access token: graphs-and-maps  (needed for writes only)
```

You can use this vault to:
- Inspect canonical `sp-cli/preferences.json` shape
- Test settings-bus persistence end-to-end
- Verify your `<sp-cli-events-log>` records reads and writes correctly

---

## PR sequence

```
PR-1   Top-level layout shell + Left Nav + view stubs           ◀── start here
  │
PR-2   _shared/ widgets + sg-remote-browser                     ◀── parallel possible after PR-1
  │
PR-3   Settings panel + settings-bus.js                         ◀── needs PR-1
  │
PR-4   Launch flow as tab + plugin folders (cards)              ◀── needs PR-2 (for shared launch-form)
  │
PR-5   Per-plugin detail components                             ◀── needs PR-2, PR-4
  │
PR-6   Right info column (events log, vault status, etc.)        ◀── parallel possible after PR-1
  │
PR-7   Polish + reality doc + smoke test                         ◀── all of the above
```

PR-2 and PR-6 are loosely coupled to the others — they can run in parallel with PR-3/PR-4 once PR-1 lands.

---

## PR-1 — Top-level layout shell + Left Nav + view stubs

**Goal:** the new 3-column layout exists. Left Nav clicks switch the main column between Compute / Storage / Settings / Diagnostics views. **Each view is a stub.** Vault picker and top-bar are slotted in. Nothing functional beyond navigation works yet.

### Files touched

- `admin/index.html` — replace existing single-column layout with a single root `<sg-layout id="root-layout">`.
- `admin/admin.js` — page controller scaffold per doc 02's wiring sketch. Initialises root layout from `ROOT_LAYOUT` JSON, wires `vault:connected` gate, wires `sp-cli:nav.selected` to swap the main column tab.
- `admin/admin.css` — minimal layout CSS. Most styling comes from sg-tokens.

### Files created

- `components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/sp-cli-left-nav.{js,html,css}` — vertical icon-rail with 4 items
- `components/sp-cli/sp-cli-compute-view/v0/v0.1/v0.1.0/sp-cli-compute-view.{js,html,css}` — stub (renders "Compute view")
- `components/sp-cli/sp-cli-storage-view/v0/v0.1/v0.1.0/sp-cli-storage-view.{js,html,css}` — placeholder per doc 01
- `components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.{js,html,css}` — stub (rendered in PR-3)
- `components/sp-cli/sp-cli-diagnostics-view/v0/v0.1/v0.1.0/sp-cli-diagnostics-view.{js,html,css}` — placeholder per doc 01

### Acceptance

- Navigate to `/admin/`. Vault gate shows. Connect vault.
- Page renders the 3-column layout: left nav (~64px), main column (default = compute stub), right column with 4 stacked panels (placeholder content).
- Click each Left Nav item → main column updates accordingly.
- Drag the splitters → resize works.
- Reload → splitter positions preserved.
- `LAYOUT_KEY` is `sp-cli:admin:root-layout:v1` (new value invalidating older saved layouts).

### Effort

**1–1.5 days.** Most of this is wiring the layout shell. The view stubs are minimal.

---

## PR-2 — `_shared/` widgets + `<sg-remote-browser>`

**Goal:** the shared widget catalogue exists. `<sg-remote-browser>` is the promoted version of `<sp-cli-vnc-viewer>` working for both VNC and iframe modes.

### Files created

In `components/sp-cli/_shared/`:

- `sp-cli-stack-header/v0/v0.1/v0.1.0/...` — name + status chip + uptime; standard composition for all detail views
- `sp-cli-status-chip/v0/v0.1/v0.1.0/...` — `●Ready` / `◐Boot` / `●Failed` / `○Stopped` with colour coding from sg-tokens
- `sp-cli-stop-button/v0/v0.1/v0.1.0/...` — button with inline confirm row (the existing pattern from `<sp-cli-stack-detail>`)
- `sp-cli-launch-form/v0/v0.1/v0.1.0/...` — form fields (stack name, region, instance type, max hours, advanced); used by `<sp-cli-launch-panel>` in PR-4
- `sp-cli-ssm-command/v0/v0.1/v0.1.0/...` — read-only `<input>` with the SSM command + copy button
- `sp-cli-network-info/v0/v0.1/v0.1.0/...` — public IP, allowed IP, security group ID
- `sg-remote-browser/v0/v0.1/v0.1.0/...` — promoted from `<sp-cli-vnc-viewer>`, generic API per doc 02

### `<sg-remote-browser>` specifics

- Migrate the existing `<sp-cli-vnc-viewer>` source to `_shared/sg-remote-browser/`.
- Replace the `open(stack, password)` API with `open({ url, auth, provider, stackName })`.
- Add `provider` attribute: `'vnc' | 'neko' | 'iframe' | 'auto'`.
- For `'auto'`: try iframe first (just embed the URL). On iframe `error` event or X-Frame-Options block, fall back to `'vnc'` mode and run the existing 5-state machine.
- For `'neko'`: stub state showing "Neko provider not yet supported. See evaluation brief."
- For `'iframe'`: trivial direct embed, no states.
- Preserve all existing state-machine behaviour for `provider='vnc'` (so the existing VNC instance detail still works).
- Fire `sg-remote-browser:state.changed` and `sg-remote-browser:fallback-applied`.

### Acceptance

- Each `_shared/` widget renders standalone in a test page.
- `<sg-remote-browser provider="vnc" url="..." stack-name="...">` works exactly as today's `<sp-cli-vnc-viewer>` did (5-state machine, password input, cert-trust prompt, iframe).
- `<sg-remote-browser provider="iframe" url="https://example.com">` embeds directly.
- `<sg-remote-browser provider="auto" url="https://kibana-blocked-by-xfo">` falls back to VNC mode after iframe fails.
- The old `<sp-cli-vnc-viewer>` is deprecated (kept for one release; admin.js uses the new component).
- `grep -r "sp-cli-vnc-viewer" components/sp-cli/` returns hits only in the deprecated component itself and historical reality docs.

### Effort

**1.5 days.** The widget shells are quick (15–30 min each). `<sg-remote-browser>` is the substantive work — ~half a day to extract from the existing component, plus testing the iframe-fallback path.

---

## PR-3 — Settings panel + settings-bus.js

**Goal:** the Settings view renders all toggles. Toggling a plugin fires `sp-cli:plugin.toggled` and persists to vault. `settings-bus.js` exists as a singleton.

### Files created

- `shared/settings-bus.js` — full implementation per doc 04
- `components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.{js,html,css}` — full implementation per doc 01

### Files touched

- `admin/admin.js` — call `startSettingsBus()` after `startVaultBus()`. Add `sp-cli:plugin.toggled` listener for the close-detail-tab logic per doc 04.

### Tests / verification

- Connect vault. Settings view renders with all default toggles.
- Toggle a plugin off → wait <100ms → fire activity-log entry visible in events log.
- Refresh page → toggle state preserved.
- Connect with vault key only (no access token). Toggle → toast warns "won't persist."
- Open a Linux detail tab. Disable Linux. Tab closes with toast.

### Acceptance

- `sp-cli/preferences.json` in the test vault is created on first toggle, with `schema_version: 2` and the right shape.
- Multi-tab sanity: toggle in one tab, switch to another tab → settings reload happens after vault reconnect (manual reconnect needed; cross-tab live sync is out of scope).
- v1 → v2 migration works if a v1 file exists in vault.

### Effort

**1.5 days.** `settings-bus.js` is straightforward (~120 lines). The Settings UI is the bulk — the toggle list, the "UI panels" section, the "Defaults" section, the [Reset layout] button, the read-only banner.

---

## PR-4 — Launch flow as tab + plugin launcher cards

**Goal:** `<sp-cli-launch-panel>` exists. Launcher pane reads catalog + settings, renders one card per enabled plugin via per-plugin `<sp-cli-{name}-card>` components. Click [Launch] → opens a tab in the main column with the launch form.

### Files created

- `components/sp-cli/sp-cli-launcher-pane/v0/v0.1/v0.1.0/sp-cli-launcher-pane.{js,html,css}`
- `components/sp-cli/sp-cli-launch-panel/v0/v0.1/v0.1.0/sp-cli-launch-panel.{js,html,css}` — refactored from `<sp-cli-launch-modal>`
- For each of `linux`, `docker`, `elastic`, `vnc`, `prometheus`, `opensearch`, `neko`:
  - `plugins/{name}/v0/v0.1/v0.1.0/sp-cli-{name}-card.{js,html,css}` — launcher card, per-plugin

### Files touched

- `components/sp-cli/sp-cli-compute-view/...` — stub becomes real: includes launcher pane (top) + stacks pane (bottom)
- `admin/admin.js` — add `_openLaunchTab(entry)` per doc 02
- `admin/index.html` — add a single `<script type="module" src="../plugins/imports.js">` that imports all per-plugin card files. Or one import per plugin if simpler.

### `<sp-cli-launch-panel>` refactor

The existing `<sp-cli-launch-modal>` is renamed and:

- `position: fixed` and `backdrop` removed
- Container is a normal `<div>` filling its sg-layout panel
- Lifecycle: `open(entry)` populates the form; `submit` posts to `entry.create_endpoint_path`; on success fires `sp-cli:launch.success` and the page controller closes the tab; on error stays open with the error.
- Esc/Cancel: fires `sp-cli:launch-cancelled` (new event), page controller closes the tab.

### `<sp-cli-{name}-card>` shape

Each card is ~50 lines. Per doc 02. Imports `<sp-cli-status-chip>` for the "stable/experimental" badge from `_shared/`.

### Acceptance

- Compute view renders launcher cards for enabled plugins (read from catalog + settings).
- Click [Launch] on Linux → tab "Launching Linux" opens in the main column. Form pre-filled with default region / instance type / max hours from settings-bus.
- Submit → tab title becomes "Launching Linux — submitting…" → success → tab auto-closes after 2s → new stack visible in stacks pane.
- Submit error → tab stays open, error rendered, [Retry] visible.
- Re-clicking [Launch] for a type that already has an open launch tab → focuses the existing tab (no duplicate).
- Close a launch tab manually (× button) → no API call cancellation needed (the request continues in the background; if it succeeds, the new stack appears anyway).
- `grep -r "position: fixed" components/sp-cli/sp-cli-launch-panel/` → zero hits.
- `grep -r "position: fixed" components/sp-cli/` → zero hits in non-deprecated code.

### Effort

**1.5 days.** Refactoring the launch flow is most of the work. The cards are repetitive (one template, six instances).

---

## PR-5 — Per-plugin detail components

**Goal:** each plugin has its own detail component. Click a stack row → opens type-specific detail tab.

### Files created

For each of `linux`, `docker`, `elastic`, `vnc`, `prometheus`, `opensearch`:

- `plugins/{name}/v0/v0.1/v0.1.0/sp-cli-{name}-detail.{js,html,css}` per doc 01

For Neko: skip — stays as a SOON tile, no detail view yet.

### Files touched

- `admin/admin.js` — `_openDetailTab(stack)` looks up `sp-cli-${stack.type_id}-detail` and creates the tab
- Delete `components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/...` — replaced by per-plugin variants
- Update tests / smoke tests as needed

### Per-plugin detail composition (per doc 01)

- **`sp-cli-linux-detail`**: header + ssm-command + network-info + resource-details + recent-activity + stop-button. Single column.
- **`sp-cli-docker-detail`**: same as Linux + container list.
- **`sp-cli-elastic-detail`**: two-column sg-layout. Left: header + endpoints list + container list + operations buttons (stub events) + stop. Right: `<sg-remote-browser provider="auto" url="{kibana_url}">`.
- **`sp-cli-vnc-detail`**: slim header bar + `<sg-remote-browser provider="vnc" url="{viewer_url}" stack-name="{name}">`.
- **`sp-cli-prometheus-detail`**: same shape as Elastic, Grafana endpoint instead of Kibana.
- **`sp-cli-opensearch-detail`**: same shape as Elastic.

### Acceptance

- Click a Linux stack row → Linux detail tab opens with SSM command, network info, stop button.
- Click an Elastic stack row → Elastic detail tab opens with split layout, Kibana embed appears.
- Click a VNC stack row → VNC detail tab opens with full-panel remote browser (same UX as today's `<sp-cli-vnc-viewer>` but in the tab).
- Switch between detail tabs → state preserved per tab (e.g. VNC keeps its iframe alive).
- Close a detail tab → fires `sp-cli:detail-closed` for cleanup hooks.
- Old `<sp-cli-stack-detail>` deleted. `grep -r "sp-cli-stack-detail" components/` → zero hits.

### Effort

**1.5 days.** Linux/Docker details are quick (~80 lines each). Elastic/Prometheus/OpenSearch need the iframe-or-remote-browser logic. VNC is a slim wrapper around the existing component.

---

## PR-6 — Right info column

**Goal:** the right column's 4 panels — events log, vault status, active sessions, cost tracker — all render with their respective behaviours.

### Files created / refactored

- `components/sp-cli/sp-cli-events-log/v0/v0.1/v0.1.0/...` — generalised version of the existing `<sp-cli-vault-activity>`. Listens for **all** `sp-cli:*`, `vault:*`, and `sg-*` events on document. Filter dropdown lets the operator narrow.
- `components/sp-cli/sp-cli-vault-status/v0/v0.1/v0.1.0/...` — reads from `vault-bus.js`'s `currentVault()`, listens for vault events to update.
- `components/sp-cli/sp-cli-active-sessions/v0/v0.1/v0.1.0/...` — placeholder showing the current operator's session.
- `components/sp-cli/sp-cli-cost-tracker/v0/v0.1/v0.1.0/...` — placeholder with mocked cost calculation.

### Acceptance

- Events log shows every event firing in real time. Filter dropdown narrows to: All / Vault / Stacks / Plugins / Errors.
- Vault status updates immediately on connect/disconnect/reconnect.
- Active sessions shows "this browser" with start time.
- Cost tracker shows mocked total based on running stacks × instance type rates.
- Toggle a panel off in Settings → it disappears from the right column. Toggle on → it reappears.

### Effort

**1 day.** Events log is the substantive work (it generalises an existing component). The other three are slim presentational components.

---

## PR-7 — Polish + reality doc + smoke test

**Goal:** integration verification, deprecation cleanup, reality doc updated, all the rough edges addressed.

### Files touched

- `team/roles/librarian/reality/v0.1.{N}/{NN}__sp-cli-ui-fractal-rebuild.md` — new reality doc capturing what shipped.
- Deprecate `<sp-cli-vnc-viewer>`, `<sp-cli-launch-modal>`, `<sp-cli-stack-detail>`, `<sp-cli-vault-activity>` (the latter renamed `<sp-cli-events-log>` is the surviving version). Remove these from the admin page; keep their files for one release with a deprecation header comment.
- Update existing tests that reference the deprecated components.
- Manual smoke test walkthrough — see below.

### Smoke test walkthrough

1. Open `/admin/` fresh browser. Connect vault `beam-idle-0930` with token `graphs-and-maps`.
2. 3-column layout renders. Left nav: Compute selected by default.
3. Drag the right-column splitter → resize. Reload → preserved.
4. Click [Launch] on Linux. Tab "Launching Linux" opens. Submit. New stack appears in the stacks pane.
5. Click the new Linux stack. Linux detail tab opens with SSM command. Click [Stop]. Inline confirm appears. Confirm. Stack disappears.
6. Click Settings (left nav). Toggle Neko on. Toggle Prometheus on.
7. Switch to Compute view. Neko and Prometheus cards now appear. Both are SOON tiles.
8. Toggle Neko off. Card disappears.
9. Click [Launch] on VNC. Submit. ~90 seconds later, VNC stack appears as Ready.
10. Click VNC stack. VNC detail tab opens, full-panel remote browser, runs through the existing 5-state machine.
11. Check Events Log on the right — every step above should have left a trail.
12. Reload page → vault auto-reconnects, layout preserved, all settings preserved.

### Acceptance

- All 15 acceptance criteria from `00__README__frontend-fractal-ui.md` pass.
- Reality doc filed.
- Test suite green.
- No `position: fixed` modal patterns.
- No console errors during the smoke walkthrough.
- The brief-vault has the new brief committed alongside the old one.

### Effort

**1 day.** Mostly verification + documentation.

---

## Final acceptance — across the full brief

When all 7 PRs are merged, a reviewer should be able to confirm all 15 of the acceptance criteria from `00__README__frontend-fractal-ui.md`. Most importantly:

- The 3-column layout renders.
- The Left Nav switches main views.
- Launch flow is **a tab, not a modal**.
- Per-plugin detail components exist and look different from each other.
- Settings panel toggles plugins live.
- `<sg-remote-browser>` is shared and used by multiple plugins.
- Frontend folder structure mirrors backend conceptually (`api_site/plugins/{name}/`).

If any fails, the brief is not done.

## Total effort

7–10 dev-days for one frontend developer. Bigger if the developer is unfamiliar with `SgComponent` or `<sg-layout>`. The largest risks remain:

1. **Layout migration** — the existing v3 layout won't be compatible with the new root layout; using `sp-cli:admin:root-layout:v1` (new key) for the root naturally invalidates without affecting users in mid-session.
2. **Launch-as-tab UX** — operators are used to the modal; the tab-based flow needs the auto-close-on-success behaviour to feel right.
3. **Per-type detail divergence** — resist over-genericising the detail views. Each type genuinely has different needs.
