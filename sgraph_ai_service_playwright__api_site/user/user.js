// ── user.js — User Provisioning page controller ─────────────────────────── //

import { apiClient    } from '../shared/api-client.js'
import { startVaultBus } from '../shared/vault-bus.js'

const LAYOUT_KEY  = 'sp-cli:user:layout'
const MODAL_TAG   = 'sg-compute-launch-modal'

const USER_LAYOUT = {
    type: 'row', sizes: [1.0, 0.0],
    children: [
        { type: 'stack', tabs: [
            { tag: 'sg-compute-user-pane',      title: 'Provision',      locked: true },
        ]},
        { type: 'stack', tabs: [
            { tag: 'sg-compute-vault-activity', title: 'Vault Activity', locked: true },
        ]},
    ],
}

document.addEventListener('DOMContentLoaded', async () => {
    let _region = ''
    startVaultBus()

    document.addEventListener('vault:connected', async (e) => {
        console.log('[user] vault connected', e.detail?.vaultId)
        _setGate(true)
        await _initLayout()
        await _loadData()
    })

    document.addEventListener('vault:disconnected', () => {
        console.log('[user] vault disconnected')
        _setGate(false)
    })

    document.addEventListener('sg-auth-saved',         () => _loadData())
    document.addEventListener('sp-cli:region-changed', (e) => { _region = e.detail?.region || ''; _loadData() })

    document.addEventListener('sp-cli:user-launch', (e) => _openModal(e.detail?.entry))

    document.addEventListener('sp-cli:launch-success', (e) => {
        const { entry, response } = e.detail
        const stackName = response?.stack_info?.stack_name || response?.stack_name || '?'
        console.log('[user] launched', entry.display_name, stackName)
        setTimeout(() => _loadData(), 3000)
    })

    document.addEventListener('sp-cli:stack-deleted', () => _loadData())

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
        layoutEl.setLayout(saved || USER_LAYOUT)

        layoutEl._events.on(SGL_EVENTS.LAYOUT_CHANGED, ({ tree }) => {
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
            console.warn('[user] data load failed:', err.message)
            if (err.message?.includes('Unauthenticated') || err.message?.includes('401')) {
                document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }))
            }
        }
    }

    function _populatePanes(types, stacks) {
        const userPane = document.querySelector('sg-compute-user-pane')
        if (userPane) {
            userPane.setTypes(types)
            userPane.setStacks(stacks)
        }
    }

    function _openModal(entry) {
        if (!entry) return
        const modal = document.querySelector(MODAL_TAG)
        modal?.open(entry)
    }

    function _loadLayout() {
        try {
            const raw = localStorage.getItem(LAYOUT_KEY)
            return raw ? JSON.parse(raw) : null
        } catch (_) { return null }
    }
})
