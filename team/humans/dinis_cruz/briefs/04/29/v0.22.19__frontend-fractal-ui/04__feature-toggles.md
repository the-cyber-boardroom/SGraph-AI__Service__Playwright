# 04 — Feature Toggles & Settings Persistence

**Status:** PROPOSED
**Read after:** `02__component-architecture.md`, `03__event-vocabulary.md`

---

## What this doc gives you

How the Settings panel works, how toggles propagate, the `settings-bus.js` module, the vault path, and the precise behaviour when a plugin is toggled off while its detail tab is open.

## The principle

Settings are **live**. Toggling a plugin off in the Settings view immediately:

1. Removes its launcher card from the Compute view.
2. Closes any open detail tabs for stacks of that type (with a toast: "Closed Linux detail (plugin disabled)").
3. Persists the new state to vault.
4. Fires `sp-cli:plugin.toggled { name: 'linux', enabled: false }`.

No page reload. No "save changes" button. Toggle = take effect.

This works because the Compute view's launcher pane re-renders on every `sp-cli:plugin.toggled`; the launcher reads from `settings-bus.js` (which is the in-memory cache + vault sync layer), not from a snapshot.

## The data shape

Stored in vault at `sp-cli/preferences.json`:

```json
{
    "schema_version": 2,
    "plugins": {
        "linux":      { "enabled": true  },
        "docker":     { "enabled": true  },
        "elastic":    { "enabled": true  },
        "vnc":        { "enabled": true  },
        "prometheus": { "enabled": false },
        "opensearch": { "enabled": false },
        "neko":       { "enabled": false }
    },
    "ui_panels": {
        "events_log":      { "visible": true  },
        "vault_status":    { "visible": true  },
        "active_sessions": { "visible": true  },
        "cost_tracker":    { "visible": true  }
    },
    "defaults": {
        "region":         "eu-west-2",
        "max_hours":      4,
        "instance_type":  "t3.medium"
    }
}
```

`schema_version: 2` because the previous brief defined version 1 with a different shape. Migration: if a v1 preferences file exists, settings-bus reads what fields it can, fills in defaults for the rest, writes v2 back. Never deletes user data.

## `settings-bus.js`

A new shared module (alongside `vault-bus.js`). Module-level singleton that owns the in-memory settings state.

