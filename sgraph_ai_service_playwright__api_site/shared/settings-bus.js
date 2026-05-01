// ── settings-bus.js — Feature-toggle state + vault persistence ─────────────── //
// Module-level singleton. Owns in-memory settings state and syncs to vault.    //
// Call startSettingsBus() once from the page controller.                        //

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
        neko:       { enabled: true  },
        firefox:    { enabled: true  },
        podman:     { enabled: true  },
    },
    ui_panels: {
        events_log:      { visible: true },
        vault_status:    { visible: true },
        active_sessions: { visible: true },
        cost_tracker:    { visible: true },
    },
    defaults: {
        region:        'eu-west-2',
        max_hours:     4,
        instance_type: 't3.medium',
    },
}

let _state  = _deepClone(DEFAULTS)
let _loaded = false

export function startSettingsBus() {
    document.addEventListener('vault:connected',    _onVaultConnected)
    document.addEventListener('vault:disconnected', _onVaultDisconnected)
}

async function _onVaultConnected() {
    try {
        const data = await vaultReadJson(VAULT_PATH)
        _state  = data ? _migrate(data) : _deepClone(DEFAULTS)
        _loaded = true
    } catch (err) {
        console.warn('[settings-bus] load failed, using defaults:', err.message)
        _state  = _deepClone(DEFAULTS)
        _loaded = true
    }
    _dispatch('sp-cli:settings.loaded', { settings: _deepClone(_state) })
}

function _onVaultDisconnected() {
    _state  = _deepClone(DEFAULTS)
    _loaded = false
}

// ── Readers ───────────────────────────────────────────────────────────────── //

export function isLoaded()              { return _loaded }
export function getPluginEnabled(name)  { return _state.plugins[name]?.enabled ?? false }
export function getAllPluginToggles()   { return _deepClone(_state.plugins) }
export function getUIPanelVisible(p)   { return _state.ui_panels[p]?.visible ?? true }
export function getDefault(key)        { return _state.defaults[key] }
export function getAllDefaults()        { return _deepClone(_state.defaults) }

// ── Writers ───────────────────────────────────────────────────────────────── //

export async function setPluginEnabled(name, enabled) {
    if (!_state.plugins[name]) _state.plugins[name] = {}
    _state.plugins[name].enabled = !!enabled
    _dispatch('sp-cli:plugin.toggled', { name, enabled: !!enabled })
    await _persist(['plugins'])
}

export async function setUIPanelVisible(panel, visible) {
    if (!_state.ui_panels[panel]) _state.ui_panels[panel] = {}
    _state.ui_panels[panel].visible = !!visible
    _dispatch('sp-cli:ui-panel.toggled', { panel, visible: !!visible })
    await _persist(['ui_panels'])
}

export async function setDefault(key, value) {
    _state.defaults[key] = value
    await _persist(['defaults'])
}

// ── Internal ──────────────────────────────────────────────────────────────── //

async function _persist(keys) {
    if (!isWritable()) {
        _dispatch('sg-toast', { message: 'Setting changed in this session only (vault is read-only).', tone: 'warning' })
        return
    }
    try {
        await vaultWriteJson(VAULT_PATH, _state, { message: `Update preferences (${keys.join(', ')})` })
        _dispatch('sp-cli:settings.saved', { keys })
    } catch (err) {
        console.error('[settings-bus] persist failed:', err)
        _dispatch('sg-toast', { message: `Failed to save settings: ${err.message}`, tone: 'error' })
    }
}

function _migrate(data) {
    const v = data.schema_version || 1
    if (v === 2) return _mergeDefaults(data)
    if (v === 1) {
        return {
            schema_version: 2,
            plugins:        data.plugins   || _deepClone(DEFAULTS.plugins),
            ui_panels:      data.ui_panels || _deepClone(DEFAULTS.ui_panels),
            defaults: {
                region:        data.default_region                    || DEFAULTS.defaults.region,
                max_hours:     data.default_max_hours                  || DEFAULTS.defaults.max_hours,
                instance_type: data.default_instance_types?.linux      || DEFAULTS.defaults.instance_type,
            },
        }
    }
    console.warn(`[settings-bus] unknown schema_version ${v}, using defaults`)
    return _deepClone(DEFAULTS)
}

function _mergeDefaults(data) {
    return {
        schema_version: 2,
        plugins:   { ..._deepClone(DEFAULTS.plugins),   ...(data.plugins   || {}) },
        ui_panels: { ..._deepClone(DEFAULTS.ui_panels), ...(data.ui_panels || {}) },
        defaults:  { ..._deepClone(DEFAULTS.defaults),  ...(data.defaults  || {}) },
    }
}

function _dispatch(name, detail) {
    document.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
}

function _deepClone(obj) { return JSON.parse(JSON.stringify(obj)) }
