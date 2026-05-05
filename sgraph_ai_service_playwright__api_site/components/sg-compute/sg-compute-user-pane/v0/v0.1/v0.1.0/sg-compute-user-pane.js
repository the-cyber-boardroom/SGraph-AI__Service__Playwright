/**
 * sg-compute-user-pane — Main pane for the user provisioning page.
 *
 * Call setTypes(entries) with entries from GET /catalog/types.
 * Call setStacks(stacks) with stacks from GET /catalog/stacks.
 *
 * Events emitted:
 *   sp-cli:user-launch       — { entry } — Launch clicked on a type card
 *   sp-cli:stack-selected    — { stack } — user clicked a stack row
 *
 * @module sg-compute-user-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { stateClass } from '../../../../../../shared/node-state.js'

function _fmtUptime(seconds) {
    if (!seconds || seconds < 0) return '—'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m`
    return `${seconds}s`
}

function _stateClass(state) {
    return stateClass(state)
}

class SgComputeUserPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-user-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._typeGrid         = this.$('.type-grid')
        this._stackStrip       = this.$('.stack-strip')
        this._emptyStateTypes  = this.$('.empty-state-types')
        this._emptyStateStacks = this.$('.empty-state-stacks')

        if (this._pendingTypes   !== undefined) { this.setTypes(this._pendingTypes);   this._pendingTypes   = undefined }
        if (this._pendingStacks  !== undefined) { this.setStacks(this._pendingStacks); this._pendingStacks  = undefined }
    }

    setTypes(entries = []) {
        if (!this._typeGrid) { this._pendingTypes = entries; return }
        const available = entries.filter(e => e.available)
        const hasTypes  = available.length > 0
        this._typeGrid.hidden        = !hasTypes
        this._emptyStateTypes.hidden = hasTypes

        if (!hasTypes) { this._typeGrid.innerHTML = ''; return }

        this._typeGrid.innerHTML = ''
        for (const e of available) {
            const card = document.createElement('div')
            card.className = 'type-card'
            card.innerHTML = `
                <div class="card-name">${e.display_name}</div>
                <div class="card-desc">${e.description}</div>
                <button class="card-launch">Launch</button>
            `
            card.querySelector('.card-launch').addEventListener('click', () => {
                this.emit('sp-cli:user-launch', { entry: e })
            })
            this._typeGrid.appendChild(card)
        }
    }

    setStacks(stacks = []) {
        if (!this._stackStrip) { this._pendingStacks = stacks; return }
        const hasStacks = stacks.length > 0
        this._stackStrip.hidden       = !hasStacks
        this._emptyStateStacks.hidden = hasStacks

        if (!hasStacks) { this._stackStrip.innerHTML = ''; return }

        this._stackStrip.innerHTML = ''
        for (const s of stacks) {
            const row = document.createElement('div')
            row.className = 'stack-row'
            row.innerHTML = `
                <span class="type-badge type-${s.spec_id}">${s.spec_id}</span>
                <span class="stack-name">${s.node_id}</span>
                <span class="state-badge ${_stateClass(s.state)}">${s.state}</span>
                <span class="stack-uptime">${_fmtUptime(s.uptime_seconds)}</span>
            `
            row.addEventListener('click', () => this.emit('sp-cli:stack-selected', { stack: s }))
            this._stackStrip.appendChild(row)
        }
    }
}

customElements.define('sg-compute-user-pane', SgComputeUserPane)
