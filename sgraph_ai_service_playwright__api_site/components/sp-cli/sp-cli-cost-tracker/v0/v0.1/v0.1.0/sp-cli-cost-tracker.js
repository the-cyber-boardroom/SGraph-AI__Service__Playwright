/**
 * sp-cli-cost-tracker — placeholder cost tracker.
 *
 * Shows mocked cost estimate from active stacks × instance type rates.
 * Real cost calculation is its own brief.
 *
 * @module sp-cli-cost-tracker
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { isRunning   } from '../../../../../../shared/node-state.js'

const HOURLY_RATES = { 't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832, 't3.xlarge': 0.1664 }

class SpCliCostTracker extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-cost-tracker' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._rowsEl  = this.$('.cost-rows')
        this._totalEl = this.$('.cost-total-val')
        this._stacks  = []
        document.addEventListener('sp-cli:stacks.updated', (e) => this.setStacks(e.detail?.stacks))
    }

    setStacks(stacks) {
        this._stacks = stacks || []
        this._render()
    }

    _render() {
        const running = this._stacks.filter(s => isRunning(s.state))
        if (!this._rowsEl) return
        this._rowsEl.innerHTML = ''
        let total = 0

        for (const s of running) {
            const rate     = HOURLY_RATES[s.instance_type] || 0.04
            const hours    = Math.max((s.uptime_seconds || 0) / 3600, 0.1)
            const cost     = rate * hours
            total         += cost

            const row      = document.createElement('div')
            row.className  = 'cost-row'
            row.innerHTML  = `
                <span class="cost-name">${_esc(s.node_id)}</span>
                <span class="cost-type">${_esc(s.instance_type || '—')}</span>
                <span class="cost-val">$${cost.toFixed(2)}</span>
            `
            this._rowsEl.appendChild(row)
        }

        if (this._totalEl) this._totalEl.textContent = `$${total.toFixed(2)}`
        if (running.length === 0 && this._rowsEl) {
            this._rowsEl.innerHTML = '<div class="cost-empty">No running stacks.</div>'
        }
    }
}

function _esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

customElements.define('sp-cli-cost-tracker', SpCliCostTracker)
