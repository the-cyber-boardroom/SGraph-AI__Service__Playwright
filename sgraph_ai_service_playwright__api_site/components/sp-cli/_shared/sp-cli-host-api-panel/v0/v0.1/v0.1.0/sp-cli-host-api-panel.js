import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliHostApiPanel extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-api-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._frame       = this.$('.api-frame')
        this._unavailable = this.$('.unavailable')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._frame) { this._pendingStack = stack; return }
        const url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
        if (!url) {
            this._unavailable?.classList.remove('hidden')
            this._frame.classList.add('hidden')
            this._frame.src = ''
        } else {
            this._unavailable?.classList.add('hidden')
            this._frame.classList.remove('hidden')
            this._frame.src = `${url}/docs`
        }
    }
}

customElements.define('sp-cli-host-api-panel', SpCliHostApiPanel)
