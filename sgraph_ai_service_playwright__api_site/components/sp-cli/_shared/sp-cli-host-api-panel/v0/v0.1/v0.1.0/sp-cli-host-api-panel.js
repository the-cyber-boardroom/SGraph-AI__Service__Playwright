import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href

class SpCliHostApiPanel extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-api-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._frame       = this.$('.api-frame')
        this._unavailable = this.$('.unavailable')
        this._status      = this.$('.api-status')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._frame) { this._pendingStack = stack; return }
        const url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
        const key = stack.host_api_key || ''

        if (!url) {
            this._unavailable?.classList.remove('hidden')
            this._frame.classList.add('hidden')
            this._frame.src = ''
            if (this._status) this._status.textContent = ''
            return
        }

        this._unavailable?.classList.add('hidden')
        this._frame.classList.remove('hidden')

        // Use /docs-auth?apikey= if available (sidecar v0.38+) so the key is
        // pre-injected and every Execute call is authenticated transparently.
        // Falls back to /docs if the endpoint is not yet deployed.
        const docsUrl = key
            ? `${url}/docs-auth?apikey=${encodeURIComponent(key)}`
            : `${url}/docs`

        this._frame.src = docsUrl

        if (this._status) {
            this._status.textContent = key ? '🔑 Authenticated' : '⚠ No API key — calls will return 403'
        }
    }
}

customElements.define('sp-cli-host-api-panel', SpCliHostApiPanel)
