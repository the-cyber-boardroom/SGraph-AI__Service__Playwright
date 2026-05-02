# UI Architect — Pass 1: Code Tour & 04/29 Brief Audit

**Date:** 2026-05-01
**Version:** v0.1.140
**Branch:** `claude/ui-architect-agent-Cg0kG`
**Author:** UI / Frontend Architect (agent, Pass 1 of 2)
**Scope:** Pass 1 — UI surface tour + audit of the 04/29 fractal-UI briefs against shipped code.
**Out of scope:** Pass 2 covers the 05/01 briefs and the boundary/scope synthesis. Anything written there is intentionally not duplicated here.

This document is read-only review. No code changes were made.

---

## 1. What the UI is today (code-verified)

### 1.1 The shell

- Landing page: `sgraph_ai_service_playwright__api_site/index.html:1-95` — three plain anchor cards (Admin Dashboard, User Provisioning, API Docs). Inline CSS, no web components, no sg-layout. Just hero + three `<a class="card">`.
- Admin shell: `sgraph_ai_service_playwright__api_site/admin/index.html:1-72` — top-bar + a single `<sg-layout id="root-layout">` + `<sg-auth-panel>`. Imports ~30 web components as ES modules. This is where the fractal admin UI lives.
- Page controller: `sgraph_ai_service_playwright__api_site/admin/admin.js:1-367` — initialises root layout from `_buildRootLayout()`, wires the full event vocabulary (nav, stacks, plugin toggles, launch flow, ui-panel toggles, region change), and mediates tab open/close. **Vault is no longer a gate** (since `e34c2e6`); layout boots immediately and vault connection is additive (`admin.js:50-57`).
- User shell: `sgraph_ai_service_playwright__api_site/user/index.html` + `user.js` (untouched by the 04/29 brief; out of scope for this rebuild).
- Python wiring: `sgraph_ai_service_playwright__api_site/__init__.py:1-2` is a 2-line module locator; the FastAPI service mounts the directory as a static site (no SSR).

### 1.2 The `sp-cli-*` web component family — `components/sp-cli/`

Top-level components (one paragraph each, role only):

| Directory | Role |
|---|---|
| `sp-cli-top-bar/` | Header bar with title + slotted region picker + slotted vault picker. |
| `sp-cli-left-nav/` | Vertical icon-rail; emits `sp-cli:nav.selected` for compute/storage/settings/diagnostics/api. |
| `sp-cli-region-picker/` | Region dropdown; emits `sp-cli:region-changed`. |
| `sp-cli-vault-picker/` | Vault key picker; bridges to `vault-bus.js`. |
| `sp-cli-vault-status/` | Right-info-column panel showing vault state. |
| `sp-cli-vault-activity/` | Legacy vault-trace pane (predecessor of events-log). |
| `sp-cli-events-log/` | Live DOM-event trace (right info column); generalised vault-activity. |
| `sp-cli-active-sessions/` | Right info panel; placeholder per brief. |
| `sp-cli-cost-tracker/` | Right info panel; mocked cost calculation per brief. |
| `sp-cli-compute-view/` | Main column compute view; currently hosts the stacks pane (and absorbs the launcher pane via composition). |
| `sp-cli-storage-view/` | Main column storage placeholder. |
| `sp-cli-settings-view/` | Main column settings panel; renders plugin toggles, ui-panel toggles, defaults. |
| `sp-cli-diagnostics-view/` | Main column diagnostics placeholder. |
| `sp-cli-api-view/` | Main column API-docs view (added in `c5566d2`, not in the original brief). |
| `sp-cli-launcher-pane/` | Renders one card per enabled plugin; reacts to `sp-cli:plugin.toggled`. |
| `sp-cli-launch-panel/` | The tab-mounted launch form (rename-replacement of the modal). |
| `sp-cli-launch-modal/` | Deprecated modal; still on disk, header tagged `@deprecated`. |
| `sp-cli-stacks-pane/` | Active-stacks list; emits `sp-cli:stack-selected`. |
| `sp-cli-stack-detail/` | Legacy generic detail; superseded by per-plugin detail components. |
| `sp-cli-vnc-viewer/` | Legacy 5-state remote-browser; superseded by `sg-remote-browser`. |
| `sp-cli-{linux,docker,podman,elastic,vnc,prometheus,opensearch,neko,firefox}-detail/` | Per-plugin detail panels — composed of `_shared/` widgets. |
| `sp-cli-catalog-pane/` | Older catalog grid; surfaces deprecated `sp-cli:catalog-launch` event. |
| `sp-cli-activity-pane/` | Application-level audit log (not the events log). |
| `sp-cli-user-pane/` | User-page launcher pane; emits deprecated `sp-cli:user-launch`. |

