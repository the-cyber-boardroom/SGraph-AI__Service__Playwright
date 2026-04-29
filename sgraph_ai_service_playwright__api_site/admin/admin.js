// ── admin.js — Admin Dashboard page controller ──────────────────────────── //

import { apiClient    } from '../shared/api-client.js'
import { startVaultBus } from '../shared/vault-bus.js'
import { startSettingsBus } from '../shared/settings-bus.js'

const ROOT_LAYOUT_KEY = 'sp-cli:admin:root-layout:v1'

const ROOT_LAYOUT = {
    type: 'row', sizes: [0.07, 0.78, 0.15],
    children: [
        { type: 'stack', tabs: [
            { tag: 'sp-cli-left-nav', title: 'Nav', locked: true },
        ]},
        { type: 'stack', tabs: [
            { tag: 'sp-cli-compute-view', title: 'Compute', locked: true },
        ]},
        { type: 'column', sizes: [0.30, 0.20, 0.20, 0.30], children: [
            { type: 'stack', tabs: [{ tag: 'sp-cli-events-log',      title: 'Events Log',      locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-vault-status',    title: 'Vault Status',    locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-active-sessions', title: 'Active Sessions', locked: true }] },
            { type: 'stack', tabs: [{ tag: 'sp-cli-cost-tracker',    title: 'Cost Tracker',    locked: true }] },
        ]},
    ],
}

const VIEW_TITLES = { compute: 'Compute', storage: 'Storage', settings: 'Settings', diagnostics: 'Diagnostics' }

