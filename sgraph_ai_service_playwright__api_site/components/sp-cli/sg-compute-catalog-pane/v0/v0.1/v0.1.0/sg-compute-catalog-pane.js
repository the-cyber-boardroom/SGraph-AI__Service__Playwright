/**
 * sg-compute-catalog-pane — Stack type catalog for the admin dashboard.
 *
 * Call setTypes(entries) with the entries array from GET /catalog/types.
 *
 * Events emitted:
 *   sp-cli:catalog-launch — { entry } — user clicked Launch on an available type
 *
 * @module sg-compute-catalog-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeCatalogPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-catalog-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._grid        = this.$('.type-grid')
        this._placeholder = this.$('.coming-soon')
        if (this._pendingTypes) {
            this.setTypes(this._pendingTypes)
            this._pendingTypes = null
        }
    }

    setTypes(entries = []) {
        if (!this._grid) { this._pendingTypes = entries; return }
        if (!entries.length) return
        this._placeholder.hidden = true
        this._grid.hidden        = false
        this._grid.innerHTML     = ''

        for (const e of entries) {
            const card = document.createElement('div')
            card.className = 'type-card' + (e.available ? '' : ' unavailable')
            card.innerHTML = `
                <div class="card-header">
                    <span class="card-name">${e.display_name}</span>
                    <span class="card-badge ${e.available ? 'badge-ok' : 'badge-soon'}">${e.available ? 'Available' : 'Soon'}</span>
                </div>
                <div class="card-desc">${e.description}</div>
                ${e.available ? '<button class="card-launch">Launch</button>' : ''}
            `
            if (e.available) {
                card.querySelector('.card-launch').addEventListener('click', () => {
                    this.emit('sp-cli:catalog-launch', { entry: e })
                })
            }
            this._grid.appendChild(card)
        }
    }
}

customElements.define('sg-compute-catalog-pane', SgComputeCatalogPane)