```javascript
// shared/settings-bus.js

import { vaultReadJson, vaultWriteJson, isWritable } from './vault-bus.js'

const VAULT_PATH = 'sp-cli/preferences.json'

const DEFAULTS = {
    schema_version: 2,
    plugins: {
        linux:      { enabled: true  },
        docker:     { enabled: true  },
        elastic:    { enabled: true  },
        vnc:        { enabled: true  },
        prometheus: { enabled: false },
        opensearch: { enabled: false },
        neko:       { enabled: false },
    },
    ui_panels: {
        events_log:      { visible: true },
        vault_status:    { visible: true },
        active_sessions: { visible: true },
        cost_tracker:    { visible: true },
    },
    defaults: {
        region:         'eu-west-2',
        max_hours:      4,
        instance_type:  't3.medium',
    },
}

let _state = _deepClone(DEFAULTS)
let _loaded = false

export function startSettingsBus() {
    document.addEventListener('vault:connected', _onVaultConnected)
    document.addEventListener('vault:disconnected', _onVaultDisconnected)
}

async function _onVaultConnected() {
    try {
        const data = await vaultReadJson(VAULT_PATH)
        _state = data ? _migrate(data) : _deepClone(DEFAULTS)
        _loaded = true
        document.dispatchEvent(new CustomEvent('sp-cli:settings.loaded', {
            detail:  { settings: _deepClone(_state) },
            bubbles: true, composed: true,
        }))
    } catch (err) {
        console.warn('settings-bus: load failed, using defaults:', err.message)
        _state = _deepClone(DEFAULTS)
        _loaded = true
        document.dispatchEvent(new CustomEvent('sp-cli:settings.loaded', {
            detail:  { settings: _deepClone(_state) },
            bubbles: true, composed: true,
        }))
    }
}

function _onVaultDisconnected() {
    _state = _deepClone(DEFAULTS)
    _loaded = false
}

export function isLoaded() { return _loaded }

export function getPluginEnabled(name) {
    return _state.plugins[name]?.enabled ?? false
}

export function getAllPluginToggles() {
    return _deepClone(_state.plugins)
}

export function getUIPanelVisible(panel) {
    return _state.ui_panels[panel]?.visible ?? true
}

export function getDefault(key) {
    return _state.defaults[key]
}

export async function setPluginEnabled(name, enabled) {
    if (!_state.plugins[name]) _state.plugins[name] = {}
    _state.plugins[name].enabled = !!enabled
    document.dispatchEvent(new CustomEvent('sp-cli:plugin.toggled', {
        detail:  { name, enabled: !!enabled },
        bubbles: true, composed: true,
    }))
    await _persist(['plugins'])
}

export async function setUIPanelVisible(panel, visible) {
    if (!_state.ui_panels[panel]) _state.ui_panels[panel] = {}
    _state.ui_panels[panel].visible = !!visible
    document.dispatchEvent(new CustomEvent('sp-cli:ui-panel.toggled', {
        detail:  { panel, visible: !!visible },
        bubbles: true, composed: true,
    }))
    await _persist(['ui_panels'])
}

export async function setDefault(key, value) {
    _state.defaults[key] = value
    await _persist(['defaults'])
}

async function _persist(keys) {
    if (!isWritable()) {
        // Read-only vault — keep the change in memory but show a toast.
        document.dispatchEvent(new CustomEvent('sg-toast', {
            detail:  { message: 'Setting changed in this session only (vault is read-only).', tone: 'warning' },
            bubbles: true, composed: true,
        }))
        return
    }
    try {
        await vaultWriteJson(VAULT_PATH, _state, { message: `Update preferences (${keys.join(', ')})` })
        document.dispatchEvent(new CustomEvent('sp-cli:settings.saved', {
            detail:  { keys },
            bubbles: true, composed: true,
        }))
    } catch (err) {
        console.error('settings-bus: persist failed:', err)
        document.dispatchEvent(new CustomEvent('sg-toast', {
            detail:  { message: `Failed to save settings: ${err.message}`, tone: 'error' },
            bubbles: true, composed: true,
        }))
    }
}

function _migrate(data) {
    const v = data.schema_version || 1
    if (v === 2) return data
    if (v === 1) {
        // Old shape from the previous brief — copy what we can, default the rest.
        return {
            schema_version: 2,
            plugins:        data.plugins        || _deepClone(DEFAULTS.plugins),
            ui_panels:      data.ui_panels      || _deepClone(DEFAULTS.ui_panels),
            defaults: {
                region:         data.default_region            || DEFAULTS.defaults.region,
                max_hours:      data.default_max_hours          || DEFAULTS.defaults.max_hours,
                instance_type:  data.default_instance_types?.linux || DEFAULTS.defaults.instance_type,
            },
        }
    }
    // Future schema we don't recognise — leave it alone, use defaults in-memory.
    console.warn(`settings-bus: unknown schema_version ${v}, using defaults`)
    return _deepClone(DEFAULTS)
}

function _deepClone(obj) { return JSON.parse(JSON.stringify(obj)) }
```

## How the Settings panel uses it

`<sp-cli-settings-view>` is a normal SgComponent. On `onReady`:

1. Listen for `sp-cli:settings.loaded` → re-render with current toggle states.
2. Read current state via `getAllPluginToggles()` for the initial render.
3. On each checkbox change, call `setPluginEnabled(name, checked)`.

```javascript
class SpCliSettingsView extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName() { return 'sp-cli-settings-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._render()
        document.addEventListener('sp-cli:settings.loaded', () => this._render())
    }

    _render() {
        // ...read settings via the imported settings-bus helpers
        // ...render checkboxes
        // ...attach onchange handlers that call setPluginEnabled etc.
    }
}
```