Shared widgets at `components/sp-cli/_shared/`:

- `sg-remote-browser/` — promoted from `sp-cli-vnc-viewer`, supports `provider="vnc|iframe|neko|auto"`. Source: `components/sp-cli/_shared/sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js:1-60+`.
- `sp-cli-stack-header/`, `sp-cli-status-chip/`, `sp-cli-stop-button/`, `sp-cli-launch-form/`, `sp-cli-ssm-command/`, `sp-cli-network-info/` — the widget catalogue from doc 02. All present.

### 1.3 The `plugins/` folder

Per-plugin folders, each with a launcher card (and detail components live under `components/sp-cli/sp-cli-{name}-detail/`):

```
plugins/{name}/v0/v0.1/v0.1.0/sp-cli-{name}-card.{js,html,css}
```

Plugins present: `docker`, `podman`, `elastic`, `vnc`, `prometheus`, `opensearch`, `neko`, `firefox`, plus a stale `linux/` card folder still on disk (replaced conceptually by `podman`).

There is **no manifest/registry file**. Plugin discovery is convention-based:

- `sp-cli-launcher-pane.js:4` defines a hard-coded `PLUGIN_ORDER = ['docker','podman','elastic','vnc','prometheus','opensearch','neko','firefox']`.
- `admin.js:126` defines `LAUNCH_TYPES = [...]` as a parallel hard-coded list for wiring `sp-cli:plugin:{name}.launch-requested` listeners.
- `settings-bus.js:11-20` lists the same 8 plugin names in `DEFAULTS.plugins`.
- `admin/index.html:30-47` hard-codes one `<script type="module">` per card and detail file.

These four lists are the de-facto registry. Adding a plugin requires four parallel edits.

### 1.4 `shared/`, `admin/`, `user/`

- `shared/` — five JS modules (`api-client.js`, `vault-bus.js`, `settings-bus.js`, `catalog.js`, `poll.js`), `tokens.css`, plus a `components/` subdir with seven Tools-style composites (`sg-api-client.js`, `sg-auth-panel.js`, `sg-create-modal.js`, `sg-header.js`, `sg-stack-card.js`, `sg-stack-grid.js`, `sg-toast-host.js`). `settings-bus.js:1-138` is the new feature-toggle singleton from PR-3. The `shared/components/` subdir predates the brief and contains the user-page composites.
- `admin/` — three files: `index.html`, `admin.js`, `admin.css`. `admin.js` is the page controller described in 1.1; it is ~370 lines including helpers and matches the doc-02 wiring sketch closely.
- `user/` — three files: `index.html`, `user.js`, `user.css`. Still uses the legacy `sp-cli:user-launch` event and `<sp-cli-user-pane>` (`user.js:40`). Untouched by the 04/29 brief and intentionally out of scope.

### 1.5 Components read in full (file:line refs)

