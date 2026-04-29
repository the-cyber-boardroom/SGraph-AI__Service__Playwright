/**
 * sp-cli-user-pane — Main pane for the user provisioning page.
 *
 * PR-3: empty states for both sections. PR-5 wires type cards and stack strip.
 *
 * @module sp-cli-user-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliUserPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-user-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._typeGrid          = this.$('.type-grid')
        this._stackStrip        = this.$('.stack-strip')
        this._emptyStateTypes   = this.$('.empty-state-types')
        this._emptyStateStacks  = this.$('.empty-state-stacks')

        this._renderTypes([])
        this._renderStacks([])
    }

    setTypes(types = []) {
        this._renderTypes(types)
    }

    setStacks(stacks = []) {
        this._renderStacks(stacks)
    }

    _renderTypes(types) {
        this._typeGrid.hidden         = types.length === 0
        this._emptyStateTypes.hidden  = types.length > 0
    }

    _renderStacks(stacks) {
        this._stackStrip.hidden       = stacks.length === 0
        this._emptyStateStacks.hidden = stacks.length > 0
    }
}

customElements.define('sp-cli-user-pane', SpCliUserPane)
