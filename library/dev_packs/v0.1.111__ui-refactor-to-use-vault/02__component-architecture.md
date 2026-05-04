# 02 — Component Architecture

**Status:** PROPOSED
**Read after:** `README.md`, `01__visual-design.md`
**Audience:** Sonnet implementing the JS/HTML side
**Verified:** All Tools URLs in this doc returned 200 from `https://dev.tools.sgraph.ai/` at draft time.

---

## What this doc gives you

Where every component lives. Which Tools components to import (with full version-pinned URLs). Which Playwright-specific components to build. The `SgComponent` pattern with a worked example. The promotion strategy for moving generic components from this repo to Tools.

## The dependency model

```
                  ┌─────────────────────────────┐
                  │  Tools (canonical)          │
                  │  https://dev.tools.sgraph.ai│
                  │                             │
                  │  /components/base           │
                  │  /components/tokens         │
                  │  /components/vault          │
                  │  /components/vault-embed    │
                  │  /components/content        │
                  │  /core/vault-client         │
                  │  /core/vault-init           │
                  │  /core/send-crypto          │
                  └─────────────┬───────────────┘
                                │ imported by URL
                                ▼
                  ┌─────────────────────────────┐
                  │  Playwright UI              │
                  │  /admin/  /user/            │
                  │                             │
                  │  components/sp-cli/...      │  ← stack-specific
                  │  shared/...                 │  ← page-specific helpers
                  └─────────────────────────────┘
```

**Direction is one-way.** Playwright UI consumes from Tools. Generic components born in Playwright graduate to Tools when they prove out (see "Promotion to Tools" below). Nothing flows back from Playwright into Tools without an explicit promotion step.

## Tools imports — the canonical URL list

Every URL below was verified accessible from `https://dev.tools.sgraph.ai/` at draft time. **Pin every version. No `latest`. No aliases.**

### Foundational (every page imports these)

```javascript
// Stylesheet (loaded as <link> in <head>)
https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css

// Component base class (imported by every component)
https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js
```

### Layout (every page imports this)

```javascript
// Fractal pane layout: rows, columns, tabs, resizable splitters, drag-to-dock.
// API: <sg-layout> element + .setLayout(json), .addTabToStack(stackId, config),
//      .getLayout() returns serialised state for persistence.
https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js
```

This is what the admin and user pages are built around — see doc 01 for the layout JSON used on each page.

### Vault layer (every page imports these)

```javascript
// Vault key derivation, openVault, readFile, batchRead, fetchSubTree
https://dev.tools.sgraph.ai/core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js

// Vault key state observer (sibling pattern for sg-vault-fetch)
https://dev.tools.sgraph.ai/components/vault-embed/sg-vault-key/v0/v0.1/v0.1.0/sg-vault-key.js

// Single-blob fetch + decrypt
https://dev.tools.sgraph.ai/components/vault-embed/sg-vault-fetch/v0/v0.1/v0.1.0/sg-vault-fetch.js
```

### Vault UI (used in the vault picker dropdown and Settings)

```javascript
// Vault key entry + connect form (used inside the vault picker dropdown)
https://dev.tools.sgraph.ai/components/vault/sg-vault-connect/v0/v0.1/v0.1.3/sg-vault-connect.js

// Vault tree browser (used in admin Settings tab — debugging / direct file access)
https://dev.tools.sgraph.ai/components/vault/sg-vault-tree/v0/v0.1/v0.1.3/sg-vault-tree.js

// New-vault creation flow
https://dev.tools.sgraph.ai/core/vault-init/v1/v1.0/v1.0.0/sg-vault-init.js
https://dev.tools.sgraph.ai/core/send-crypto/v1/v1.0/v1.0.0/sg-send-crypto.js
```

### Content rendering (only on the admin Settings tab for now)

```javascript
// JSON viewer for inspecting vault files raw
https://dev.tools.sgraph.ai/components/content/sg-content-json/v0/v0.1/v0.1.0/sg-content-json.js
```

### Verifying versions before use