The settings-bus is the single source of truth. Multiple components reading independently always see consistent values because the bus mutates one in-memory state object.

## How the Launcher pane reacts

`<sp-cli-launcher-pane>` listens for two events:

1. `sp-cli:settings.loaded` — initial render (filters catalog by enabled plugins).
2. `sp-cli:plugin.toggled` — re-render (a plugin was just toggled).

```javascript
onReady() {
    document.addEventListener('sp-cli:settings.loaded', () => this._render())
    document.addEventListener('sp-cli:plugin.toggled',  () => this._render())
}

_render() {
    if (!this._catalog) return                              // catalog not fetched yet
    const toggles = getAllPluginToggles()                   // from settings-bus
    const enabledTypes = this._catalog.entries.filter(e => toggles[e.type_id]?.enabled)
    // render one card per enabled type
    // ...
}
```

## Closing detail tabs when a plugin is disabled

The page controller listens for `sp-cli:plugin.toggled`:

```javascript
document.addEventListener('sp-cli:plugin.toggled', (e) => {
    const { name, enabled } = e.detail
    if (enabled) return                                       // enabling: nothing to close
    // Disabled: find detail tabs whose stack.type_id matches and close them
    for (const [stackName, tabId] of Object.entries(_detailTabIds)) {
        const stackTypeForTab = _tabIdToTypeId(tabId)        // look up via panel element or stored map
        if (stackTypeForTab === name) {
            _layoutEl.removePanel(tabId)
            delete _detailTabIds[stackName]
            document.dispatchEvent(new CustomEvent('sg-toast', {
                detail:  { message: `Closed ${name} detail (plugin disabled)` },
                bubbles: true, composed: true,
            }))
        }
    }
    // Same for any open launch tabs of this type
    if (_launchTabIds[name]) {
        _layoutEl.removePanel(_launchTabIds[name])
        delete _launchTabIds[name]
    }
})
```

## Read-only vault behaviour

If the operator is connected with vault key but no access token (read-only mode per the previous brief's design):

1. Settings can still be **changed** (in-memory).
2. Changes don't persist — next page reload, defaults again.
3. A toast warns once per session: "Setting changed in this session only (vault is read-only)."
4. The Settings view shows a banner at the top: "⚠ Read-only mode — settings won't persist. [Add access token →]" — link triggers the same flow as the top-bar's read-only banner.

## Default values throughout the app

The launch panel uses `getDefault('region')`, `getDefault('max_hours')`, `getDefault('instance_type')` to pre-fill its form. When the operator changes the form's values for a *specific* launch, that doesn't change the defaults — only the Settings view's "Defaults" section changes them. This keeps "what you launched today" separate from "what you usually launch."

## Testing

Manual smoke test:

1. Connect to a vault with a fresh `sp-cli/preferences.json` file (or none — settings-bus reads → null → uses defaults).
2. Settings view shows defaults.
3. Toggle Neko on → launcher card appears within ~50ms.
4. Reload page → vault reconnect → settings reload → Neko card still visible.
5. Toggle Neko off → launcher card disappears.
6. Open a Linux stack's detail tab. Disable Linux in Settings. Tab closes with toast.
7. Disconnect vault. Reconnect with vault key only (no access token). Toggle a plugin. Toast appears: "...won't persist." Reload — toggle is back to whatever was in vault.

## What good looks like

- `grep -r "localStorage" components/sp-cli/sp-cli-settings-view/` returns zero hits — settings live in vault, not localStorage.
- The settings-bus module has no DOM access — only event dispatch + vault read/write. Pure logic.
- `sp-cli:plugin.toggled` fires every time the operator toggles, even if the toggle is a no-op (false → false). The receiver de-dupes if needed.
- Settings load completes before the launcher first renders. (Achieved by the launcher waiting for `sp-cli:settings.loaded`.)
- Read-only mode is non-blocking — operator can still use the app, just with the warning toast.
