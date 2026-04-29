/**
 * sp-cli-stacks-pane — Active stacks list for the admin dashboard.
 *
 * PR-3: empty state. PR-4 wires real stack data from the API.
 *
 * Events emitted:
 *   sp-cli:stacks-refresh — user clicked the refresh button
 *
 * @module sp-cli-stacks-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliStacksPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-stacks-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._list       = this.$('.stack-list')
        this._emptyState = this.$('.empty-state')

        this.$('.btn-refresh')?.addEventListener('click', () => {
            this.emit('sp-cli:stacks-refresh')
        })

        this._render([])
    }

    setStacks(stacks = []) {
        this._render(stacks)
    }

    _render(stacks) {
        const hasStacks = stacks.length > 0
        this._list.hidden       = !hasStacks
        this._emptyState.hidden = hasStacks
    }
}

customElements.define('sp-cli-stacks-pane', SpCliStacksPane)