The version pins above are correct as of brief drafting time. **Before you start a PR, run this check** to catch any breaking version moves:

```bash
for url in \
  "components/tokens/v1/v1.0/v1.0.0/sg-tokens.css" \
  "components/base/v1/v1.0/v1.0.0/sg-component.js" \
  "core/sg-layout/v0.1.0/sg-layout.js" \
  "core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js" \
  "core/vault-write/v1/v1.1/v1.1.1/sg-vault-write.js" \
  "components/vault-embed/sg-vault-key/v0/v0.1/v0.1.0/sg-vault-key.js" \
  "components/vault-embed/sg-vault-fetch/v0/v0.1/v0.1.0/sg-vault-fetch.js" \
  "components/vault/sg-vault-connect/v0/v0.1/v0.1.3/sg-vault-connect.js" \
; do
  curl -s -o /dev/null -w "%{http_code} %s\n" "https://dev.tools.sgraph.ai/${url}"
done
```

All should return 200. If anything 404s, find the latest version under that family by browsing the Tools repo at `the-cyber-boardroom/SGraph-AI__Tools`, update the URL in the brief and your imports, and proceed.

---

## File tree — what lives where

```
sgraph_ai_service_playwright__api_site/
├── index.html                       Root landing page → links to /admin/ /user/
├── style.css                        Existing — kept (used by index.html)
│
├── admin/
│   ├── index.html                   Admin dashboard shell
│   ├── admin.js                     Admin page controller
│   └── admin.css                    Admin-only layout
│
├── user/
│   ├── index.html                   User provisioning shell
│   ├── user.js                      User page controller
│   └── user.css                     User-only layout
│
├── shared/
│   ├── api-client.js                ← (PROMOTE to Tools — see below)
│   ├── poll.js                      ← (PROMOTE to Tools)
│   ├── catalog.js                   Stays — SP-CLI specific
│   ├── vault-bus.js                 NEW — vault event bus glue (see doc 03)
│   └── components/
│       ├── sg-api-client.js         ← (PROMOTE to Tools)
│       ├── sg-toast-host.js         ← (PROMOTE to Tools)
│       └── sg-auth-panel.js         ← (PROMOTE to Tools, generalised as sg-api-key-panel)
│
└── components/sp-cli/                NEW — Playwright-specific component family
    ├── sp-cli-top-bar/v0/v0.1/v0.1.0/
    │   ├── sp-cli-top-bar.js
    │   ├── sp-cli-top-bar.html
    │   └── sp-cli-top-bar.css
    ├── sp-cli-vault-picker/v0/v0.1/v0.1.0/
    │   ├── sp-cli-vault-picker.js
    │   ├── sp-cli-vault-picker.html
    │   └── sp-cli-vault-picker.css
    ├── sp-cli-vault-activity/v0/v0.1/v0.1.0/         (NEW — live vault read/write trace pane)
    │   ├── sp-cli-vault-activity.js
    │   ├── sp-cli-vault-activity.html
    │   └── sp-cli-vault-activity.css
    ├── sp-cli-region-picker/v0/v0.1/v0.1.0/
    │   ├── sp-cli-region-picker.js
    │   ├── sp-cli-region-picker.html
    │   └── sp-cli-region-picker.css
    ├── sp-cli-stacks-pane/v0/v0.1/v0.1.0/             (NEW — admin Stacks tab wrapper for sg-layout)
    │   ├── sp-cli-stacks-pane.js
    │   ├── sp-cli-stacks-pane.html
    │   └── sp-cli-stacks-pane.css
    ├── sp-cli-catalog-pane/v0/v0.1/v0.1.0/            (NEW — admin Catalog tab placeholder)
    │   ├── sp-cli-catalog-pane.js
    │   ├── sp-cli-catalog-pane.html
    │   └── sp-cli-catalog-pane.css
    ├── sp-cli-activity-pane/v0/v0.1/v0.1.0/           (NEW — admin Activity Log tab wrapper; renders sp-cli-activity-log)
    │   ├── sp-cli-activity-pane.js
    │   ├── sp-cli-activity-pane.html
    │   └── sp-cli-activity-pane.css
    ├── sp-cli-user-pane/v0/v0.1/v0.1.0/               (NEW — user-page main tab wrapper)
    │   ├── sp-cli-user-pane.js
    │   ├── sp-cli-user-pane.html
    │   └── sp-cli-user-pane.css
    ├── sp-cli-stack-table/v0/v0.1/v0.1.0/
    │   ├── sp-cli-stack-table.js
    │   ├── sp-cli-stack-table.html
    │   └── sp-cli-stack-table.css
    ├── sp-cli-stack-card/v0/v0.1/v0.1.0/             (replaces user-page active row)
    │   ├── sp-cli-stack-card.js
    │   ├── sp-cli-stack-card.html
    │   └── sp-cli-stack-card.css
    ├── sp-cli-stack-detail/v0/v0.1/v0.1.0/           (the slide-in detail panel)
    │   ├── sp-cli-stack-detail.js
    │   ├── sp-cli-stack-detail.html
    │   └── sp-cli-stack-detail.css
    ├── sp-cli-type-card/v0/v0.1/v0.1.0/              (the launch-card grid item)
    │   ├── sp-cli-type-card.js
    │   ├── sp-cli-type-card.html
    │   └── sp-cli-type-card.css
    ├── sp-cli-launch-wizard/v0/v0.1/v0.1.0/          (the multi-state launch modal)
    │   ├── sp-cli-launch-wizard.js
    │   ├── sp-cli-launch-wizard.html
    │   └── sp-cli-launch-wizard.css
    ├── sp-cli-activity-log/v0/v0.1/v0.1.0/           (admin-only — the application activity log, reads sp-cli/activity-log.json)
    │   ├── sp-cli-activity-log.js
    │   ├── sp-cli-activity-log.html
    │   └── sp-cli-activity-log.css
    └── sp-cli-confirm-modal/v0/v0.1/v0.1.0/          (Stop confirmation, etc.)
        ├── sp-cli-confirm-modal.js
        ├── sp-cli-confirm-modal.html
        └── sp-cli-confirm-modal.css
```

