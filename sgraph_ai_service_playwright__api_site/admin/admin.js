// ── admin.js — Admin Dashboard page controller ──────────────────────────── //
// PR-2: vault-bus bootstrap + vault gate. Stack data wired in PR-4.         //

import { apiClient   } from '../shared/api-client.js'
import { startVaultBus } from '../shared/vault-bus.js'

document.addEventListener('DOMContentLoaded', () => {
    startVaultBus()

    document.addEventListener('vault:connected', async (e) => {
        console.log('[admin] vault connected', e.detail?.vaultId)
        _setGate(true)
        // PR-3: populate sg-layout
        // PR-4: load catalog + active stacks
    })

    document.addEventListener('vault:disconnected', () => {
        console.log('[admin] vault disconnected')
        _setGate(false)
    })

    function _setGate(connected) {
        const gate = document.getElementById('vault-gate')
        const main = document.getElementById('main-content')
        if (gate) gate.hidden = connected
        if (main) main.hidden = !connected
    }
})
