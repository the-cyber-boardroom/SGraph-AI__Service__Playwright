# 02 — Component Architecture

**Status:** PROPOSED
**Read after:** `00__README__frontend-fractal-ui.md`, `01__visual-design.md`

---

## What this doc gives you

The full file tree. Per-component contracts. The `_shared/` widget catalogue. The `<sg-remote-browser>` design (promoted from the existing `<sp-cli-vnc-viewer>`). The page-controller wiring.

## The dependency model — same as before, with one addition

```
                ┌────────────────────────────────┐
                │  Tools (canonical)             │
                │  https://dev.tools.sgraph.ai   │
                └────────────────────────────────┘
                              ▲
                              │ imported by URL
                              │
                ┌─────────────┴──────────────────┐
                │  api_site/components/sp-cli/   │
                │                                │
                │  ├── _shared/                  │  ← shared widgets used by all plugins
                │  │   sp-cli-stack-header       │
                │  │   sp-cli-stop-button        │
                │  │   sp-cli-status-chip        │
                │  │   sp-cli-launch-form        │
                │  │   sp-cli-ssm-command        │
                │  │   sp-cli-network-info       │
                │  │   sg-remote-browser         │
                │  │                             │
                │  ├── (existing top-level):     │  ← preserved
                │  │   sp-cli-top-bar            │
                │  │   sp-cli-vault-picker       │
                │  │   sp-cli-region-picker      │
                │  │   sp-cli-vault-activity     │  → renamed sp-cli-events-log
                │  │                             │
                │  └── (new chrome):             │
                │      sp-cli-left-nav           │
                │      sp-cli-compute-view       │
                │      sp-cli-storage-view       │
                │      sp-cli-settings-view      │
                │      sp-cli-diagnostics-view   │
                │      sp-cli-launcher-pane      │
                │      sp-cli-stacks-pane        │  ← exists, refactored
                │      sp-cli-launch-panel       │  ← rename of sp-cli-launch-modal
                │      sp-cli-events-log         │
                │      sp-cli-vault-status       │
                │      sp-cli-active-sessions    │
                │      sp-cli-cost-tracker       │
                └────────────────────────────────┘
                              ▲
                              │ imported by tag-based discovery
                              │
                ┌─────────────┴──────────────────┐
                │  api_site/plugins/             │  ← NEW: per-plugin folders
                │                                │
                │  ├── linux/                    │
                │  │   sp-cli-linux-card         │  → launcher card
                │  │   sp-cli-linux-detail       │  → instance detail
                │  │                             │
                │  ├── docker/                   │
                │  ├── elastic/                  │
                │  ├── vnc/                      │
                │  ├── prometheus/               │
                │  ├── opensearch/               │
                │  └── neko/                     │  → soon-tile only this brief
                └────────────────────────────────┘
```

