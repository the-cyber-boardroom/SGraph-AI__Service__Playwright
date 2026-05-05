import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { getCatalogue, loadCatalogue } from '../../../../../../shared/spec-catalogue.js'

class SpCliSpecsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-specs-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._grid    = this.$('.sv-grid')
        this._empty   = this.$('.sv-empty')
        this._count   = this.$('.sv-count')

        document.addEventListener('sp-cli:catalogue.loaded', () => this._render())
        loadCatalogue().then(() => this._render()).catch(() => {})
    }

    _render() {
        if (!this._grid) return
        let specs
        try { specs = getCatalogue().specs || [] } catch (_) { return }

        this._grid.innerHTML = ''
        this._empty.hidden   = specs.length > 0
        this._grid.hidden    = specs.length === 0

        if (this._count) {
            this._count.textContent = specs.length ? `(${specs.length})` : ''
        }

        for (const spec of specs) {
            this._grid.appendChild(this._buildCard(spec))
        }
    }

    _buildCard(spec) {
        const card = document.createElement('article')
        card.className = 'spec-card'
        card.setAttribute('role', 'listitem')

        const stabClass = _stabClass(spec.stability)
        const bootLabel = _fmtBoot(spec.boot_seconds_typical)
        const capChips  = (spec.capabilities || [])
            .map(c => `<span class="cap-chip">${_esc(c)}</span>`).join('')

        card.innerHTML = `
            <div class="sc-top">
                <div class="sc-icon" aria-hidden="true">${_esc(spec.icon || '⬡')}</div>
                <div class="sc-identity">
                    <div class="sc-name">${_esc(spec.display_name)}</div>
                    <div class="sc-id">${_esc(spec.spec_id)}</div>
                </div>
            </div>
            <div class="sc-meta">
                <span class="badge ${stabClass}" aria-label="Stability: ${_esc(spec.stability || 'unknown')}">${_esc(spec.stability || '—')}</span>
                ${spec.soon ? '<span class="badge badge-soon">soon</span>' : ''}
                <span class="sc-boot" aria-label="Boot time: ${bootLabel}">${bootLabel}</span>
            </div>
            ${capChips ? `<div class="sc-caps" aria-label="Capabilities">${capChips}</div>` : ''}
            ${spec.version ? `<div class="sc-version">v${_esc(spec.version)}</div>` : ''}
            <div class="sc-actions">
                <button class="btn-launch" ${spec.soon ? 'disabled aria-disabled="true"' : ''} aria-label="Launch a node using spec ${_esc(spec.spec_id)}">Launch node</button>
            </div>
        `

        if (!spec.soon) {
            card.querySelector('.btn-launch').addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('sp-cli:catalog-launch', {
                    detail:  { entry: { ...spec } },
                    bubbles: true, composed: true,
                }))
            })
        }

        return card
    }
}

function _stabClass(s) {
    if (s === 'stable')       return 'badge-stable'
    if (s === 'deprecated')   return 'badge-deprecated'
    return 'badge-experimental'
}

function _fmtBoot(secs) {
    if (!secs) return '—'
    if (secs < 120) return `~${secs}s`
    return `~${Math.round(secs / 60)}min`
}

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

customElements.define('sp-cli-specs-view', SpCliSpecsView)
