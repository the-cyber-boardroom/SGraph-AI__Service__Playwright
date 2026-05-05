import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeSpecDetail extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-spec-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._iconEl           = this.$('.sd-icon')
        this._nameEl           = this.$('.sd-name')
        this._specIdEl         = this.$('.sd-spec-id')
        this._stabilityEl      = this.$('.sd-stability-badge')
        this._navGroupEl       = this.$('.sd-nav-group')
        this._versionEl        = this.$('.sd-field-version')
        this._bootEl           = this.$('.sd-field-boot')
        this._navEl            = this.$('.sd-field-nav')
        this._capsEl           = this.$('.sd-field-caps')
        this._endpointEl       = this.$('.sd-field-endpoint')
        this._extendsPlaceholder = this.$('.sd-extends-placeholder')
        this._extendsList      = this.$('.sd-extends-list')
        this._readmeLink       = this.$('.sd-readme-link')
        this._readmePlaceholder = this.$('.sd-readme-placeholder')
        this._btnHeaderLaunch  = this.$('.btn-launch-header')
        this._btnFooterLaunch  = this.$('.btn-launch-footer')

        this._btnHeaderLaunch?.addEventListener('click', () => this._launch())
        this._btnFooterLaunch?.addEventListener('click', () => this._launch())

        if (this._pendingSpec) { this.open(this._pendingSpec); this._pendingSpec = null }
    }

    open(spec) {
        if (!this._nameEl) { this._pendingSpec = spec; return }
        this._spec = spec
        this._render(spec)
    }

    _render(spec) {
        const esc = _esc

        if (this._iconEl)     this._iconEl.textContent     = spec.icon || '⬡'
        if (this._nameEl)     this._nameEl.textContent     = spec.display_name || spec.spec_id
        if (this._specIdEl)   this._specIdEl.textContent   = spec.spec_id

        if (this._stabilityEl) {
            const s = spec.stability || 'experimental'
            this._stabilityEl.textContent = s
            this._stabilityEl.className   = `sd-stability-badge ${s}`
        }
        if (this._navGroupEl) this._navGroupEl.textContent = spec.nav_group || ''

        if (this._versionEl)  this._versionEl.textContent  = spec.version ? `v${esc(spec.version)}` : '—'
        if (this._bootEl)     this._bootEl.textContent      = _fmtBoot(spec.boot_seconds_typical)
        if (this._navEl)      this._navEl.textContent       = spec.nav_group || '—'

        if (this._capsEl) {
            const caps = spec.capabilities || []
            this._capsEl.innerHTML = caps.length
                ? caps.map(c => `<span class="cap-chip">${esc(c)}</span>`).join('')
                : '<span style="color:var(--sg-text-muted);font-style:italic">none</span>'
        }

        if (this._endpointEl) {
            this._endpointEl.innerHTML = spec.create_endpoint_path
                ? `<span class="sd-endpoint">${esc(spec.create_endpoint_path)}</span>`
                : '<span style="color:var(--sg-text-muted);font-style:italic">—</span>'
        }

        const extendsArr = spec.extends || []
        if (this._extendsPlaceholder) this._extendsPlaceholder.hidden = extendsArr.length > 0
        if (this._extendsList) {
            this._extendsList.hidden = extendsArr.length === 0
            this._extendsList.innerHTML = extendsArr.map(id =>
                `<code style="font-family:monospace;font-size:0.85em;background:var(--sg-bg-alt);border:1px solid var(--sg-border);border-radius:3px;padding:1px 6px">${esc(id)}</code>`
            ).join(' → ')
        }

        if (this._readmeLink && this._readmePlaceholder) {
            const href = spec.spec_id ? `/api/specs/${encodeURIComponent(spec.spec_id)}/readme` : ''
            if (href) {
                this._readmeLink.href        = href
                this._readmeLink.textContent = `View README for ${esc(spec.display_name || spec.spec_id)}`
                this._readmeLink.hidden      = false
                this._readmePlaceholder.hidden = true
            } else {
                this._readmeLink.hidden      = true
                this._readmePlaceholder.hidden = false
            }
        }
    }

    _launch() {
        if (!this._spec) return
        document.dispatchEvent(new CustomEvent('sp-cli:catalog-launch', {
            detail:  { entry: { ...this._spec } },
            bubbles: true, composed: true,
        }))
    }
}

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function _fmtBoot(secs) {
    if (!secs) return '—'
    if (secs < 120) return `~${secs}s`
    return `~${Math.round(secs / 60)} min`
}

customElements.define('sg-compute-spec-detail', SgComputeSpecDetail)
