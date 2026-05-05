import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '../../../../../../shared/api-client.js'
import '../../../../_shared/sp-cli-stack-header/v0/v0.1/v0.1.0/sp-cli-stack-header.js'
import '../../../../_shared/sp-cli-ssm-command/v0/v0.1/v0.1.0/sp-cli-ssm-command.js'
import '../../../../_shared/sp-cli-network-info/v0/v0.1/v0.1.0/sp-cli-network-info.js'
import '../../../../_shared/sp-cli-stop-button/v0/v0.1/v0.1.0/sp-cli-stop-button.js'

class SpCliPodmanDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-podman-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._header = this.$('.detail-header')
        this._ssm    = this.$('.detail-ssm')
        this._net    = this.$('.detail-net')
        this._stop   = this.$('.detail-stop')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._header) { this._pendingStack = stack; return }
        this._stack = stack
        this._header.setStack?.(stack)
        this._ssm.setStack?.(stack)
        this._net.setStack?.(stack)
        this._stop.setStack?.(stack)
        this._fetchDetail(stack)
    }

    async _fetchDetail(stack) {
        try {
            const info = await apiClient.get(`/podman/stack/${stack.node_id}`)
            if (!this._stack || this._stack.node_id !== stack.node_id) return
            const merged = { ...stack, ...info }
            this._header.setStack?.(merged)
            this._ssm.setStack?.(merged)
            this._net.setStack?.(merged)
        } catch (_) {}
    }
}

customElements.define('sp-cli-podman-detail', SpCliPodmanDetail)
