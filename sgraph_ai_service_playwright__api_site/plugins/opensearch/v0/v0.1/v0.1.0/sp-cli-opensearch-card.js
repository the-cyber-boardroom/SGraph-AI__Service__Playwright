import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const STATIC = { type_id: 'opensearch', display_name: 'OpenSearch + Dashboards', icon: '🌐', stability: 'experimental', boot: '—', soon: false, create_endpoint_path: '/opensearch/stack' }

class SpCliOpensearchCard extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-opensearch-card' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() { this._entry = STATIC; this._render(); this.$('.btn-launch')?.addEventListener('click', () => this._launch()) }
    setEntry(entry) { this._entry = { ...STATIC, ...entry }; this._render() }

    _render() {
        const e = this._entry
        if (this.$('.card-icon'))  this.$('.card-icon').textContent  = e.icon
        if (this.$('.card-name'))  this.$('.card-name').textContent  = e.display_name
        if (this.$('.card-boot'))  this.$('.card-boot').textContent  = e.boot
        const stab = this.$('.badge-stability')
        if (stab)  { stab.hidden = e.stability === 'stable'; stab.textContent = e.stability }
        if (this.$('.badge-soon')) this.$('.badge-soon').hidden = !e.soon
        const btn = this.$('.btn-launch')
        if (btn)   { btn.disabled = !!e.soon; btn.textContent = e.soon ? 'Coming soon' : 'Launch →' }
    }

    _launch() {
        document.dispatchEvent(new CustomEvent('sp-cli:plugin:opensearch.launch-requested', { detail: { entry: this._entry }, bubbles: true, composed: true }))
    }
}
customElements.define('sp-cli-opensearch-card', SpCliOpensearchCard)
