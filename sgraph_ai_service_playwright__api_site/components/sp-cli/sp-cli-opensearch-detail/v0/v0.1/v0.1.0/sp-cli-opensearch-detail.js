import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '../../../../../../shared/api-client.js'
import { isRunning   } from '../../../../../../shared/node-state.js'
import '../../../../_shared/sp-cli-stack-header/v0/v0.1/v0.1.0/sp-cli-stack-header.js'
import '../../../../_shared/sp-cli-ssm-command/v0/v0.1/v0.1.0/sp-cli-ssm-command.js'
import '../../../../_shared/sp-cli-network-info/v0/v0.1/v0.1.0/sp-cli-network-info.js'
import '../../../../_shared/sp-cli-stop-button/v0/v0.1/v0.1.0/sp-cli-stop-button.js'
import '../../../../_shared/sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js'

class SpCliOpensearchDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-opensearch-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._header         = this.$('.detail-header')
        this._ssm            = this.$('.detail-ssm')
        this._net            = this.$('.detail-net')
        this._stop           = this.$('.detail-stop')
        this._browserSection = this.$('.browser-section')
        this._browser        = this.$('.remote-browser')
        this._serviceUrls    = this.$('.service-urls')
        this._dashboardsUrl  = this.$('.dashboards-url')
        this._osUrl          = this.$('.os-url')
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
            const info = await apiClient.get(`/opensearch/stack/${stack.stack_name}`)
            if (!this._stack || this._stack.stack_name !== stack.stack_name) return
            const merged = { ...stack, ...info }
            this._header.setStack?.(merged)
            this._ssm.setStack?.(merged)
            this._net.setStack?.(merged)
            const ip = merged.public_ip
            if (ip && isRunning(merged.state)) {
                const dashboards = `https://${ip}:5601`
                const os         = `https://${ip}:9200`
                if (this._dashboardsUrl) { this._dashboardsUrl.href = dashboards; this._dashboardsUrl.textContent = dashboards }
                if (this._osUrl)         { this._osUrl.href = os;                 this._osUrl.textContent = os }
                if (this._serviceUrls) this._serviceUrls.hidden = false
                if (this._browser) this._browser.setAttribute('src', dashboards)
                if (this._browserSection) this._browserSection.hidden = false
            }
        } catch (_) {}
    }
}

customElements.define('sp-cli-opensearch-detail', SpCliOpensearchDetail)
