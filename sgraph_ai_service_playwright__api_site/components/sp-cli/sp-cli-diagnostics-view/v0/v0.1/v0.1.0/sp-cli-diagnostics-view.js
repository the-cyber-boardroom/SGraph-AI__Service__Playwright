import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const DIAG_LAYOUT = {
    type: 'column',
    sizes: [0.25, 0.19, 0.19, 0.19, 0.18],
    children: [
        { type: 'stack', tabs: [{ tag: 'sp-cli-events-log',       title: 'Events Log',      locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-vault-status',     title: 'Vault Status',    locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-active-sessions',  title: 'Active Sessions', locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-cost-tracker',     title: 'Cost Tracker',    locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-storage-viewer',   title: 'Storage',         locked: true }] },
    ],
}

class SpCliDiagnosticsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-diagnostics-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    async onReady() {
        await import('https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js')
        const layout = this.$('#diag-layout')
        layout?.setLayout(DIAG_LAYOUT)
    }
}

customElements.define('sp-cli-diagnostics-view', SpCliDiagnosticsView)
