import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliNetworkInfo extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-network-info' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._ipEl    = this.$('.net-ip')
        this._allowEl = this.$('.net-allow')
        this._sgEl    = this.$('.net-sg')
    }

    setStack(stack) {
        if (this._ipEl)    this._ipEl.textContent    = stack?.public_ip      || '—'
        if (this._allowEl) this._allowEl.textContent = stack?.allowed_ip     || '—'
        if (this._sgEl)    this._sgEl.textContent    = stack?.security_group || stack?.sg_id || '—'
    }
}

customElements.define('sp-cli-network-info', SpCliNetworkInfo)
