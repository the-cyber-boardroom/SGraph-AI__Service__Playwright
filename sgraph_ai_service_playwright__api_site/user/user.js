// ── user.js — User Provisioning page controller ─────────────────────────── //

import { startVaultBus } from '../shared/vault-bus.js'

const LAYOUT_KEY  = 'sp-cli:user:layout'

const USER_LAYOUT = {
    type: 'row', sizes: [1.0, 0.0],
    children: [
        { type: 'stack', tabs: [
            { tag: 'sp-cli-user-pane',      title: 'Provision',      locked: true },
        ]},
        { type: 'stack', tabs: [
            { tag: 'sp-cli-vault-activity', title: 'Vault Activity', locked: true },
        ]},
    ],
}

document.addEventListener('DOMContentLoaded', async () => {
    startVaultBus()

    document.addEventListener('vault:connected', async (e) => {
        console.log('[user] vault connected', e.detail?.vaultId)
        _setGate(true)
        await _initLayout()
    })

    document.addEventListener('vault:disconnected', () => {
        console.log('[user] vault disconnected')
        _setGate(false)
    })

    function _setGate(connected) {
        const gate = document.getElementById('vault-gate')
        const main = document.getElementById('main-content')
        if (gate) gate.hidden = connected
        if (main) main.hidden = !connected
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

    function _loadLayout() {
        try {
            const raw = localStorage.getItem(LAYOUT_KEY)
            return raw ? JSON.parse(raw) : null
        } catch (_) { return null }
    }
})
