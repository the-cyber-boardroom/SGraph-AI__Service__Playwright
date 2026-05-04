/**
 * sp-cli-stacks-pane — Active stacks list for the admin dashboard.
 *
 * Events emitted:
 *   sp-cli:stacks-refresh    — user clicked the refresh button
 *   sp-cli:stack-selected    — { stack } — user clicked a stack row
 *
 * @module sp-cli-stacks-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

function _fmtUptime(seconds) {
    if (!seconds || seconds < 0) return '—'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m`
    return `${seconds}s`
}

function _stateClass(state) {
    const s = (state || '').toLowerCase()
    if (s === 'running')                        return 'state-running'
    if (s === 'stopped' || s === 'terminated')  return 'state-stopped'
    return 'state-pending'
}

class SpCliStacksPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-stacks-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._list       = this.$('.stack-list')
        this._emptyState = this.$('.empty-state')
        this._counter    = this.$('.stack-count')

        this.$('.btn-refresh')?.addEventListener('click', () => {
            this.emit('sp-cli:nodes.refresh')
            this.emit('sp-cli:stacks.refresh')   // DEPRECATED — remove in F9
            this.emit('sp-cli:stacks-refresh')   // DEPRECATED — remove in F9
        })

        if (this._pendingStacks !== undefined) {
            this._render(this._pendingStacks)
            this._pendingStacks = undefined
        } else {
            this._render([])
        }
    }

    setStacks(stacks = []) {
        if (!this._list) { this._pendingStacks = stacks; return }
        this._render(stacks)
    }

    _render(stacks) {
        const hasStacks = stacks.length > 0
        this._emptyState.hidden = hasStacks
        this._list.hidden       = !hasStacks

        if (this._counter) this._counter.textContent = hasStacks ? `(${stacks.length})` : ''

        if (!hasStacks) { this._list.innerHTML = ''; return }

        this._list.innerHTML = ''
        for (const s of stacks) {
            const row = document.createElement('div')
            row.className = 'stack-row'
            row.innerHTML = `
                <span class="type-badge type-${s.type_id}">${s.type_id}</span>
                <span class="stack-name">${s.stack_name}</span>
                <span class="state-badge ${_stateClass(s.state)}">${s.state}</span>
                <span class="stack-ip">${s.public_ip || '—'}</span>
                <span class="stack-uptime">${_fmtUptime(s.uptime_seconds)}</span>
            `
            row.addEventListener('click', () => {
                this.emit('sp-cli:node.selected',   { stack: s })
                this.emit('sp-cli:stack.selected',  { stack: s })  // DEPRECATED — remove in F9
                this.emit('sp-cli:stack-selected',  { stack: s })  // DEPRECATED — remove in F9
            })
            this._list.appendChild(row)
        }
    }
}

customElements.define('sp-cli-stacks-pane', SpCliStacksPane)
