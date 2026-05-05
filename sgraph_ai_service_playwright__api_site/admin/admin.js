// ── admin.js — Admin Dashboard page controller ──────────────────────────── //

import { apiClient         } from '../shared/api-client.js'
import { startSettingsBus, getUseLegacyApi } from '../shared/settings-bus.js'

const ROOT_LAYOUT_KEY   = 'sp-cli:admin:root-layout:v2'
const HOST_API_KEYS_KEY = 'sp-cli:host-api-keys'

function _loadHostApiKeys() {
    try { return JSON.parse(localStorage.getItem(HOST_API_KEYS_KEY) || '{}') } catch { return {} }
}

function _saveHostApiKeys(map) {
    try { localStorage.setItem(HOST_API_KEYS_KEY, JSON.stringify(map)) } catch {}
}

function _buildRootLayout() {
    return {
        type: 'row', sizes: [0.07, 0.93],
        children: [
            { type: 'stack', tabs: [{ tag: 'sp-cli-left-nav',     title: 'Nav',     locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-compute-view', title: 'Compute', locked: true }] },
        ],
    }
}

const VIEW_TITLES = { compute: 'Compute', nodes: 'Active Nodes', stacks: 'Stacks', settings: 'Settings', diagnostics: 'Diagnostics', api: 'API Docs' }

document.addEventListener('DOMContentLoaded', async () => {
    let _layoutEl         = null
    let _layoutReady      = false
    let _mainStackId      = null
    let _currentView      = 'compute'
    let _currentViewTabId = null
    let _region           = ''
    let _detailTabIds     = {}      // node_id → panelId
    let _detailTypeIds    = {}      // node_id → spec_id
    let _launchTabIds     = {}      // spec_id → panelId
    let _hostApiKeys      = _loadHostApiKeys()  // node_id → api_key_value

    startSettingsBus()

    // ── Boot immediately ──────────────────────────────────────────────────── //

    await _initLayout()
    _loadData()

    // ── Settings loaded → re-init layout if settings fired before boot ────── //

    document.addEventListener('sp-cli:settings.loaded', async () => {
        if (!_layoutReady) await _initLayout()
    })

    // ── Navigation ────────────────────────────────────────────────────────── //

    document.addEventListener('sp-cli:nav.selected', (e) => {
        const view = e.detail?.view
        if (view === 'diagnostics') _toggleDiagnostics()
        else _switchView(view)
    })

    // ── Stack interactions ────────────────────────────────────────────────── //

    document.addEventListener('sp-cli:node.selected',   (e) => _openDetailTab(e.detail?.stack))
    document.addEventListener('sp-cli:node.deleted',    (e) => _onStackDeleted(e.detail?.stack))
    document.addEventListener('sp-cli:nodes.refresh',   () => _loadData())
    document.addEventListener('sp-cli:stack.selected',  (e) => _openDetailTab(e.detail?.stack))  // DEPRECATED
    document.addEventListener('sp-cli:stack-selected',  (e) => _openDetailTab(e.detail?.stack))  // DEPRECATED
    document.addEventListener('sp-cli:stack.deleted',   (e) => _onStackDeleted(e.detail?.stack)) // DEPRECATED
    document.addEventListener('sp-cli:stack-deleted',   (e) => _onStackDeleted(e.detail?.stack)) // DEPRECATED
    document.addEventListener('sp-cli:stacks.refresh',  () => _loadData())                       // DEPRECATED
    document.addEventListener('sp-cli:stacks-refresh',  () => _loadData())                       // DEPRECATED
    document.addEventListener('sp-cli:region-changed',  (e) => { _region = e.detail?.region || ''; _loadData() })

    // ── Plugin / settings events ─────────────────────────────────────────── //

    document.addEventListener('sp-cli:plugin.toggled', (e) => {
        const { name, enabled } = e.detail || {}
        if (enabled) return
        for (const [nodeId, tabId] of Object.entries(_detailTabIds)) {
            if (_detailTypeIds[nodeId] === name) {
                _layoutEl?.removePanel(tabId)
                delete _detailTabIds[nodeId]
                delete _detailTypeIds[nodeId]
                _activity(`Closed ${name} detail (plugin disabled)`)
            }
        }
        if (_launchTabIds[name]) {
            _layoutEl?.removePanel(_launchTabIds[name])
            delete _launchTabIds[name]
        }
    })

    // ── Auth ──────────────────────────────────────────────────────────────── //

    document.addEventListener('sg-auth-saved', () => _loadData())

    // ── Launch flow ───────────────────────────────────────────────────────── //

    const LAUNCH_TYPES = ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']
    LAUNCH_TYPES.forEach(t =>
        document.addEventListener(`sp-cli:plugin:${t}.launch-requested`, (e) => _openLaunchTab(e.detail?.entry))
    )
    document.addEventListener('sp-cli:catalog-launch', (e) => _openLaunchTab(e.detail?.entry)) // compat
    document.addEventListener('sp-cli:user-launch',    (e) => _openLaunchTab(e.detail?.entry)) // compat

    document.addEventListener('sp-cli:node.launched', (e) => {
        const { response } = e.detail || {}
        const nodeId = response?.node_id || response?.stack_info?.stack_name || response?.stack_name
        const apiKey = response?.api_key_value
        if (nodeId && apiKey) {
            _hostApiKeys[nodeId] = apiKey
            _saveHostApiKeys(_hostApiKeys)
        }
    })

    document.addEventListener('sp-cli:launch.success', (e) => {
        const { entry, response } = e.detail || {}
        const nodeId  = response?.node_id || response?.stack_info?.stack_name || response?.stack_name || '?'
        const specId  = entry?.spec_id || entry?.type_id
        _activity(`✓ Launched ${entry?.display_name}: ${nodeId}`)
        if (specId && _launchTabIds[specId]) {
            _layoutEl?.removePanel(_launchTabIds[specId])
            delete _launchTabIds[specId]
        }
        setTimeout(() => _loadData(), 1_000)
    })
    document.addEventListener('sp-cli:launch-success', (e) => {                                // compat
        const { entry, response } = e.detail || {}
        const nodeId = response?.node_id || response?.stack_info?.stack_name || response?.stack_name || '?'
        _activity(`✓ Launched ${entry?.display_name}: ${nodeId}`)
        setTimeout(() => _loadData(), 1_000)
    })
    document.addEventListener('sp-cli:launch.error', (e) => {
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })
    document.addEventListener('sp-cli:launch-error', (e) => {                                  // compat
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })

    document.addEventListener('sp-cli:launch.cancelled', (e) => {
        const specId = e.detail?.entry?.spec_id || e.detail?.entry?.type_id
        if (specId && _launchTabIds[specId]) {
            _layoutEl?.removePanel(_launchTabIds[specId])
            delete _launchTabIds[specId]
        }
    })

    // ── Stack stop / delete ───────────────────────────────────────────────── //

    document.addEventListener('sp-cli:stack.stop-requested', async (e) => {
        const stack = e.detail?.stack
        if (!stack) return
        const nodeId = stack.node_id || stack.stack_name
        try {
            await apiClient.delete(`/api/nodes/${nodeId}`)
            _activity(`🗑 Deleted ${stack.spec_id || stack.type_id} node: ${nodeId}`)
            document.dispatchEvent(new CustomEvent('sp-cli:stack.deleted', {
                detail:  { stack },
                bubbles: true, composed: true,
            }))
        } catch (err) {
            _activity(`✗ Delete failed (${nodeId}): ${err.message}`)
            document.dispatchEvent(new CustomEvent('sp-cli:stack.stop-failed', {
                detail:  { stack, error: err.message },
                bubbles: true, composed: true,
            }))
        }
    })

    // ── Helpers ───────────────────────────────────────────────────────────── //

    async function _initLayout() {
        if (_layoutReady) return
        _layoutReady = true

        const { SGL_EVENTS } = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout-events.js')
        await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')

        _layoutEl = document.getElementById('root-layout')
        _layoutEl.setLayout(_loadLayout() || _buildRootLayout())

        const tree        = _layoutEl.getLayout()
        _mainStackId      = _findMainStackId(tree)
        _currentViewTabId = _findCurrentViewTabId(tree, _mainStackId)

        _layoutEl._events.on(SGL_EVENTS.LAYOUT_CHANGED, ({ tree }) => {
            try { localStorage.setItem(ROOT_LAYOUT_KEY, JSON.stringify(tree)) } catch (_) {}
        })
    }

    function _switchView(view) {
        if (!_layoutEl || !_mainStackId || !view || view === _currentView) return
        const tag   = `sp-cli-${view}-view`
        const title = VIEW_TITLES[view] || view

        const newTabId = _layoutEl.addTabToStack(_mainStackId, { tag, title, locked: true }, true)
        if (_currentViewTabId) _layoutEl.removePanel(_currentViewTabId)
        _currentViewTabId = newTabId
        _currentView      = view
    }

    function _toggleDiagnostics() {
        const col = document.getElementById('diag-col')
        if (col) col.hidden = !col.hidden
    }

    function _openDetailTab(stack) {
        if (!stack || !_layoutEl || !_mainStackId) return
        const nodeId = stack.node_id || stack.stack_name
        const specId = stack.spec_id || stack.type_id
        if (_detailTabIds[nodeId]) {
            _layoutEl.focusPanel(_detailTabIds[nodeId])
            return
        }
        const displayType = _capitalize(specId)
        const tabId = _layoutEl.addTabToStack(_mainStackId, {
            tag:    `sp-cli-${specId}-detail`,
            title:  `${displayType}: ${nodeId}`,
            locked: false,
        }, true)
        if (tabId) {
            _detailTabIds[nodeId]  = tabId
            _detailTypeIds[nodeId] = specId
            _layoutEl.getPanelElement(tabId)?.open?.(stack)
        }
    }

    function _openLaunchTab(entry) {
        if (!entry || !_layoutEl || !_mainStackId) return
        const specId = entry.spec_id || entry.type_id
        if (_launchTabIds[specId]) {
            _layoutEl.focusPanel(_launchTabIds[specId])
            return
        }
        const tabId = _layoutEl.addTabToStack(_mainStackId, {
            tag:    'sp-cli-launch-panel',
            title:  `Launching ${entry.display_name}`,
            locked: false,
        }, true)
        if (tabId) {
            _launchTabIds[specId] = tabId
            _layoutEl.getPanelElement(tabId)?.open?.(entry)
        }
    }

    function _onStackDeleted(stack) {
        if (!stack) return
        const nodeId = stack.node_id || stack.stack_name
        const specId = stack.spec_id || stack.type_id
        _activity(`🗑 Deleted ${specId} node: ${nodeId}`)
        if (_detailTabIds[nodeId]) {
            _layoutEl?.removePanel(_detailTabIds[nodeId])
            delete _detailTabIds[nodeId]
            delete _detailTypeIds[nodeId]
        }
        _loadData()
    }

    async function _loadData() {
        try {
            const regionParam = _region ? `?region=${encodeURIComponent(_region)}` : ''
            const useLegacy   = getUseLegacyApi()
            const specsUrl    = useLegacy ? '/catalog/types'                         : '/api/specs'
            const nodesUrl    = useLegacy ? `/catalog/stacks${regionParam}`          : `/api/nodes${regionParam}`
            const [catalogResp, nodesResp] = await Promise.all([
                apiClient.get(specsUrl),
                apiClient.get(nodesUrl),
            ])
            const specs = useLegacy ? (catalogResp?.entries || []) : (catalogResp?.specs || [])
            const nodes = useLegacy ? (nodesResp?.stacks   || []) : (nodesResp?.nodes  || [])
            _populatePanes(specs, nodes)
        } catch (err) {
            console.warn('[admin] data load failed:', err.message)
            if (err.message?.includes('Unauthenticated') || err.message?.includes('401')) {
                document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }))
            }
        }
    }

    function _populatePanes(types, stacks) {
        // Augment each node with its stored host API key (captured on launch)
        const augmented = stacks.map(s => ({
            ...s,
            host_api_key: _hostApiKeys[s.node_id || s.stack_name] || s.host_api_key || '',
        }))
        document.querySelector('sp-cli-compute-view')?.setData?.({ types, stacks })
        document.querySelector('sp-cli-nodes-view')?.setStacks?.(augmented)
        document.querySelector('sp-cli-stacks-pane')?.setStacks?.(stacks)
        // cost-tracker may be inside shadow DOM (diagnostics view); use event so it receives data
        document.dispatchEvent(new CustomEvent('sp-cli:stacks.updated', {
            detail: { stacks }, bubbles: true, composed: true,
        }))
    }

    function _activity(message) {
        document.dispatchEvent(new CustomEvent('sp-cli:activity-entry', {
            detail:  { message },
            bubbles: true, composed: true,
        }))
    }

    function _loadLayout() {
        try {
            const raw = localStorage.getItem(ROOT_LAYOUT_KEY)
            return raw ? JSON.parse(raw) : null
        } catch (_) { return null }
    }

    function _capitalize(s) { return s ? s[0].toUpperCase() + s.slice(1) : '' }

    function _findMainStackId(tree) {
        const viewTags = [
            'sp-cli-compute-view', 'sp-cli-nodes-view', 'sp-cli-stacks-view', 'sp-cli-storage-view',
            'sp-cli-settings-view', 'sp-cli-diagnostics-view', 'sp-cli-api-view',
        ]
        for (const tag of viewTags) {
            const id = _findStackWithTag(tree, tag)
            if (id) return id
        }
        return null
    }

    function _findCurrentViewTabId(tree, mainStackId) {
        const stack = _findNodeById(tree, mainStackId)
        if (!stack) return null
        const viewTags = [
            'sp-cli-compute-view', 'sp-cli-nodes-view', 'sp-cli-stacks-view', 'sp-cli-storage-view',
            'sp-cli-settings-view', 'sp-cli-diagnostics-view', 'sp-cli-api-view',
        ]
        for (const tag of viewTags) {
            const tab = stack.tabs?.find(t => t.tag === tag)
            if (tab?.id) {
                _currentView = tag.replace('sp-cli-', '').replace('-view', '')
                return tab.id
            }
        }
        return null
    }

    function _findStackWithTag(tree, tag) {
        if (!tree) return null
        if (tree.type === 'stack' && tree.tabs?.some(t => t.tag === tag)) return tree.id
        for (const child of tree.children || []) {
            const found = _findStackWithTag(child, tag)
            if (found) return found
        }
        return null
    }

    function _findNodeById(tree, id) {
        if (!tree || !id) return null
        if (tree.id === id) return tree
        for (const child of tree.children || []) {
            const found = _findNodeById(child, id)
            if (found) return found
        }
        return null
    }
})
