/**
 * sp-cli-activity-pane — Activity log for the admin dashboard.
 *
 * Listens for sp-cli:activity-entry events on document and appends them.
 *
 * @module sp-cli-activity-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliActivityPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-activity-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._list       = this.$('.entry-list')
        this._emptyState = this.$('.empty-state')

        this.$('.btn-clear')?.addEventListener('click', () => this._clear())

        document.addEventListener('sp-cli:activity-entry', (e) => this._append(e.detail))
    }

    _append(detail = {}) {
        this._emptyState.hidden = true
        const row = document.createElement('div')
        row.className = 'entry-row'
        const ts   = new Date().toLocaleTimeString()
        row.textContent = `[${ts}] ${detail.message || JSON.stringify(detail)}`
        this._list.appendChild(row)
        this._list.scrollTop = this._list.scrollHeight
    }

    _clear() {
        this._list.innerHTML    = ''
        this._emptyState.hidden = false
    }
}

customElements.define('sp-cli-activity-pane', SpCliActivityPane)
