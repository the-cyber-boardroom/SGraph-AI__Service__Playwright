import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '../../../../../../shared/api-client.js'
import '../../../../_shared/sp-cli-stack-header/v0/v0.1/v0.1.0/sp-cli-stack-header.js'
import '../../../../_shared/sp-cli-ssm-command/v0/v0.1/v0.1.0/sp-cli-ssm-command.js'
import '../../../../_shared/sp-cli-network-info/v0/v0.1/v0.1.0/sp-cli-network-info.js'
import '../../../../_shared/sp-cli-stop-button/v0/v0.1/v0.1.0/sp-cli-stop-button.js'

class SpCliElasticDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-elastic-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._header      = this.$('.detail-header')
        this._ssm         = this.$('.detail-ssm')
        this._net         = this.$('.detail-net')
        this._stop        = this.$('.detail-stop')
        this._serviceUrls = this.$('.service-urls')
        this._kibanaUrl   = this.$('.kibana-url')
        this._esUrl       = this.$('.es-url')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._header) { this._pendingStack = stack; return }
        this._stack = stack
        if (this._serviceUrls) this._serviceUrls.hidden = true
        this._header.setStack?.(stack)
        this._ssm.setStack?.(stack)
        this._net.setStack?.(stack)
        this._stop.setStack?.(stack)
        this._fetchDetail(stack)
    }

    async _fetchDetail(stack) {
        try {
            const info = await apiClient.get(`/elastic/stack/${stack.stack_name}`)
            if (!this._stack || this._stack.stack_name !== stack.stack_name) return
            const merged = { ...stack, ...info }
            this._header.setStack?.(merged)
            this._ssm.setStack?.(merged)
            this._net.setStack?.(merged)
            const ip = merged.public_ip
            if (ip && (merged.state || '').toLowerCase() === 'running') {
                this._setServiceUrls(ip)
            }
        } catch (_) {}
    }

    _setServiceUrls(ip) {
        const kibana = `https://${ip}:5601`
        const es     = `https://${ip}:9200`
        if (this._kibanaUrl) { this._kibanaUrl.href = kibana; this._kibanaUrl.textContent = kibana }
        if (this._esUrl)     { this._esUrl.href = es;         this._esUrl.textContent = es }
        if (this._serviceUrls) this._serviceUrls.hidden = false
    }
}

customElements.define('sp-cli-elastic-detail', SpCliElasticDetail)
