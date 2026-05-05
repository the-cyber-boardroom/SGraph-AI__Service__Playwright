import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeApiView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-api-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._frame = this.$('.docs-frame')
        if (this._frame) this._frame.src = `${window.location.origin}/docs`
    }
}

customElements.define('sg-compute-api-view', SgComputeApiView)
