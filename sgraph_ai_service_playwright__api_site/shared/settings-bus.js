// ── settings-bus.js — Feature-toggle state + localStorage persistence ──────── //
// Module-level singleton. Owns in-memory settings state and persists locally.  //
// Vault integration paused pending refactor — see debrief 05/02 for details.  //
// Call startSettingsBus() once from the page controller.                        //

const LS_KEY = 'sp-cli:settings:v3'

const DEFAULTS = {
    schema_version: 3,
    use_legacy_api: false,
    plugins: {},   // populated from catalogue on sp-cli:catalogue.loaded
    ui_panels: {
        events_log:      { visible: true },
        vault_status:    { visible: true },
        active_sessions: { visible: true },
        cost_tracker:    { visible: true },
    },
    defaults: {
        region:        'eu-west-2',
        max_hours:     1,
        instance_type: 't3.medium',
    },
}

let _state  = _deepClone(DEFAULTS)
let _loaded = false

export function startSettingsBus() {
    _load()
}

function _load() {
    try {
        const raw = localStorage.getItem(LS_KEY)
        _state  = raw ? _migrate(JSON.parse(raw)) : _deepClone(DEFAULTS)
        _loaded = true
    } catch (err) {
        console.warn('[settings-bus] load failed, using defaults:', err.message)
        _state  = _deepClone(DEFAULTS)
        _loaded = true
    }
    _dispatch('sp-cli:settings.loaded', { settings: _deepClone(_state) })
}

// ── Readers ───────────────────────────────────────────────────────────────── //

export function isLoaded()              { return _loaded }
export function getPluginEnabled(name)  { return _state.plugins[name]?.enabled ?? false }
export function getAllPluginToggles()   { return _deepClone(_state.plugins) }
export function getUIPanelVisible(p)   { return _state.ui_panels[p]?.visible ?? true }
export function getDefault(key)        { return _state.defaults[key] }
export function getAllDefaults()        { return _deepClone(_state.defaults) }
export function getUseLegacyApi()      { return _state.use_legacy_api ?? false }

// ── Writers ───────────────────────────────────────────────────────────────── //

export async function setUseLegacyApi(val) {
    _state.use_legacy_api = !!val
    _dispatch('sp-cli:settings.use-legacy-api.changed', { use_legacy_api: !!val })
    _persist()
}

export async function setPluginEnabled(name, enabled) {
    if (!_state.plugins[name]) _state.plugins[name] = {}
    _state.plugins[name].enabled = !!enabled
    _dispatch('sp-cli:plugin.toggled', { name, enabled: !!enabled })
    _persist()
}

export async function setUIPanelVisible(panel, visible) {
    if (!_state.ui_panels[panel]) _state.ui_panels[panel] = {}
    _state.ui_panels[panel].visible = !!visible
    _dispatch('sp-cli:ui-panel.toggled', { panel, visible: !!visible })
    _persist()
}

export async function setDefault(key, value) {
    _state.defaults[key] = value
    _persist()
}

// ── Internal ──────────────────────────────────────────────────────────────── //

function _persist() {
    try {
        localStorage.setItem(LS_KEY, JSON.stringify(_state))
        _dispatch('sp-cli:settings.saved', {})
    } catch (err) {
        console.error('[settings-bus] persist failed:', err)
        _dispatch('sg-toast', { message: `Failed to save settings: ${err.message}`, tone: 'error' })
    }
}

function _migrate(data) {
    const v = data.schema_version || 1
    if (v === 3) return _mergeDefaults(data)
    if (v === 2) return _mergeDefaults({ ...data, use_legacy_api: data.use_legacy_api ?? false })
    if (v === 1) {
        return {
            schema_version: 3,
            use_legacy_api: false,
            plugins:        data.plugins   || _deepClone(DEFAULTS.plugins),
            ui_panels:      data.ui_panels || _deepClone(DEFAULTS.ui_panels),
            defaults: {
                region:        data.default_region                    || DEFAULTS.defaults.region,
                max_hours:     data.default_max_hours                  || DEFAULTS.defaults.max_hours,
                instance_type: data.default_instance_types?.podman     || DEFAULTS.defaults.instance_type,
            },
        }
    }
    console.warn(`[settings-bus] unknown schema_version ${v}, using defaults`)
    return _deepClone(DEFAULTS)
}

function _mergeDefaults(data) {
    return {
        schema_version: 3,
        use_legacy_api: data.use_legacy_api ?? false,
        plugins:   { ..._deepClone(DEFAULTS.plugins),   ...(data.plugins   || {}) },
        ui_panels: { ..._deepClone(DEFAULTS.ui_panels), ...(data.ui_panels || {}) },
        defaults:  { ..._deepClone(DEFAULTS.defaults),  ...(data.defaults  || {}) },
    }
}

function _dispatch(name, detail) {
    document.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
}

function _deepClone(obj) { return JSON.parse(JSON.stringify(obj)) }

// When the catalogue loads, ensure every spec has a plugin toggle (enabled by default).
// This replaces the old hardcoded DEFAULTS.plugins list.
document.addEventListener('sp-cli:catalogue.loaded', (e) => {
    let changed = false
    for (const spec of (e.detail?.specs || [])) {
        if (!_state.plugins[spec.spec_id]) {
            _state.plugins[spec.spec_id] = { enabled: true }
            changed = true
        }
    }
    if (changed) {
        _persist()
        _dispatch('sp-cli:plugin.toggled', {})
    }
})
