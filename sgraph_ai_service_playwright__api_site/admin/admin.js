// ── admin.js — Admin Dashboard page controller ──────────────────────────── //

import { apiClient    } from '../shared/api-client.js'
import { startVaultBus } from '../shared/vault-bus.js'

const LAYOUT_KEY    = 'sp-cli:admin:layout'
const MODAL_TAG     = 'sp-cli-launch-modal'

const ADMIN_LAYOUT = {
    type: 'row', sizes: [0.72, 0.28],
    children: [
        { type: 'stack', tabs: [
            { tag: 'sp-cli-stacks-pane',   title: 'Stacks',       locked: true  },
            { tag: 'sp-cli-catalog-pane',  title: 'Catalog',      locked: false },
            { tag: 'sp-cli-activity-pane', title: 'Activity Log', locked: false },
        ]},
        { type: 'stack', tabs: [
            { tag: 'sp-cli-vault-activity', title: 'Vault Activity', locked: true },
        ]},
    ],
}

document.addEventListener('DOMContentLoaded', async () => {
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

    document.addEventListener('sp-cli:stacks-refresh', () => _loadData())

    document.addEventListener('sg-auth-saved', () => _loadData())

    document.addEventListener('sp-cli:catalog-launch', (e) => _openModal(e.detail?.entry))
    document.addEventListener('sp-cli:user-launch',    (e) => _openModal(e.detail?.entry))

    document.addEventListener('sp-cli:launch-success', (e) => {
        const { entry, response } = e.detail
        const stackName = response?.stack_info?.stack_name || response?.stack_name || '?'
        _activity(`✓ Launched ${entry.display_name}: ${stackName}`)
        setTimeout(() => _loadData(), 3000)
    })

    document.addEventListener('sp-cli:launch-error', (e) => {
        _activity(`✗ Launch failed (${e.detail?.entry?.display_name}): ${e.detail?.error}`)
    })

    function _setGate(connected) {
        document.getElementById('vault-gate').hidden  = connected
        document.getElementById('main-content').hidden = !connected
    }

    async function _initLayout() {
        const layoutEl = document.getElementById('main-layout')
        if (!layoutEl || layoutEl._layoutReady) return
        layoutEl._layoutReady = true

        const { SGL_EVENTS } = await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout-events.js')
        await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')

        const saved = _loadLayout()
        layoutEl.setLayout(saved || ADMIN_LAYOUT)

        layoutEl._events.on(SGL_EVENTS.LAYOUT_CHANGED, ({ tree }) => {
            try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(tree)) } catch (_) {}
        })
    }

    async function _loadData() {
        try {
            const [catalogResp, stacksResp] = await Promise.all([
                apiClient.get('/catalog/types'),
                apiClient.get('/catalog/stacks'),
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
})
