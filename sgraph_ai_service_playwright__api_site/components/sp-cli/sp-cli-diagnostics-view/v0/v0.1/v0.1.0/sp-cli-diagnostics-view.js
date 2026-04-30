/**
 * sp-cli-diagnostics-view — Diagnostics view placeholder.
 *
 * Real-time API status, error log, and system health coming in a follow-up brief.
 *
 * @module sp-cli-diagnostics-view
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliDiagnosticsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-diagnostics-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        const apiUrl = localStorage.getItem('sg_api_url') || window.location.origin
        const el = this.$('.api-url')
        if (el) el.textContent = apiUrl
    }
}

customElements.define('sp-cli-diagnostics-view', SpCliDiagnosticsView)
