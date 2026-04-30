import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliComputeView extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-compute-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._stacksPane = this.$('.stacks-pane')
        if (this._pendingStacks) { this._stacksPane?.setStacks?.(this._pendingStacks); this._pendingStacks = null }
    }

    setData({ stacks = [] } = {}) {
        if (!this._stacksPane) { this._pendingStacks = stacks; return }
        this._stacksPane.setStacks?.(stacks)
    }
}

customElements.define('sp-cli-compute-view', SpCliComputeView)