**About the "pane wrapper" components** (`sp-cli-stacks-pane`, `sp-cli-catalog-pane`, `sp-cli-activity-pane`, `sp-cli-user-pane`): `<sg-layout>` instantiates components by tag name when their tab becomes active. So we need a top-level wrapper component per tab that composes the actual content (stack table + type strip + filters in `sp-cli-stacks-pane`, etc.). The wrappers are thin — they're just composition shells; the real logic lives in the component pieces they assemble.

**Two important distinctions** between activity components:

| Component | Purpose | Reads from |
|---|---|---|
| `<sp-cli-activity-log>` | **Application** activity log — launches, stops, ready transitions. Operators-facing. | `sp-cli/activity-log.json` in vault. |
| `<sp-cli-vault-activity>` | **Vault** trace — reads, writes, decryptions. Developer/operator-facing introspection. | `sp-cli:vault-bus:*` events on the document. |

They look similar (chronological lists with icons) but are conceptually different. The application log is the audit trail of what stacks were provisioned. The vault trace is the audit trail of what bytes hit the vault. Both are useful; both are visible.

**Convention notes:**

- All Playwright-specific components live under `components/sp-cli/` with the **same versioned-folder shape Tools uses**: `name/v{N}/v{N.M}/v{N.M.P}/`. Each component is three files (`.js` + `.html` + `.css`).
- The `sp-cli-` prefix avoids collisions with Tools' `sg-` prefix and makes provenance obvious.
- Generic components in `shared/` are flat — those are deprecated-once-promoted and don't get the versioned folder shape.

## The `SgComponent` pattern — worked example

Every component in `components/sp-cli/` extends `SgComponent`. Three-file shape: `.js` (logic), `.html` (template), `.css` (styles). The base class handles Shadow DOM, fetches the sibling `.html` and `.css`, calls lifecycle hooks.

### `sp-cli-top-bar.js`