document.addEventListener('DOMContentLoaded', async () => {
    let _layoutEl         = null
    let _layoutReady      = false
    let _mainStackId      = null
    let _currentView      = 'compute'
    let _currentViewTabId = null
    let _region           = ''
    let _detailTabIds     = {}                                      // stack_name → panelId
    let _detailTypeIds    = {}                                      // stack_name → type_id (for plugin toggle cleanup)
    let _launchTabIds     = {}                                      // type_id   → panelId

    startVaultBus()
    startSettingsBus()

    // ── Vault gate ────────────────────────────────────────────────────────── //

    document.addEventListener('vault:connected', async () => {
        _setGate(true)
        await _initLayout()
        await _loadData()
    })
    document.addEventListener('vault:disconnected', () => _setGate(false))

    // ── Navigation ────────────────────────────────────────────────────────── //

    document.addEventListener('sp-cli:nav.selected', (e) => _switchView(e.detail?.view))

    // ── Stack interactions ────────────────────────────────────────────────── //

    document.addEventListener('sp-cli:stack.selected',  (e) => _openDetailTab(e.detail?.stack))
    document.addEventListener('sp-cli:stack-selected',  (e) => _openDetailTab(e.detail?.stack)) // compat
    document.addEventListener('sp-cli:stack.deleted',   (e) => _onStackDeleted(e.detail?.stack))
    document.addEventListener('sp-cli:stack-deleted',   (e) => _onStackDeleted(e.detail?.stack)) // compat
    document.addEventListener('sp-cli:stacks.refresh',  () => _loadData())
    document.addEventListener('sp-cli:stacks-refresh',  () => _loadData())                       // compat
    document.addEventListener('sp-cli:region-changed',  (e) => { _region = e.detail?.region || ''; _loadData() })

    // ── Plugin / settings events ─────────────────────────────────────────── //

    document.addEventListener('sp-cli:plugin.toggled', (e) => {
        const { name, enabled } = e.detail || {}
        if (enabled) return
        for (const [stackName, tabId] of Object.entries(_detailTabIds)) {
            if (_detailTypeIds[stackName] === name) {
                _layoutEl?.removePanel(tabId)
                delete _detailTabIds[stackName]
                delete _detailTypeIds[stackName]
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

    // ── Launch flow (wired here; sp-cli-launch-panel added in PR-4) ───────── //

    const LAUNCH_TYPES = ['linux', 'docker', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko']
    LAUNCH_TYPES.forEach(t =>
        document.addEventListener(`sp-cli:plugin:${t}.launch-requested`, (e) => _openLaunchTab(e.detail?.entry))
    )
    document.addEventListener('sp-cli:catalog-launch', (e) => _openLaunchTab(e.detail?.entry)) // compat
    document.addEventListener('sp-cli:user-launch',    (e) => _openLaunchTab(e.detail?.entry)) // compat

    document.addEventListener('sp-cli:launch.success', (e) => {
        const { entry, response } = e.detail || {}
        const stackName = response?.stack_info?.stack_name || response?.stack_name || '?'
        _activity(`✓ Launched ${entry?.display_name}: ${stackName}`)
        if (_launchTabIds[entry?.type_id]) {
            _layoutEl?.removePanel(_launchTabIds[entry.type_id])
            delete _launchTabIds[entry.type_id]
        }
        setTimeout(() => _loadData(), 3_000)
    })
    document.addEventListener('sp-cli:launch-success', (e) => {                                // compat
        const { entry, response } = e.detail || {}
        const stackName = response?.stack_info?.stack_name || response?.stack_name || '?'
        _activity(`✓ Launched ${entry?.display_name}: ${stackName}`)
        setTimeout(() => _loadData(), 3_000)
    })
    document.addEventListener('sp-cli:launch.error', (e) => {
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })
    document.addEventListener('sp-cli:launch-error', (e) => {                                  // compat
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })

    document.addEventListener('sp-cli:launch.cancelled', (e) => {
        const typeId = e.detail?.entry?.type_id
        if (typeId && _launchTabIds[typeId]) {
            _layoutEl?.removePanel(_launchTabIds[typeId])
            delete _launchTabIds[typeId]
        }
    })

    // ── Stack stop / delete ───────────────────────────────────────────────── //

    document.addEventListener('sp-cli:stack.stop-requested', async (e) => {
        const stack = e.detail?.stack
        if (!stack) return
        try {
            await apiClient.delete(`/${stack.type_id}/stack/${stack.stack_name}`)
            _activity(`🗑 Deleted ${stack.type_id} stack: ${stack.stack_name}`)
            document.dispatchEvent(new CustomEvent('sp-cli:stack.deleted', {
                detail:  { stack },
                bubbles: true, composed: true,
            }))
        } catch (err) {
            _activity(`✗ Delete failed (${stack.stack_name}): ${err.message}`)
            document.dispatchEvent(new CustomEvent('sp-cli:stack.stop-failed', {
                detail:  { stack, error: err.message },
                bubbles: true, composed: true,
            }))
        }
    })

    // ── Helpers ───────────────────────────────────────────────────────────── //

    function _setGate(connected) {
        document.getElementById('vault-gate').hidden  = connected
        document.getElementById('main-content').hidden = !connected
    }

    async function _initLayout() {
        if (_layoutReady) return
        _layoutReady = true

        const { SGL_EVENTS } = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout-events.js')
        await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')

        _layoutEl = document.getElementById('root-layout')
        _layoutEl.setLayout(_loadLayout() || ROOT_LAYOUT)

        const tree      = _layoutEl.getLayout()
        _mainStackId    = _findMainStackId(tree)
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

    function _openDetailTab(stack) {
        if (!stack || !_layoutEl || !_mainStackId) return
        if (_detailTabIds[stack.stack_name]) {
            _layoutEl.focusPanel(_detailTabIds[stack.stack_name])
            return
        }
        const displayType = _capitalize(stack.type_id)
        const tabId = _layoutEl.addTabToStack(_mainStackId, {
            tag:    `sp-cli-${stack.type_id}-detail`,
            title:  `${displayType}: ${stack.stack_name}`,
            locked: false,
        }, true)
        if (tabId) {
            _detailTabIds[stack.stack_name]  = tabId
            _detailTypeIds[stack.stack_name] = stack.type_id
            _layoutEl.getPanelElement(tabId)?.open?.(stack)
        }
    }

    function _openLaunchTab(entry) {
        if (!entry || !_layoutEl || !_mainStackId) return
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
            _layoutEl.getPanelElement(tabId)?.open?.(entry)
        }
    }

    function _onStackDeleted(stack) {
        if (!stack) return
        _activity(`🗑 Deleted ${stack.type_id} stack: ${stack.stack_name}`)
        if (_detailTabIds[stack.stack_name]) {
            _layoutEl?.removePanel(_detailTabIds[stack.stack_name])
            delete _detailTabIds[stack.stack_name]
            delete _detailTypeIds[stack.stack_name]
        }
        _loadData()
    }

    async function _loadData() {
        try {
            const regionParam = _region ? `?region=${encodeURIComponent(_region)}` : ''
            const [catalogResp, stacksResp] = await Promise.all([
                apiClient.get('/catalog/types'),
                apiClient.get(`/catalog/stacks${regionParam}`),
            ])
            _populatePanes(catalogResp?.entries || [], stacksResp?.stacks || [])
        } catch (err) {
            console.warn('[admin] data load failed:', err.message)
            if (err.message?.includes('Unauthenticated') || err.message?.includes('401')) {
                document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }))
            }
        }
    }

    function _populatePanes(types, stacks) {
        document.querySelector('sp-cli-compute-view')?.setData?.({ types, stacks })
        document.querySelector('sp-cli-stacks-pane')?.setStacks?.(stacks)
        document.querySelector('sp-cli-cost-tracker')?.setStacks?.(stacks)
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

    // Find the stack ID that holds the current main view
    function _findMainStackId(tree) {
        const viewTags = [
            'sp-cli-compute-view', 'sp-cli-storage-view',
            'sp-cli-settings-view', 'sp-cli-diagnostics-view',
        ]
        for (const tag of viewTags) {
            const id = _findStackWithTag(tree, tag)
            if (id) return id
        }
        return null
    }

    // Find the tab ID for the currently active view inside a given stack
    function _findCurrentViewTabId(tree, mainStackId) {
        const stack = _findNodeById(tree, mainStackId)
        if (!stack) return null
        const viewTags = [
            'sp-cli-compute-view', 'sp-cli-storage-view',
            'sp-cli-settings-view', 'sp-cli-diagnostics-view',
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
