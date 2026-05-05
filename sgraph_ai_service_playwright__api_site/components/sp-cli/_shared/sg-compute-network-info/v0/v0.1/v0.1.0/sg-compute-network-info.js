import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeNetworkInfo extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-network-info' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._ipEl    = this.$('.net-ip')
        this._allowEl = this.$('.net-allow')
        this._sgEl    = this.$('.net-sg')
        if (this._pendingStack) { this.setStack(this._pendingStack); this._pendingStack = null }
    }

    setStack(stack) {
        if (!this._ipEl) { this._pendingStack = stack; return }
        this._ipEl.textContent    = stack?.public_ip      || '—'
        this._allowEl.textContent = stack?.allowed_ip     || '—'
        this._sgEl.textContent    = stack?.security_group || stack?.sg_id || '—'
    }
}

customElements.define('sg-compute-network-info', SgComputeNetworkInfo)
