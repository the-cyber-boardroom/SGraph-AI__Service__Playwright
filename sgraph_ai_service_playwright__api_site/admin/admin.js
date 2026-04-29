// ── admin.js — Admin Dashboard page controller ──────────────────────────── //

import { apiClient    } from '../shared/api-client.js'
import { startVaultBus } from '../shared/vault-bus.js'

const LAYOUT_KEY = 'sp-cli:admin:layout:v3'                        // v3 — resets saved layouts from older shapes
const MODAL_TAG  = 'sp-cli-launch-modal'

const ADMIN_LAYOUT = {
    type: 'row', sizes: [0.42, 0.36, 0.22],
    children: [
        { type: 'stack', tabs: [
            { tag: 'sp-cli-catalog-pane',  title: 'Catalog',      locked: false },
        ]},
        { type: 'column', sizes: [0.55, 0.45], children: [
            { type: 'stack', tabs: [
                { tag: 'sp-cli-stacks-pane',   title: 'Stacks',       locked: true  },
            ]},
            { type: 'stack', tabs: [
                { tag: 'sp-cli-activity-pane', title: 'Activity Log', locked: false },
            ]},
        ]},
        { type: 'stack', tabs: [
            { tag: 'sp-cli-vault-activity', title: 'Vault Activity', locked: true  },
            { tag: 'sp-cli-stack-detail',   title: 'Stack Detail',   locked: false },
        ]},
    ],
}

document.addEventListener('DOMContentLoaded', async () => {
    let _region      = ''
    let _layoutEl    = null
    let _rightStackId = null
    const _vncTabIds = {}                                           // stack_name → sg-layout panelId

    startVaultBus()

    document.addEventListener('vault:connected', async (e) => {
        console.log('[admin] vault connected', e.detail?.vaultId)
        _setGate(true)
        await _initLayout()
        await _loadData()
    })

    document.addEventListener('vault:disconnected', () => {
        console.log('[admin] vault disconnected')
        _setGate(false)
    })

    document.addEventListener('sp-cli:stacks-refresh',   () => _loadData())
    document.addEventListener('sg-auth-saved',           () => _loadData())
    document.addEventListener('sp-cli:region-changed',   (e) => { _region = e.detail?.region || ''; _loadData() })

    document.addEventListener('sp-cli:catalog-launch',   (e) => _openModal(e.detail?.entry))
    document.addEventListener('sp-cli:user-launch',      (e) => _openModal(e.detail?.entry))

    document.addEventListener('sp-cli:launch-success', (e) => {
        const { entry, response } = e.detail
        const stackName = response?.stack_info?.stack_name || response?.stack_name || '?'
        _activity(`✓ Launched ${entry.display_name}: ${stackName}`)
        if (entry.type_id === 'vnc' && response?.operator_password) {
            sessionStorage.setItem(`vnc:pwd:${stackName}`, response.operator_password)
        }
        setTimeout(() => _loadData(), 3000)
    })

    document.addEventListener('sp-cli:launch-error', (e) => {
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })

    document.addEventListener('sp-cli:stack-deleted', (e) => {
        const stack = e.detail?.stack
        _activity(`🗑 Deleted ${stack?.type_id} stack: ${stack?.stack_name}`)
        if (stack?.type_id === 'vnc' && _vncTabIds[stack.stack_name]) {
            _layoutEl?.removePanel(_vncTabIds[stack.stack_name])
            delete _vncTabIds[stack.stack_name]
        }
        _loadData()
    })

    document.addEventListener('sp-cli:vnc-open-viewer', (e) => {
        const stack = e.detail?.stack
        if (stack) _openVncViewer(stack)
    })

    function _setGate(connected) {
        document.getElementById('vault-gate').hidden  = connected
        document.getElementById('main-content').hidden = !connected
    }

    async function _initLayout() {
        _layoutEl = document.getElementById('main-layout')
        if (!_layoutEl || _layoutEl._layoutReady) return
        _layoutEl._layoutReady = true

        const { SGL_EVENTS } = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout-events.js')
        await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')

        const saved = _loadLayout()
        _layoutEl.setLayout(saved || ADMIN_LAYOUT)

        _rightStackId = _findStackWithTag(_layoutEl.getLayout(), 'sp-cli-stack-detail')

        _layoutEl._events.on(SGL_EVENTS.LAYOUT_CHANGED, ({ tree }) => {
            try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(tree)) } catch (_) {}
        })
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
        const stacksPane  = document.querySelector('sp-cli-stacks-pane')
        const catalogPane = document.querySelector('sp-cli-catalog-pane')
        if (stacksPane)  stacksPane.setStacks(stacks)
        if (catalogPane) catalogPane.setTypes(types)
    }

    function _openModal(entry) {
        if (!entry) return
        const modal = document.querySelector(MODAL_TAG)
        modal?.open(entry)
    }

    function _openVncViewer(stack, password = '') {
        if (!_layoutEl || !_rightStackId) return

        if (_vncTabIds[stack.stack_name]) {
            _layoutEl.focusPanel(_vncTabIds[stack.stack_name])
            return
        }

        const pwd = password || sessionStorage.getItem(`vnc:pwd:${stack.stack_name}`) || ''
        const el  = document.createElement('sp-cli-vnc-viewer')

        const tabId = _layoutEl.addTabToStack(_rightStackId, {
            el,
            title:  `VNC: ${stack.stack_name}`,
            locked: false,
        }, true)

        if (tabId) {
            _vncTabIds[stack.stack_name] = tabId
            el.open(stack, pwd)
        }
    }

    function _activity(message) {
        document.dispatchEvent(new CustomEvent('sp-cli:activity-entry', {
            detail:  { message },
            bubbles: true, composed: true,
        }))
    }

    function _loadLayout() {
        try {
            const raw = localStorage.getItem(LAYOUT_KEY)
            return raw ? JSON.parse(raw) : null
        } catch (_) { return null }
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
})