```javascript
/**
 * sp-cli-top-bar — Provisioning Console top bar.
 *
 * Shows brand mark, page title, region picker, vault picker.
 * Vault picker is composed from sp-cli-vault-picker (sibling component).
 *
 * Attributes:
 *   page-title  — "Provisioning Console", "Admin Dashboard", etc.
 *   region      — defaults to eu-west-2; updates from vault preferences
 *
 * Events:
 *   sp-cli:region-changed   — { region }
 *
 * @module sp-cli-top-bar
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliTopBar extends SgComponent {

    static jsUrl = import.meta.url

    get resourceName() { return 'sp-cli-top-bar' }

    get sharedCssPaths() {
        return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css']
    }

    static get observedAttributes() { return ['page-title', 'region'] }

    onReady() {
        this._titleEl  = this.$('.page-title')
        this._regionEl = this.$('.region-picker')
        this._renderTitle()
        this._renderRegion()
    }

    attributeChangedCallback(name, _old, newVal) {
        if (!this.isReady) return
        if (name === 'page-title') this._renderTitle()
        if (name === 'region')     this._renderRegion()
    }

    _renderTitle() {
        if (this._titleEl) this._titleEl.textContent = this.getAttribute('page-title') || ''
    }

    _renderRegion() {
        if (this._regionEl) this._regionEl.textContent = this.getAttribute('region') || 'eu-west-2'
    }
}

customElements.define('sp-cli-top-bar', SpCliTopBar)
```

### `sp-cli-top-bar.html`

```html
<div class="top-bar">
  <div class="brand">
    <span class="brand-mark">SGraph</span>
  </div>
  <h1 class="page-title"></h1>
  <div class="region-picker">eu-west-2</div>
  <slot name="vault-picker"></slot>
</div>
```

The `<slot name="vault-picker">` lets the page controller compose a `<sp-cli-vault-picker>` into the slot — keeps the top bar agnostic to the vault-picker implementation.

### `sp-cli-top-bar.css`

```css
:host {
    display: block;
    border-bottom: 1px solid var(--sg-border);
    background: var(--sg-bg-secondary);
}
.top-bar {
    display: flex;
    align-items: center;
    gap: var(--sg-sp-4);
    padding: var(--sg-sp-2) var(--sg-sp-4);
    height: 56px;
}
.brand-mark {
    font-family: var(--sg-font-display);
    font-weight: var(--sg-fw-bold);
    color: var(--sg-text-heading);
    letter-spacing: 0.04em;
}
.page-title {
    flex: 1;
    margin: 0;
    font-size: 1rem;
    font-weight: var(--sg-fw-medium);
    color: var(--sg-text);
}
.region-picker {
    color: var(--sg-text-muted);
    font-size: var(--sg-fs-small);
    padding: var(--sg-sp-1) var(--sg-sp-2);
}
```

This is the canonical pattern. **Every component in this brief follows this shape** — three files, `static jsUrl = import.meta.url`, `get resourceName()`, `get sharedCssPaths()` returning the tokens URL, `onReady()` for setup, `$()` / `$$()` for shadow-root queries, `emit()` for events.

## Per-component contracts

Below: the API surface (attributes, properties, events) for every Playwright-specific component. Layout details are in doc 01; this is the wiring contract.

### `<sp-cli-top-bar>`

**Attributes:** `page-title`, `region`
**Slots:** `vault-picker`
**Events:** `sp-cli:region-changed`, `sp-cli:brand-clicked`
**Inside:** brand mark, title, region picker, vault picker slot

### `<sp-cli-vault-picker>`

**Attributes:** none
**Properties:**
- `vaultState` (read-only) — current vault info: `{ vaultId, apiBaseUrl, stats } | null`

**Events:** `sp-cli:vault-picker-opened`, `sp-cli:connect-requested`, `sp-cli:create-requested`, `sp-cli:disconnect-requested`, `sp-cli:vault-switched`
**Listens to (on document):** `vault:connected`, `vault:disconnected` (from `<sg-vault-connect>`)
**Inside:** the dropdown UI (current vault summary, recent vaults list, action buttons). Embeds `<sg-vault-connect>` from Tools when "Connect another vault" is clicked.

