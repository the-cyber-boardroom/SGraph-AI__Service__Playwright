import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '../../sp-cli-events-log/v0/v0.1/v0.1.0/sp-cli-events-log.js'

class SpCliDiagnosticsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-diagnostics-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        const apiUrlEl = this.$('.api-url')
        if (apiUrlEl) apiUrlEl.textContent = localStorage.getItem('sg_api_url') || window.location.origin

        this.shadowRoot.querySelectorAll('.diag-tab').forEach(btn =>
            btn.addEventListener('click', () => this._switchTab(btn.dataset.tab))
        )
    }

    _switchTab(name) {
        this.shadowRoot.querySelectorAll('.diag-tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === name)
        )
        this.shadowRoot.querySelectorAll('.diag-panel').forEach(p =>
            p.hidden = p.dataset.panel !== name
        )
    }
}

customElements.define('sp-cli-diagnostics-view', SpCliDiagnosticsView)
