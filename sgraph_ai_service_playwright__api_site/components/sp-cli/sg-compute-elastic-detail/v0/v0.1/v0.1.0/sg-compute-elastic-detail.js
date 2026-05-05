import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '../../../../../../shared/api-client.js'
import { isRunning   } from '../../../../../../shared/node-state.js'
import '../../../../_shared/sg-compute-stack-header/v0/v0.1/v0.1.0/sg-compute-stack-header.js'
import '../../../../_shared/sg-compute-ssm-command/v0/v0.1/v0.1.0/sg-compute-ssm-command.js'
import '../../../../_shared/sg-compute-network-info/v0/v0.1/v0.1.0/sg-compute-network-info.js'
import '../../../../_shared/sg-compute-stop-button/v0/v0.1/v0.1.0/sg-compute-stop-button.js'
import '../../../../_shared/sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js'
import '../../../../_shared/sg-compute-host-shell/v0/v0.1/v0.1.0/sg-compute-host-shell.js'
import '../../../../_shared/sg-compute-host-api-panel/v0/v0.1/v0.1.0/sg-compute-host-api-panel.js'

class SgComputeElasticDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-elastic-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._header         = this.$('.detail-header')
        this._ssm            = this.$('.detail-ssm')
        this._net            = this.$('.detail-net')
        this._stop           = this.$('.detail-stop')
        this._browserSection = this.$('.browser-section')
        this._browser        = this.$('.remote-browser')
        this._serviceUrls    = this.$('.service-urls')
        this._kibanaUrl      = this.$('.kibana-url')
        this._esUrl          = this.$('.es-url')
        this._shell          = this.$('.host-shell')
        this._hostApi        = this.$('.host-api-panel')
        this._tabs           = Array.from(this.shadowRoot.querySelectorAll('.tab-btn'))
        this._panels         = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))
        this._tabs.forEach(btn => btn.addEventListener('click', () => this._activateTab(btn.dataset.tab)))
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
        this._shell  ?.open?.(stack)
        this._hostApi?.open?.(stack)
        this._fetchDetail(stack)
    }

    async _fetchDetail(stack) {
        try {
            const info = await apiClient.get(`/elastic/stack/${stack.node_id}`)
            if (!this._stack || this._stack.node_id !== stack.node_id) return
            const merged = { ...stack, ...info }
            this._header.setStack?.(merged)
            this._ssm.setStack?.(merged)
            this._net.setStack?.(merged)
            const ip = merged.public_ip
            if (ip && isRunning(merged.state)) {
                this._setServiceUrls(ip)
                if (this._browser) this._browser.setAttribute('src', `https://${ip}:5601`)
                if (this._browserSection) this._browserSection.hidden = false
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

    _activateTab(name) {
        this._tabs  .forEach(b => b.classList.toggle('active', b.dataset.tab   === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
    }
}

customElements.define('sg-compute-elastic-detail', SgComputeElasticDetail)