- `sgraph_ai_service_playwright__api_site/admin/admin.js:1-367`
- `sgraph_ai_service_playwright__api_site/admin/index.html:1-72`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/sp-cli-top-bar.js:1-40`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/sp-cli-left-nav.js:1-46`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launch-panel/v0/v0.1/v0.1.0/sp-cli-launch-panel.js:1-60`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launcher-pane/v0/v0.1/v0.1.0/sp-cli-launcher-pane.js:1-43`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/sp-cli-firefox-detail.js:1-60`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-podman-detail/v0/v0.1/v0.1.0/sp-cli-podman-detail.js:1-44`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-vnc-detail/v0/v0.1/v0.1.0/sp-cli-vnc-detail.js:1-40`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.js:1-142`
- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-events-log/v0/v0.1/v0.1.0/sp-cli-events-log.js:1-60+`
- `sgraph_ai_service_playwright__api_site/plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js:1-30`
- `sgraph_ai_service_playwright__api_site/shared/settings-bus.js:1-138`

---

## 2. Patterns & boundaries observed (the implicit contract)

These are the conventions the codebase enforces today. Future UI work must respect them.

- **Triple-versioned folder layout** — every component lives at `{name}/v0/v0.1/v0.1.0/{name}.{js,html,css}`. The version directories are real (not aliases). Example: `components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/sp-cli-left-nav.js`.
- **Three-file SgComponent pattern** — `.js` (logic), `.html` (template), `.css` (styles), siblings in the version leaf. The base class is imported by URL: `https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js` (see e.g. `sp-cli-left-nav.js:11`).
- **Custom-element naming** — `sp-cli-{kebab-case}` for SP-CLI components, `sg-{kebab}` for promoted-to-Tools generics (`sg-remote-browser`, `sg-auth-panel`). `customElements.define()` at the bottom of every JS file (e.g. `sp-cli-left-nav.js:45`).
- **No build toolchain** — native ES modules, every dependency resolved via relative path or absolute Tools URL. `admin/index.html:24-69` is one `<script type="module">` per component, in dependency order.
- **Shadow-DOM `$()` accessor** — every component reads its template via `this.$('.selector')` in `onReady()` (see `sp-cli-podman-detail.js:14-18`).
- **Pending-stack pattern** — detail components stash an early `open(stack)` call in `this._pendingStack` if `onReady()` has not yet fired (`sp-cli-firefox-detail.js:21,25`, `sp-cli-vnc-detail.js:21,25`, `sp-cli-podman-detail.js:18,22`). This is a load-order race resolution, not Type_Safe ergonomics.
- **Event dispatch on `document`** — components dispatch `new CustomEvent(name, { detail, bubbles: true, composed: true })` on `document` (see `settings-bus.js:135` and `sp-cli-left-nav.js:31-34`). The page controller listens on `document` and does not reach into shadow DOMs.
- **Event vocabulary** — `{family}:{action}` for top-level (e.g. `vault:connected`), `sp-cli:{noun}.{verb}` for app events (`sp-cli:nav.selected`), `sp-cli:plugin:{name}.{verb}` for plugin events (`sp-cli:plugin:firefox.launch-requested`), and back-compat aliases with hyphens kept alongside (`admin.js:75-80`).
- **Tag-based plugin discovery** — `sp-cli-launcher-pane.js:35-37` instantiates `document.createElement('sp-cli-{name}-card')` from a name list. `admin.js:226` opens detail tabs by `sp-cli-{stack.type_id}-detail`. Cards and details register globally via `customElements.define()` and the page controller never touches their classes directly.
- **Layout state** — root layout JSON is built dynamically by `admin.js:_buildRootLayout()` (lines 16-31), persisted on `LAYOUT_CHANGED` to `localStorage` under key `sp-cli:admin:root-layout:v1` (`admin.js:7,202-204`). Reset is `localStorage.removeItem` + reload (`sp-cli-settings-view.js:120-123`).
- **No imports between plugins** — confirmed: `plugins/firefox/...` and `plugins/podman/...` import only from `_shared/` widgets and `shared/api-client.js`, never from another plugin.
- **CSS strategy** — `sg-tokens.css` from Tools (`sharedCssPaths` getter on every component) plus a per-component `.css`. No global stylesheet beyond `tokens.css` and `admin/admin.css`.
- **No-modal rule with one residual** — `grep "position: fixed"` returns one hit only in the deprecated `sp-cli-launch-modal/sp-cli-launch-modal.css:4`. All live code paths use sg-layout tabs.
- **Preferences live in vault** — `settings-bus.js:7` writes to `sp-cli/preferences.json` with `schema_version: 2` and a v1→v2 migration path (`settings-bus.js:106-123`).

---

## 3. Recently merged UI changes (since the 04/29 briefs)

`git log 5a6b542..origin/dev -- sgraph_ai_service_playwright__api_site/`:

| Commit | Subject | What changed in UI tree | Risks / out-of-pattern? |
|---|---|---|---|
| `092f069` | feat: add sp-cli-firefox-card and sp-cli-firefox-detail UI components | Added `plugins/firefox/v0/v0.1/v0.1.0/{js,html,css}` for card; added `components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/{js,html,css}`; added 1 line each to `admin.js` (LAUNCH_TYPES) and `index.html` (script tags); test file updated. | Clean — follows the per-plugin folder pattern exactly. |
| `c5566d2` | fix bugs + add firefox card + API docs nav button | Added `<sp-cli-api-view>` (the API docs view); added a 5th left-nav item `data-view="api"` (`sp-cli-left-nav.html:23-26`); minor fixes in `sp-cli-launch-form.js`, `sp-cli-status-chip.js`, `sp-cli-launcher-pane.js`, `settings-bus.js` (added firefox to defaults). | Slight scope creep: the 04/29 brief specified four nav items (Compute/Storage/Settings/Diagnostics). API was added unilaterally and is referenced as a fifth view in `admin.js:33,308,323`. Not in the brief, not bad, but deserves explicit blessing. |
| `2fc3d1d` | ui: fix stop button placement + API view white background | Tweaked CSS and HTML for every detail component to give the stop button a footer placement (`docker-detail`, `elastic-detail`, `firefox-detail`, `linux-detail`, `neko-detail`, `opensearch-detail`, `podman-detail`, `prometheus-detail`, `stack-detail`, `vnc-detail`) and fixed `sp-cli-api-view.css`. | Pure visual polish, no contract changes. Touches the legacy `sp-cli-stack-detail` too — that file is supposedly going away (PR-7 in the implementation plan), so the patch is wasted but not harmful. |
| `3f1b75d` | feat: add Podman plugin card + detail to UI | Added `plugins/podman/...` card and `components/sp-cli/sp-cli-podman-detail/...`; added podman to `LAUNCH_TYPES` and `PLUGIN_ORDER` and `settings-bus.js` defaults; `Plugin__Registry.py` and manifest tests updated. | Clean. The five-place plugin-list duplication (PLUGIN_ORDER + LAUNCH_TYPES + DEFAULTS + index.html scripts + Plugin__Registry) is increasingly visible as a maintenance issue but every site was updated. |
| `e34c2e6` | feat: remove vault gate — dashboard loads immediately, vault is optional | `admin/admin.js:50-67` boots layout immediately and treats vault as additive; `admin/admin.css` simplified; `admin/index.html` lost the gate template block. | Material UX change, well-isolated. The brief did not call for vault-gating either way — this aligns with "vault optional" pragmatism but is not in any of the 04/29 briefs. |
| `ba122af` | merge: sync with dev — podman replaces linux, resolve conflict | Conflict-resolution merge for the podman track. `sgraph_ai_service_playwright__api_site/` unaffected aside from previously merged podman files. | n/a |

**Branch-merged check:** `git log origin/dev..origin/claude/setup-dev-agent-ui-titBw` returned **zero unmerged commits**. The original `claude/setup-dev-agent-ui-titBw` branch (vault gate removal + 8-type plugin registry) is fully absorbed into `dev`.

---

## 4. Implemented-vs-spec audit of the 04/29 fractal-UI briefs

Each subsection: brief item → status → file evidence.

### 4.1 `01__visual-design.md`

| Section / concept | Status | Evidence |
|---|---|---|
| 3-column root layout (Left Nav / Main / Right Info) using `<sg-layout>` | DONE | `admin/admin.js:23-30`, `admin/index.html:18` |
| Layout-state persisted to `localStorage` on `LAYOUT_CHANGED` | DONE | `admin.js:7,202-204` |
| Left Nav with Compute / Storage / Settings / Diagnostics | DONE | `sp-cli-left-nav.html:1-22` |
| Left Nav additional API item (5th) | DONE-but-extra (not in brief) | `sp-cli-left-nav.html:23-26` |
| Compute view — launcher row + active stacks pane | PARTIAL | `sp-cli-compute-view.js:1-19` only hosts stacks pane; launcher is rendered separately and not vertically stacked the way the brief drew. Visual structure differs from the doc-01 ASCII. |
| Launcher pane reads `/catalog/types`, filters by toggles, renders one card per enabled plugin | PARTIAL | `sp-cli-launcher-pane.js:25-39` filters by toggles but uses **hard-coded `PLUGIN_ORDER`**, not catalog response. `admin.js:268-272` does fetch catalog/types but only forwards to compute-view as `setData({types,stacks})`. Catalog→card wiring is incomplete. |
| Launch flow as a tab, not a modal | DONE | `admin.js:237-252` opens a launch tab; `sp-cli-launch-panel.js:1-60` is a normal panel; old modal CSS only present in deprecated dir. |
| Per-type instance details — Linux, Docker, Elastic, VNC, Prometheus, OpenSearch, Neko | DONE for 8 types (incl. firefox + podman) | `components/sp-cli/sp-cli-{linux,docker,podman,elastic,vnc,prometheus,opensearch,neko,firefox}-detail/` all present |
| Linux detail composition (header + ssm + network + resource + activity + stop) | PARTIAL | `sp-cli-linux-detail` exists; `_shared/sp-cli-resource-details` and `_shared/sp-cli-recent-activity` not present in `_shared/` listing. |
| Elastic detail with two-column sg-layout + Kibana embed via `<sg-remote-browser>` | PROPOSED — does not exist yet | `sp-cli-elastic-detail.js` does not import `sg-remote-browser` (verified by grep). Single-column composition only. |
| VNC detail = full-panel `<sg-remote-browser>` | DONE | `sp-cli-vnc-detail.js:7,19-20` imports and uses `sg-remote-browser`. |
| Storage view placeholder | DONE | `components/sp-cli/sp-cli-storage-view/` exists. |
| Settings view with plugin toggles + UI panel toggles + defaults + reset layout | DONE | `sp-cli-settings-view.js:36-141` |
| Diagnostics view placeholder | DONE | `components/sp-cli/sp-cli-diagnostics-view/` exists. |
| Right info column — Events Log / Vault Status / Active Sessions / Cost Tracker | DONE | `admin.js:9-14` (`RIGHT_PANELS`) and four corresponding component dirs. |
| Plugin stability badges | DONE | `sp-cli-firefox-card.js:18-19`, `sp-cli-settings-view.js:81` |
| Empty-state / loading / error treatments | PARTIAL | `sp-cli-launcher-pane.js:32-33` handles empty enabled list; broader error states inconsistent. |

### 4.2 `02__component-architecture.md`

| Section / concept | Status | Evidence |
|---|---|---|
| `_shared/` widgets: stack-header, status-chip, stop-button, launch-form, ssm-command, network-info | DONE | `components/sp-cli/_shared/{sp-cli-stack-header,sp-cli-status-chip,sp-cli-stop-button,sp-cli-launch-form,sp-cli-ssm-command,sp-cli-network-info}/` |
| `<sg-remote-browser>` in `_shared/` with provider attribute (vnc/iframe/neko/auto) | DONE | `_shared/sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js:1-60+` |
| `<sg-remote-browser>` API `open({url, auth, provider, stackName})` | DONE | doc comment at `sg-remote-browser.js:6-11`; used by `sp-cli-firefox-detail.js:52-55` and `sp-cli-vnc-detail.js`. |
| Frontend plugin folders mirror backend (`api_site/plugins/{name}/`) | DONE for 9 plugins | `plugins/{docker,podman,linux,elastic,vnc,prometheus,opensearch,neko,firefox}/...`. Note the stale `plugins/linux/` is on disk and can be cleaned up. |
| Each plugin folder contains `card.{js,html,css}` and `detail.{js,html,css}` | PARTIAL | Cards live under `plugins/{name}/...`; details live under `components/sp-cli/sp-cli-{name}-detail/...` (NOT the brief's plan to put both inside `plugins/{name}/`). Functionally equivalent, structurally divergent. |
| `<sp-cli-launch-panel>` as rename-replacement of `<sp-cli-launch-modal>` | DONE | `sp-cli-launch-panel/v0/v0.1/v0.1.0/sp-cli-launch-panel.js:1-60`; modal kept on disk with `@deprecated` header at `sp-cli-launch-modal.js:1`. |
| Old `<sp-cli-stack-detail>` deleted | PROPOSED — does not exist yet | `components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/{js,html,css}` still present and was even patched by `2fc3d1d`. |
| Old `<sp-cli-vnc-viewer>` deleted | PROPOSED — does not exist yet | Still present at `components/sp-cli/sp-cli-vnc-viewer/v0/v0.1/v0.1.0/`. |
| Page-controller event wiring matches doc 02 sketch | DONE | `admin/admin.js:46-183` is a near-1:1 implementation (layout init, nav switch, openLaunchTab, openDetailTab, plugin-toggle close-detail-tab logic, ui-panel toggle, region change, auth, stop/delete). |
| Plugin discovery driven by catalog response | PROPOSED — does not exist yet | Hard-coded `PLUGIN_ORDER` at `sp-cli-launcher-pane.js:4`; catalog response fetched but not used by launcher. |
| `imports.js` aggregator OR per-plugin script tags | DONE (chose script tags) | `admin/index.html:30-67` — explicit `<script type="module">` per plugin and view. |

### 4.3 `03__event-vocabulary.md`

| Section / concept | Status | Evidence |
|---|---|---|
| Vault events (`vault:connected`, `vault:disconnected`) preserved | DONE | `admin.js:61`, `settings-bus.js:38-39` |
| Vault-bus trace events (`sp-cli:vault-bus:read-*`, `write-*`) preserved | DONE | listed in `sp-cli-events-log.js:15-19` |
| `sp-cli:stack.selected` (dotted) with `sp-cli:stack-selected` (hyphen) compat | DONE | `admin.js:75-76` |
| `sp-cli:stack.deleted` with hyphen compat | DONE | `admin.js:77-78` |
| `sp-cli:stacks.refresh` with hyphen compat | DONE | `admin.js:79-80` |
| `sp-cli:plugin:{name}.launch-requested` | DONE | `admin.js:126-129`, `sp-cli-firefox-card.js:26` |
| Deprecated `sp-cli:catalog-launch` / `sp-cli:user-launch` still firing for back-compat | DONE | `sp-cli-catalog-pane.js:50`, `sp-cli-user-pane.js:68`, listened for at `admin.js:130-131` |
| `sp-cli:launch.success` / `sp-cli:launch.error` (dotted) with hyphen compat | DONE | `admin.js:133-154` |
| `sp-cli:launch.cancelled` | DONE | `admin.js:156-162` |
| `sp-cli:nav.selected` | DONE | `sp-cli-left-nav.js:31-34` → listened at `admin.js:71` |
| `sp-cli:plugin.toggled` | DONE | `settings-bus.js:74` → `admin.js:85-100` |
| `sp-cli:ui-panel.toggled` | DONE | `settings-bus.js:81` → `admin.js:104-118` |
| `sp-cli:settings.saved` / `sp-cli:settings.loaded` | DONE | `settings-bus.js:52,99` |
| `sp-cli:region-changed` | DONE | `admin.js:81` |
| Auth events (`sg-auth-required` / `sg-show-auth` / `sg-auth-saved`) | DONE | `admin.js:122,275-277` |
| `sp-cli:brand-clicked` | DONE | `sp-cli-top-bar.js:36-38` |
| Plugin-specific events (`sp-cli:plugin:elastic.import-requested` etc.) | PROPOSED — does not exist yet | grep finds no emitters. |
| `sg-remote-browser:state.changed` / `sg-remote-browser:fallback-applied` | DONE (declared) | doc comment `sg-remote-browser.js:21-23`; emission verified in component body (out of scope for full-read). |
| `sp-cli:detail-closed` | PROPOSED — does not exist yet | grep finds no emitter. |
| `sp-cli:activity-entry` for application audit log | DONE | `admin.js:288-292` |

### 4.4 `04__feature-toggles.md`

| Section / concept | Status | Evidence |
|---|---|---|
| `shared/settings-bus.js` singleton | DONE | `shared/settings-bus.js:1-138` |
| Vault path `sp-cli/preferences.json` | DONE | `settings-bus.js:7` |
| `schema_version: 2` defaults shape | DONE | `settings-bus.js:9-32` |
| v1 → v2 migration | DONE | `settings-bus.js:106-123` |
| Defaults merged on load (so new plugin keys fill in) | DONE | `_mergeDefaults` at `settings-bus.js:125-132` |
| Read-only vault behaviour: in-memory toggle + warning toast | DONE | `settings-bus.js:92-103` |
| Read-only banner in Settings view | DONE | `sp-cli-settings-view.js:43,116-118` |
| Closing detail tabs when plugin disabled | DONE | `admin.js:85-100` |
| Closing launch tab when plugin disabled | DONE | `admin.js:96-99` |
| UI-panel visibility toggle (hide/show right-column section live) | PARTIAL | `admin.js:104-118` removes the panel on disable but on re-enable shows a toast asking the user to "Reset Layout in Settings" rather than re-creating it. Live re-show is not implemented. |
| Default values plumbed through to launch panel (`getDefault`) | DONE | `sp-cli-launch-panel.js:3,34` (`getAllDefaults()`); Settings view writes back via `setDefault` (lines 50-52). |
| Multi-tab live cross-sync | PROPOSED — does not exist yet (and out of scope per brief) | n/a |
| Plugin name set matches brief (linux/docker/elastic/vnc/prometheus/opensearch/neko) | DIFFERS | `settings-bus.js:11-20` ships **8 types**: docker, podman, elastic, vnc, prometheus, opensearch, neko, firefox. `linux` was retired in favour of `podman`; `firefox` was added. |

### 4.5 `05__implementation-plan.md`

| PR | Status | Evidence |
|---|---|---|
| PR-1 — Top-level layout shell + Left Nav + view stubs | DONE | `admin/admin.js`, `admin/index.html`, `sp-cli-left-nav`, `sp-cli-compute-view`, `sp-cli-storage-view`, `sp-cli-settings-view`, `sp-cli-diagnostics-view` all present. |
| PR-2 — `_shared/` widgets + `<sg-remote-browser>` | DONE | All seven `_shared/` directories present. |
| PR-3 — Settings panel + `settings-bus.js` | DONE | `shared/settings-bus.js`, `sp-cli-settings-view`. |
| PR-4 — Launch flow as tab + plugin launcher cards | DONE for 8 plugins | `sp-cli-launch-panel`, `sp-cli-launcher-pane`, `plugins/{docker,podman,elastic,vnc,prometheus,opensearch,neko,firefox}/...` cards all present. |
| PR-5 — Per-plugin detail components (linux/docker/elastic/vnc/prometheus/opensearch) | PARTIAL | All 6 brief-listed details exist plus podman/firefox/neko. Brief required deleting `<sp-cli-stack-detail>` — still on disk. Brief required Elastic/Prometheus/OpenSearch with split-column + sg-remote-browser — not yet wired (verified for elastic). |
| PR-6 — Right info column components | DONE | `sp-cli-events-log`, `sp-cli-vault-status`, `sp-cli-active-sessions`, `sp-cli-cost-tracker` all present. |
| PR-7 — Polish + reality doc + smoke test | PARTIAL | Reality doc has shards through `15__sp-cli-ui-dev-agent-dashboard.md` but no `*-fractal-rebuild.md` slice yet. Deprecated components (vnc-viewer, launch-modal, stack-detail, vault-activity) still on disk. |

**Headline percentage:** ~70-75% of the 04/29 vision is shipped in code. The structural skeleton is live; the gaps are (a) per-plugin detail composition divergence (Elastic/Prometheus/OpenSearch don't yet embed `sg-remote-browser`), (b) catalog-driven plugin discovery still hard-coded in five places, (c) deprecated components not yet deleted, (d) plugin-specific `import-requested`/`screenshot-requested` events reserved-but-unimplemented.

---

## 6. Open questions for Pass 2

These are flagged for the sibling agent that handles the 05/01 briefs and the boundary/scope statement. Pass 2 should decide what is in-scope vs. deferred and whether the divergences below are accepted as-is.

- **Plugin registry duplication.** Adding a plugin requires edits in five places: `PLUGIN_ORDER` (`sp-cli-launcher-pane.js:4`), `LAUNCH_TYPES` (`admin.js:126`), `settings-bus.js` `DEFAULTS.plugins`, `admin/index.html` script tags, and backend `Plugin__Registry`. The brief promised "data-driven plugin discovery from `/catalog/types`". Should Pass 2 codify a single source of truth (e.g. `shared/plugin-manifest.js`)?
- **`linux` vs `podman` plugin naming.** Brief lists `linux` everywhere; reality has `podman` (with stale `plugins/linux/` and `sp-cli-linux-detail/` still on disk). Settings-bus defaults dropped `linux`. Confirm whether the linux artefacts should be removed or kept for back-compat.
- **`firefox` and `api` views are out-of-brief additions.** The 04/29 brief specified seven plugins (linux/docker/elastic/vnc/prometheus/opensearch/neko) and four nav items. Code now has eight plugins (incl. firefox) and five nav items (incl. API docs). Pass 2 should decide whether to update the brief or roll back.
- **Plugin-folder structure divergence.** Brief said `plugins/{name}/` should hold both `card` and `detail`. Reality keeps card under `plugins/{name}/...` and detail under `components/sp-cli/sp-cli-{name}-detail/...`. Pick one and document it.
- **Elastic/Prometheus/OpenSearch detail composition.** Brief specified split-column layout with `<sg-remote-browser>`. Reality has single-column details without remote-browser embedding. Plug-and-play work item; trivial to do once the brief is ratified.
- **Deprecated components on disk.** `sp-cli-vnc-viewer`, `sp-cli-launch-modal`, `sp-cli-stack-detail`, `sp-cli-vault-activity`, `sp-cli-catalog-pane`, `sp-cli-user-pane` still present. Some are referenced by the user page; the brief's "deprecate for one release" path is not formally tracked.
- **Reserved-but-unimplemented events.** `sp-cli:plugin:elastic.{import,export,screenshot}-requested`, `sp-cli:plugin:playwright.*`, `sp-cli:detail-closed`, `sp-cli:plugin:vnc.viewer-mode-toggled` are documented in the brief and reserved in convention but have no emitters or listeners. Pass 2 should confirm these stay reserved or get exercised.
- **UI-panel re-show UX.** `admin.js:112-117` requires a layout reset to re-show a hidden right-panel. Brief implied live re-show. Either fix or revise the brief.
- **Vault gate removal.** `e34c2e6` removed the vault gate but the brief assumed a vault-required boot path. Pass 2 should reconcile the read-only / vault-optional behaviour with the doc-04 read-only banner story.
- **Reality doc shard for the fractal rebuild.** `team/roles/librarian/reality/v0.1.31/` has no shard for the fractal-UI rebuild yet. Filing a `16__sp-cli-fractal-ui-rebuild.md` (or numbered next slot) would close the PR-7 acceptance.
