import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const STATIC = { spec_id: 'podman', type_id: 'podman', display_name: 'Podman host', icon: '🦭', stability: 'stable', boot: '~10min', soon: false, create_endpoint_path: '/podman/stack' }

class SpCliPodmanCard extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-podman-card' }
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
        const detail = { entry: this._entry }
        document.dispatchEvent(new CustomEvent('sp-cli:spec:podman.launch-requested',   { detail, bubbles: true, composed: true }))
        document.dispatchEvent(new CustomEvent('sp-cli:plugin:podman.launch-requested', { detail, bubbles: true, composed: true })) // DEPRECATED
    }
}
customElements.define('sp-cli-podman-card', SpCliPodmanCard)
