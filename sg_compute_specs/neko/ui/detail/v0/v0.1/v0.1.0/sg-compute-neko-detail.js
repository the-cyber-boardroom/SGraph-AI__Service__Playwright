import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '/ui/components/sp-cli/_shared/sg-compute-stack-header/v0/v0.1/v0.1.0/sg-compute-stack-header.js'
import '/ui/components/sp-cli/_shared/sg-compute-stop-button/v0/v0.1/v0.1.0/sg-compute-stop-button.js'
import '/ui/components/sp-cli/_shared/sg-compute-host-shell/v0/v0.1/v0.1.0/sg-compute-host-shell.js'
import '/ui/components/sp-cli/_shared/sg-compute-host-api-panel/v0/v0.1/v0.1.0/sg-compute-host-api-panel.js'

class SgComputeNekoDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-neko-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._header  = this.$('.detail-header')
        this._stop    = this.$('.detail-stop')
        this._shell   = this.$('.host-shell')
        this._hostApi = this.$('.host-api-panel')
        this._tabs    = Array.from(this.shadowRoot.querySelectorAll('.tab-btn'))
        this._panels  = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))
        this._tabs.forEach(btn => btn.addEventListener('click', () => this._activateTab(btn.dataset.tab)))
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._header) { this._pendingStack = stack; return }
        this._stack = stack
        this._header.setStack?.(stack)
        this._stop.setStack?.(stack)
        this._shell  ?.open?.(stack)
        this._hostApi?.open?.(stack)
    }

    _activateTab(name) {
        this._tabs  .forEach(b => b.classList.toggle('active', b.dataset.tab   === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
    }
}

customElements.define('sg-compute-neko-detail', SgComputeNekoDetail)