The plugin folders are **discovered by convention**. The launcher pane reads the catalog response, and for each enabled plugin, expects a `sp-cli-{plugin}-card` web component to exist (registered globally via the plugin's `card.js`). Same for `sp-cli-{plugin}-detail`. Plugin folders are loaded eagerly on page load (the components register themselves; if the plugin's not enabled in settings, its card just isn't rendered).

## The full file tree

```
sgraph_ai_service_playwright__api_site/
├── index.html                       Landing page → /admin/ /user/
├── style.css                        Existing (kept)
│
├── admin/
│   ├── index.html                   Admin shell with top-bar + 3-column sg-layout
│   ├── admin.js                     Page controller — see "Page controller wiring"
│   └── admin.css                    Admin layout — minimal
│
├── user/
│   └── ...                          Untouched in this brief
│
├── shared/
│   ├── api-client.js                Existing (kept)
│   ├── poll.js                      Existing (kept)
│   ├── catalog.js                   Existing (kept)
│   ├── vault-bus.js                 Existing (kept)
│   └── settings-bus.js              ← NEW: feature-toggle state, see doc 04
│
└── components/sp-cli/
    │
    ├── _shared/                                                          ← NEW
    │   ├── sp-cli-stack-header/v0/v0.1/v0.1.0/...                       (status chip + name + uptime)
    │   ├── sp-cli-stop-button/v0/v0.1/v0.1.0/...                        (stop with inline confirm)
    │   ├── sp-cli-status-chip/v0/v0.1/v0.1.0/...                        (●Ready / ◐Boot / ●Failed)
    │   ├── sp-cli-launch-form/v0/v0.1/v0.1.0/...                        (form fields used by sp-cli-launch-panel)
    │   ├── sp-cli-ssm-command/v0/v0.1/v0.1.0/...                        (SSM command + copy button)
    │   ├── sp-cli-network-info/v0/v0.1/v0.1.0/...                       (public IP + allowed IP + SG)
    │   └── sg-remote-browser/v0/v0.1/v0.1.0/...                         (promoted from sp-cli-vnc-viewer)
    │
    ├── sp-cli-top-bar/v0/v0.1/v0.1.0/...                                EXISTING (kept)
    ├── sp-cli-vault-picker/v0/v0.1/v0.1.0/...                           EXISTING (kept)
    ├── sp-cli-region-picker/v0/v0.1/v0.1.0/...                          EXISTING (kept)
    ├── sp-cli-vault-activity/v0/v0.1/v0.1.0/...                         EXISTING (kept; renamed sp-cli-events-log later)
    │
    ├── sp-cli-left-nav/v0/v0.1/v0.1.0/...                              ← NEW
    ├── sp-cli-compute-view/v0/v0.1/v0.1.0/...                          ← NEW
    ├── sp-cli-storage-view/v0/v0.1/v0.1.0/...                          ← NEW (placeholder)
    ├── sp-cli-settings-view/v0/v0.1/v0.1.0/...                         ← NEW
    ├── sp-cli-diagnostics-view/v0/v0.1/v0.1.0/...                      ← NEW (placeholder)
    │
    ├── sp-cli-launcher-pane/v0/v0.1/v0.1.0/...                         ← NEW
    ├── sp-cli-stacks-pane/v0/v0.1/v0.1.0/...                           EXISTING (refactored — see below)
    ├── sp-cli-launch-panel/v0/v0.1/v0.1.0/...                          ← rename of sp-cli-launch-modal
    │
    ├── sp-cli-events-log/v0/v0.1/v0.1.0/...                            ← NEW (or rename of sp-cli-vault-activity, generalised)
    ├── sp-cli-vault-status/v0/v0.1/v0.1.0/...                          ← NEW
    ├── sp-cli-active-sessions/v0/v0.1/v0.1.0/...                       ← NEW
    └── sp-cli-cost-tracker/v0/v0.1/v0.1.0/...                          ← NEW (placeholder)


sgraph_ai_service_playwright__api_site/plugins/                         ← NEW DIRECTORY
│
├── linux/v0/v0.1/v0.1.0/
│   ├── sp-cli-linux-card.js
│   ├── sp-cli-linux-card.html
│   ├── sp-cli-linux-card.css
│   ├── sp-cli-linux-detail.js                                          (composes _shared widgets)
│   ├── sp-cli-linux-detail.html
│   └── sp-cli-linux-detail.css
│
├── docker/v0/v0.1/v0.1.0/...                                           (mirror linux)
├── elastic/v0/v0.1/v0.1.0/...                                          (composes <sg-remote-browser> for Kibana)
├── vnc/v0/v0.1/v0.1.0/...                                              (composes <sg-remote-browser> full-panel)
├── prometheus/v0/v0.1/v0.1.0/...                                       (mirror elastic)
├── opensearch/v0/v0.1/v0.1.0/...                                       (mirror elastic; SOON tile)
└── neko/v0/v0.1/v0.1.0/...                                             (SOON tile only)
```

## Plugin folder structure — per plugin

Each plugin folder has the same shape:

```
plugins/{name}/v0/v0.1/v0.1.0/
├── sp-cli-{name}-card.js
├── sp-cli-{name}-card.html
├── sp-cli-{name}-card.css
├── sp-cli-{name}-detail.js
├── sp-cli-{name}-detail.html
└── sp-cli-{name}-detail.css
```

### `sp-cli-{name}-card`

Launcher card. Contract:

- **Properties**:
  - `entry: Schema__Stack__Type__Catalog__Entry` — the catalog data for this type
  - `available: boolean` — whether this is a "live" tile or a "soon" tile (also derivable from entry)
- **Events emitted**:
  - `sp-cli:plugin:{name}.launch-requested { entry }` — when [Launch] clicked
- **Inside**: type icon, display name, stability badge, expected boot time, [Launch] button or "soon" treatment.

Default-shape boilerplate that most plugins use is identical — only icon and name differ. The launcher pane could in fact use a single shared `<sp-cli-generic-card>` that takes the entry. But **the brief specifies per-plugin cards** so plugins can specialise (e.g. Elastic showing "Kibana + Elasticsearch" with two icons; VNC showing "browser-in-browser" with a desktop preview thumbnail). Stick with per-plugin cards.

### `sp-cli-{name}-detail`

Instance detail view. Composes `_shared/` widgets in a layout that fits this type. Contract:

- **Properties**:
  - `stack: object` — the full info from `GET /{type}/stack/{name}`
- **Events listened (on document)**:
  - `sp-cli:stack.deleted` — if the deleted stack matches, emit close-tab signal
- **Events emitted**:
  - `sp-cli:stack.stop-requested { stack }` — passes through from the embedded stop button
  - `sp-cli:detail-closed { stack }` — when the operator closes the tab (sg-layout fires the close; the detail listens via lifecycle disconnectedCallback)
  - Plugin-specific events (e.g. `sp-cli:elastic.import-requested`)

Per-plugin detail compositions:

- **`sp-cli-linux-detail`**: Stack header, SSM command, network info, resource details, recent activity, stop button. **Single column.**
- **`sp-cli-docker-detail`**: Same as Linux + container list (mostly visual — no extra functionality this brief).
- **`sp-cli-elastic-detail`**: Two-column sg-layout — left column with header + endpoints + container list + operations; right column with `<sg-remote-browser>` pointing at Kibana (auto-falls-back from iframe).
- **`sp-cli-vnc-detail`**: Slim toolbar (header + stop) + `<sg-remote-browser>` filling the rest.
- **`sp-cli-prometheus-detail`**: Same as Elastic with Grafana endpoint.
- **`sp-cli-opensearch-detail`**: Same as Elastic with OpenSearch dashboards.
- **`sp-cli-neko-detail`**: Just `<sg-remote-browser>` full-panel (when Neko goes available; for now disabled).

## `<sg-remote-browser>` — the promoted shared component

Today's `<sp-cli-vnc-viewer>` is already an embedded-iframe component with a 5-state machine (`empty → not-running → cert → auth → ready`). The brief **promotes it to `<sg-remote-browser>`** in `_shared/` so any plugin can compose it.

### What changes from `<sp-cli-vnc-viewer>`

- **Renamed** to `<sg-remote-browser>` (and lives in `_shared/sg-remote-browser/`).
- **Provider attribute** added: `provider="vnc"` or `provider="neko"` or `provider="iframe"`. For now `vnc` is the only working one; `neko` and `iframe` are stubs that delegate to the iframe pattern.
- **Generic open API**: instead of `open(stack, password)`, takes `open({ url, auth, provider })`:
  - `url` — the target URL to embed (e.g. Kibana, mitmweb, VNC viewer)
  - `auth` — `{type: 'basic', user, pass}` or `{type: 'token', token}` or null
  - `provider` — explicit provider hint
- **Iframe fallback**: when `provider='iframe'`, just embed directly. When `provider='vnc'`, do the existing 5-state flow.
- **`auto`** provider tries iframe first; on iframe error event (X-Frame-Options blocked), falls back to whatever the user has configured as remote-browser default (initially VNC; later Neko if the experiment recommends).

### Component contract

```javascript
// import in any detail view
import 'https://api/.../sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js'

// usage
<sg-remote-browser
    provider="auto"
    url="https://18.132.60.220:5601/"      ← Kibana endpoint
    stack-name="elastic-loud-noether"      ← for sessionStorage scoping (passwords, cert-trust)
></sg-remote-browser>
```

Events fired:
- `sg-remote-browser:state.changed { state, provider }` — for telemetry
- `sg-remote-browser:fallback-applied { from, to }` — when iframe fails and we fall back

### What ships first

In this brief: `provider='vnc'` works (it's the existing component) and `provider='iframe'` works (trivial direct embed). `provider='neko'` is a stub returning the cert/auth screen with "Not yet supported." `provider='auto'` tries iframe first; falls back to VNC for the existing VNC use case; reports unsupported for Neko.

The Neko branch is filled in by the **Neko evaluation brief** when that lands.

## Page-controller wiring (`admin.js`)

Lots of events in this design. Here's the wiring contract:

### Events the page controller listens for (high level)

```javascript
// Vault state
document.addEventListener('vault:connected', _onVaultConnected)
document.addEventListener('vault:disconnected', _onVaultDisconnected)

// Navigation
document.addEventListener('sp-cli:nav.selected', _onNavSelected)

// Plugin toggles
document.addEventListener('sp-cli:plugin.toggled', _onPluginToggled)

// Launch flow
document.addEventListener('sp-cli:plugin:linux.launch-requested',  e => _openLaunchTab(e.detail.entry))
document.addEventListener('sp-cli:plugin:docker.launch-requested', e => _openLaunchTab(e.detail.entry))
document.addEventListener('sp-cli:plugin:elastic.launch-requested', e => _openLaunchTab(e.detail.entry))
document.addEventListener('sp-cli:plugin:vnc.launch-requested',    e => _openLaunchTab(e.detail.entry))
document.addEventListener('sp-cli:launch-submitted', _onLaunchSubmit)
document.addEventListener('sp-cli:launch-success', _onLaunchSuccess)
document.addEventListener('sp-cli:launch-error', _onLaunchError)

// Stack interactions
document.addEventListener('sp-cli:stack.selected', e => _openDetailTab(e.detail.stack))
document.addEventListener('sp-cli:stack.stop-requested', _onStopRequested)
document.addEventListener('sp-cli:stack.deleted', _onStackDeleted)

// Refresh hints
document.addEventListener('sp-cli:stacks.refresh', _loadData)
document.addEventListener('sp-cli:region-changed', _onRegionChanged)
```

The full ~250-line controller is roughly:

```javascript
import { startVaultBus } from '../shared/vault-bus.js'
import { startSettingsBus } from '../shared/settings-bus.js'
import { apiClient } from '../shared/api-client.js'

import './imports.js'  // imports all sp-cli-* components and plugin/* components

const ROOT_LAYOUT_KEY = 'sp-cli:admin:root-layout:v1'

const ROOT_LAYOUT = {
    type: 'row', sizes: [0.07, 0.78, 0.15],
    children: [
        { type: 'stack', tabs: [{ tag: 'sp-cli-left-nav',     title: 'Nav', locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-compute-view', title: 'Compute', locked: true }] },
        { type: 'column', sizes: [0.30, 0.20, 0.20, 0.30], children: [
            { type: 'stack', tabs: [{ tag: 'sp-cli-events-log',      title: 'Events Log',      locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-vault-status',    title: 'Vault Status',    locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-active-sessions', title: 'Active Sessions', locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-cost-tracker',    title: 'Cost Tracker',    locked: true }] },
        ]},
    ],
}

document.addEventListener('DOMContentLoaded', async () => {
    let _layoutEl = null
    let _mainStackId = null
    let _currentView = 'compute'
    let _detailTabIds = {}     // stack_name → panelId, for detail tabs in main stack
    let _launchTabIds = {}     // entry.type_id → panelId, for launch tabs

    startVaultBus()
    startSettingsBus()

    // Wire all events as above ...
    
    async function _initLayout() {
        const sgLayoutMod = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')
        const sgLayoutEvents = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout-events.js')
        _layoutEl = document.querySelector('#root-layout')
        _layoutEl.setLayout(_loadLayout() || ROOT_LAYOUT)
        _mainStackId = _findStackWithTag(_layoutEl.getLayout(), 'sp-cli-compute-view')
        _layoutEl._events.on(sgLayoutEvents.SGL_EVENTS.LAYOUT_CHANGED, ({tree}) => {
            try { localStorage.setItem(ROOT_LAYOUT_KEY, JSON.stringify(tree)) } catch (_) {}
        })
    }

    function _onNavSelected(e) {
        const view = e.detail.view  // 'compute' | 'storage' | 'settings' | 'diagnostics'
        if (view === _currentView) return
        const targetTag = `sp-cli-${view}-view`
        // replace the main column's first tab
        _layoutEl.replaceTab(_mainStackId, 0, { tag: targetTag, title: _viewTitle(view), locked: true })
        _currentView = view
    }

    function _openLaunchTab(entry) {
        if (_launchTabIds[entry.type_id]) {
            _layoutEl.focusPanel(_launchTabIds[entry.type_id])
            return
        }
        const tabId = _layoutEl.addTabToStack(_mainStackId, {
            tag:    'sp-cli-launch-panel',
            title:  `Launching ${entry.display_name}`,
            locked: false,
        }, true)
        if (tabId) {
            _launchTabIds[entry.type_id] = tabId
            const el = _layoutEl.getPanelElement(tabId)
            el?.open(entry)
        }
    }

    function _openDetailTab(stack) {
        if (_detailTabIds[stack.stack_name]) {
            _layoutEl.focusPanel(_detailTabIds[stack.stack_name])
            return
        }
        const tabId = _layoutEl.addTabToStack(_mainStackId, {
            tag:    `sp-cli-${stack.type_id}-detail`,
            title:  `${stack.display_type} ${stack.stack_name}`,
            locked: false,
        }, true)
        if (tabId) {
            _detailTabIds[stack.stack_name] = tabId
            const el = _layoutEl.getPanelElement(tabId)
            el?.open(stack)
        }
    }

    // ...
})
```

The controller is ~250 lines but it's all event-wiring + tab coordination. Same shape as today's `admin.js` but extended.

## What stays the same

The current `vault-bus.js`, `api-client.js`, `poll.js`, `catalog.js`, the existing `<sp-cli-top-bar>`, `<sp-cli-vault-picker>`, `<sp-cli-region-picker>`, `<sp-cli-vault-activity>` (with rename) are preserved. The brief is structural, not a rewrite.

The `<sp-cli-launch-modal>` becomes `<sp-cli-launch-panel>` — same fields and submission logic, different framing (no backdrop, no fixed positioning, lives in a sg-layout tab).

The `<sp-cli-vnc-viewer>` becomes `<sg-remote-browser>` (in `_shared/`) — same 5-state machine, generic API.

The `<sp-cli-stack-detail>` is **deleted** and replaced by per-plugin detail components composing `_shared/` widgets.

The `<sp-cli-stacks-pane>` is preserved — only the click-row-opens-detail behaviour changes (now opens a tab instead of replacing the right-pane content).

## What good looks like

- `grep -r "from .* sp-cli-stack-detail" components/sp-cli/` returns zero hits — replaced everywhere.
- `grep -r "position: fixed" components/sp-cli/` returns zero hits — no modal patterns.
- For each compute type, the `plugins/{type}/` folder exists with both card.js and detail.js.
- The Compute view's launcher is **driven by the catalog response, not a hard-coded list**. Adding a new type to the backend's catalog → new card appears with no frontend code change beyond the per-plugin folder.
- Tab ID tracking (`_detailTabIds`, `_launchTabIds`) prevents duplicate tabs for the same stack/launch.
- Layout state persists across reloads (LAYOUT_CHANGED event → localStorage).
- Switching nav doesn't lose detail or launch tabs (they stay in the main stack).