### `<sp-cli-region-picker>`

**Attributes:** `value`
**Events:** `sp-cli:region-changed`
**Inside:** dropdown of available regions. For MVP this is `eu-west-2` only; the structure exists for future expansion.

### `<sp-cli-stack-table>` (admin only)

**Properties:**
- `stacks` — array of `Schema__Stack__Summary`-shaped objects
- `loading` — bool, shows skeleton

**Events:** `sp-cli:row-clicked` (with detail `{ type, name }`), `sp-cli:stop-requested` (from row overflow menu)
**Inside:** sortable table with type icon, name, state, IP, uptime, action menu

### `<sp-cli-stack-card>` (user-page active strip)

**Properties:**
- `stack` — single `Schema__Stack__Summary` object

**Events:** `sp-cli:details-requested`, `sp-cli:stop-requested`
**Inside:** horizontal compact card with type icon, name, state dot, IP, uptime, action buttons.

### `<sp-cli-stack-detail>`

**Properties:**
- `stack` — full `Schema__{Linux,Docker,Elastic}__Info` object (the page controller fetches this when the panel opens)
- `activity` — array of recent activity entries for this stack

**Attributes:** `open` (presence-attr; controls slide-in)

**Events:** `sp-cli:detail-closed`, `sp-cli:stop-requested`, `sp-cli:restart-requested`
**Inside:** the full detail panel from doc 01 — header, status, SSM, network, resource details (collapsible), recent activity (collapsible), actions row.

### `<sp-cli-type-card>`

**Properties:**
- `entry` — a `Schema__Stack__Type__Catalog__Entry`

**Events:** `sp-cli:launch-requested` (with detail `{ type }`)
**Inside:** the launch card from doc 01 — emoji, name, description, boot time, [Launch] button (or disabled state for `available=false`).

### `<sp-cli-launch-wizard>`

**Properties:**
- `entry` — a `Schema__Stack__Type__Catalog__Entry` (the type being launched)

**Attributes:** `open`

**Internal states:**
1. `form` — initial dropdown picker
2. `progress` — checkpoint state machine with progress bar
3. `ready` — success view with SSM command
4. `error` — failure view with retry/cancel

**Events:** `sp-cli:launch-submitted` (form → controller fires the create call), `sp-cli:launch-completed`, `sp-cli:launch-cancelled`, `sp-cli:wizard-closed`
**Polling:** owns its own poll loop (using the promoted `poll.js`) once it transitions to `progress`. Does NOT cancel the launch on close; only stops its own polling.

The checkpoint logic lives entirely in this component:

```javascript
// State machine — order matters, evaluated top to bottom
const CHECKPOINTS = [
    { id: 'created',    label: 'Stack created',     reachedWhen: ({ launched })   => launched },
    { id: 'pending',    label: 'Instance pending',  reachedWhen: ({ health })     => health?.state === 'PENDING'      || health?.state === 'INITIALIZING' },
    { id: 'running',    label: 'Instance running',  reachedWhen: ({ health })     => health?.state === 'RUNNING' },
    { id: 'ssm',        label: 'Waiting for SSM',   reachedWhen: ({ health })     => health?.state === 'RUNNING' && health?.ssm_reachable === true,
                                                    skipWhen   : ({ entry })      => entry.type_id === 'elastic' /* elastic uses its own readiness signal */ },
    { id: 'ready',      label: 'Ready',             reachedWhen: ({ health })     => health?.healthy === true },
]
```

The wizard re-renders on every health-poll tick, walking the checkpoint list and computing which are reached/in-progress/pending.

### `<sp-cli-activity-log>` (admin only)

**Properties:**
- `entries` — array of activity log entries (read from vault path `sp-cli/activity-log.json`)
- `loading` — bool

**Events:** `sp-cli:activity-clear-requested`, `sp-cli:activity-row-clicked` (jump to detail)
**Inside:** reverse-chronological table of recent actions.

### `<sp-cli-confirm-modal>`

**Attributes:** `open`
**Properties:**
- `title` — "Stop linux-quiet-fermi?"
- `body` — "This will terminate the EC2 instance."
- `confirm-label` — "Stop stack"
- `confirm-variant` — "danger" | "primary"

**Events:** `sp-cli:confirm`, `sp-cli:cancel`

A reusable confirmation modal. Used for Stop, future Delete, etc.

---

## Page controller responsibilities

The two pages are thin. The controller's job is:

1. Wire components together via events.
2. Fetch data on load (catalog, active stacks).
3. Listen for vault connection state and react.
4. Coordinate the active-stacks polling cycle (admin) and detail-panel refresh.

### `admin/admin.js` — sketch

```javascript
import { apiClient }       from '../shared/api-client.js'
import { startVaultBus }   from '../shared/vault-bus.js'
import { loadCatalog }     from '../shared/catalog.js'

import '../components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/sp-cli-top-bar.js'
import '../components/sp-cli/sp-cli-vault-picker/v0/v0.1/v0.1.0/sp-cli-vault-picker.js'
import '../components/sp-cli/sp-cli-stack-table/v0/v0.1/v0.1.0/sp-cli-stack-table.js'
import '../components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/sp-cli-stack-detail.js'
import '../components/sp-cli/sp-cli-type-card/v0/v0.1/v0.1.0/sp-cli-type-card.js'
import '../components/sp-cli/sp-cli-launch-wizard/v0/v0.1/v0.1.0/sp-cli-launch-wizard.js'
import '../components/sp-cli/sp-cli-activity-log/v0/v0.1/v0.1.0/sp-cli-activity-log.js'
import '../components/sp-cli/sp-cli-confirm-modal/v0/v0.1/v0.1.0/sp-cli-confirm-modal.js'

const STACK_REFRESH_MS = 15_000

document.addEventListener('DOMContentLoaded', async () => {

    // 1. Vault state — gate all data loads
    const vaultBus = startVaultBus()  // listens for vault:connected / vault:disconnected, manages localStorage

    // 2. Wire the top bar
    const topBar = document.querySelector('sp-cli-top-bar')

    // 3. Catalog: fetch once when vault connects (reads vault preferences first, then FastAPI)
    document.addEventListener('vault:connected', async () => {
        const catalog = await loadCatalog()  // merges /catalog/types from FastAPI with vault overrides
        const stackTable    = document.querySelector('sp-cli-stack-table')
        const typeContainer = document.querySelector('#type-cards')

        // Populate type cards
        typeContainer.innerHTML = ''
        for (const entry of catalog.entries) {
            const card = document.createElement('sp-cli-type-card')
            card.entry = entry
            typeContainer.appendChild(card)
        }

        // First fetch
        refreshStacks(stackTable)
        setInterval(() => refreshStacks(stackTable), STACK_REFRESH_MS)
    })

    document.addEventListener('vault:disconnected', () => {
        // Clear all data displays; re-show the connect-vault prompt
    })

    // 4. Wire interactions (events bubble up to document)
    document.addEventListener('sp-cli:launch-requested', (e) => {
        const wizard = document.querySelector('sp-cli-launch-wizard')
        wizard.entry = e.detail.entry
        wizard.setAttribute('open', '')
    })

    document.addEventListener('sp-cli:row-clicked', (e) => {
        openDetailPanel(e.detail.type, e.detail.name)
    })

    document.addEventListener('sp-cli:stop-requested', (e) => {
        showStopConfirm(e.detail.type, e.detail.name)
    })

    document.addEventListener('sp-cli:launch-completed', () => {
        refreshStacks(document.querySelector('sp-cli-stack-table'))
    })
})


async function refreshStacks(table) {
    table.loading = true
    try {
        const result = await apiClient.get('/catalog/stacks')
        table.stacks = result.stacks || []
        // Cache to vault for offline / fast first-paint next time
        await writeVaultCache('sp-cli/active-stacks-cache.json', result)
    } catch (err) {
        // Try fallback from vault cache; toast if even that fails
        const cached = await readVaultCache('sp-cli/active-stacks-cache.json')
        if (cached) table.stacks = cached.stacks
        toast(`Could not refresh — using cached data`, 'warning')
    } finally {
        table.loading = false
    }
}

// openDetailPanel, showStopConfirm, toast — straightforward wiring; see admin.js full impl
```

The user controller is structurally identical, just with different DOM selectors and no activity log. Both controllers are ~150 lines each.

---

## Promotion to Tools — what gets graduated

These three modules are generic enough to belong in Tools, not Playwright. **Promotion is part of this brief's scope.**

| Source | Tools target | Renamed? |
|---|---|---|
| `shared/api-client.js` + `<sg-api-client>` | `Tools/components/tool-api/sg-api-client/v0/v0.1/v0.1.0/sg-api-client.js` | No |
| `shared/poll.js` | `Tools/core/poll/v0/v0.1/v0.1.0/sg-poll.js` | Module path; class is `startPoll` |
| `<sg-toast-host>` | `Tools/components/feedback/sg-toast-host/v0/v0.1/v0.1.0/sg-toast-host.js` | No |
| `<sg-auth-panel>` | `Tools/components/auth/sg-api-key-panel/v0/v0.1/v0.1.0/sg-api-key-panel.js` | Renamed — generalised, configurable storage prefix |

### Promotion mechanics (what Sonnet does)

1. **Make a feature branch in the Tools repo** (`SGraph-AI__Tools`): `claude/promote-from-sp-cli-{date}`.
2. **Copy each file** into the target path under `sgraph_ai_tools__static/components/{family}/{name}/v0/v0.1/v0.1.0/`. Add the JSDoc module header per Tools convention. Make sure each component extends `SgComponent` (rewrite if currently extending `HTMLElement` directly — this is part of promotion).
3. **Do not modify the API surface during promotion** (events, properties stay the same). API generalisation (e.g. `sg-api-key-panel`'s configurable storage prefix) happens in a follow-up PR after the move.
4. **Open a PR** in Tools, get it merged, deploy to `dev.tools.sgraph.ai`.
5. **In Playwright,** replace local imports with `https://dev.tools.sgraph.ai/...` URLs. Delete the local copies. Verify everything still works.

If the Tools PR cannot land in time for the Playwright brief to complete, fall back: keep the local copies in `shared/`, mark with a `// TODO: promote to Tools` comment, ship the brief, do the promotion as a separate follow-up.

### What does NOT get promoted

| Component | Why it stays in Playwright |
|---|---|
| `sp-cli-top-bar` | Product-specific layout |
| `sp-cli-vault-picker` | Product-specific composition (uses `<sg-vault-connect>` from Tools, but the dropdown UI is product-specific) |
| `sp-cli-region-picker` | Region list is AWS-specific to the Playwright product (could move later if a second SGraph product needs it) |
| `sp-cli-stack-*` | Stack-provisioning specific |
| `sp-cli-type-card` | Specific to the catalog shape |
| `sp-cli-launch-wizard` | Specific to the create/health/ready protocol |
| `sp-cli-activity-log` | Reads a vault-path that's Playwright-specific |
| `sp-cli-confirm-modal` | Could promote later if a second product needs it; defer |

The rule of thumb: **if I can describe the component's purpose without saying "stack" or "AWS" or "EC2", it's probably promotable.**

---

## What good looks like

When this brief is done, a developer should be able to:

1. Open any `sp-cli-*` component file and find a 3-file pair (`.js` + `.html` + `.css`).
2. Run `grep -c "extends SgComponent" components/sp-cli/**/*.js` and see one match per component.
3. Run `grep "fetch(" sgraph_ai_service_playwright__api_site/` and see hits only in the api-client module and Tools-imported URLs.
4. Add a sixth stack type by editing the FastAPI catalog only — zero UI changes.
5. Read `02__component-architecture.md` and find the canonical Tools URL for any imported component.
6. Confirm the version pins in this doc match the actual import statements with one `grep`.

If any of those is hard, the architecture is not done.
