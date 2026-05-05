import { SgComponent    } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { getDefault     } from '../../../../../../shared/settings-bus.js'
import { loadCatalogue, getCatalogue } from '../../../../../../shared/spec-catalogue.js'

const _EC2_CSS = new URL('../../../../../../shared/ec2-tokens.css', import.meta.url).href

function _fmtBoot(secs) {
    if (!secs) return '—'
    if (secs < 120) return `~${secs}s`
    return `~${Math.round(secs / 60)}min`
}

const REGIONS        = ['eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2']
const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge']
const MAX_HOURS      = [1, 2, 4, 8, 12, 24]

const NAME_WORDS = [
    'nova', 'echo', 'lark', 'ford', 'pike', 'wren', 'dusk', 'reef', 'sage', 'fern',
    'kite', 'vale', 'bolt', 'cove', 'dune', 'flux', 'glen', 'haze', 'isle', 'jade',
]

function _genName(typeId) {
    const word = NAME_WORDS[Math.floor(Math.random() * NAME_WORDS.length)]
    const num  = String(Math.floor(Math.random() * 9000) + 1000)
    return `${typeId}-${word}-${num}`
}

// Rough on-demand spot rates (USD/hr) for cost hint — intentionally approximate
const COST_TABLE = {
    't3.micro': 0.011, 't3.small': 0.023, 't3.medium': 0.047,
    't3.large': 0.094, 't3.xlarge': 0.188,
}

class SpCliComputeView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-compute-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._specGroups  = this.$('.spec-groups')
        this._cfgCol      = this.$('.configure-col')
        this._cfgIcon     = this.$('.cfg-icon')
        this._cfgName     = this.$('.cfg-name')
        this._cfgDesc     = this.$('.cfg-desc')
        this._cfgStab     = this.$('.cfg-stability')
        this._cfgBoot     = this.$('.cfg-boot-val')
        this._regionSel   = this.$('.field-region')
        this._instanceSel = this.$('.field-instance')
        this._hoursSel    = this.$('.field-hours')
        this._nameInput   = this.$('.field-name')
        this._openCheck   = this.$('.field-open')
        this._btnLaunch   = this.$('.btn-launch')
        this._btnLabel    = this.$('.btn-label')
        this._btnSpinner  = this.$('.btn-spinner')
        this._errorMsg    = this.$('.error-msg')
        this._barBoot     = this.$('.cfg-bar-boot')
        this._barHourly   = this.$('.cfg-bar-hourly')
        this._barMax      = this.$('.cfg-bar-max')
        this._barNet      = this.$('.cfg-bar-net')

        this._populateSelect(this._regionSel,   REGIONS,        r => r)
        this._populateSelect(this._instanceSel, INSTANCE_TYPES, t => t)
        this._populateSelect(this._hoursSel,    MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)

        this._regionSel?.addEventListener('change',   () => this._updateCostBar())
        this._instanceSel?.addEventListener('change', () => this._updateCostBar())
        this._hoursSel?.addEventListener('change',    () => this._updateCostBar())
        this._openCheck?.addEventListener('change',   () => this._updateCostBar())

        this.$('.btn-close-cfg')?.addEventListener('click', () => this._closeCfg())
        this._btnLaunch?.addEventListener('click', () => this._launch())

        document.addEventListener('sp-cli:settings.loaded', () => this._applyDefaults())
        document.addEventListener('sp-cli:catalogue.loaded', () => this._renderGroups())
        this._applyDefaults()
        loadCatalogue().then(() => this._renderGroups()).catch(() => {})
    }

    // Called by admin.js — no-op in new design (stacks live in nodes-view)
    setData(_) {}

    _applyDefaults() {
        const region   = getDefault('region')        || 'eu-west-2'
        const instance = getDefault('instance_type') || 't3.medium'
        const hours    = getDefault('max_hours')     || 1
        if (this._regionSel)   this._regionSel.value   = region
        if (this._instanceSel) this._instanceSel.value = instance
        if (this._hoursSel)    this._hoursSel.value     = String(hours)
        this._updateCostBar()
    }

    _renderGroups() {
        if (!this._specGroups) return
        let specs
        try { specs = getCatalogue().specs || [] } catch (_) { return }
        const groups = [...new Set(specs.map(s => s.nav_group || 'OTHER'))]
        this._specGroups.innerHTML = ''

        for (const group of groups) {
            const groupSpecs = specs.filter(s => (s.nav_group || 'OTHER') === group)
            if (!groupSpecs.length) continue

            const section = document.createElement('div')
            section.className = 'spec-section'
            section.innerHTML = `<div class="spec-group-label tlabel">${group}</div><div class="spec-card-row"></div>`
            const row = section.querySelector('.spec-card-row')

            for (const spec of groupSpecs) {
                const card = document.createElement('div')
                card.className = `spec-card${spec.soon ? ' spec-card--soon' : ''}`
                card.dataset.specId = spec.spec_id
                card.setAttribute('role', 'button')
                card.setAttribute('tabindex', spec.soon ? '-1' : '0')
                card.setAttribute('aria-label', spec.soon ? `${spec.display_name} — coming soon` : `Select ${spec.display_name}`)
                if (spec.soon) card.setAttribute('aria-disabled', 'true')
                const bootLabel = _fmtBoot(spec.boot_seconds_typical)
                card.innerHTML = `
                    <div class="sc-icon" aria-hidden="true">${spec.icon || '⬡'}</div>
                    <div class="sc-body">
                        <div class="sc-name">${spec.display_name}</div>
                        <div class="sc-meta">
                            ${spec.stability !== 'stable' ? `<span class="ec2-pill warn">${spec.stability}</span>` : '<span class="ec2-pill good">stable</span>'}
                            ${spec.soon ? '<span class="ec2-pill">soon</span>' : ''}
                            <span class="sc-boot">${bootLabel}</span>
                        </div>
                    </div>
                `
                if (!spec.soon) {
                    card.addEventListener('click', () => this._selectSpec(spec, card))
                    card.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._selectSpec(spec, card) }
                    })
                }
                row.appendChild(card)
            }
            this._specGroups.appendChild(section)
        }
    }

    _selectSpec(spec, cardEl) {
        Array.from(this.shadowRoot.querySelectorAll('.spec-card')).forEach(c => {
            const sel = c === cardEl
            c.classList.toggle('selected', sel)
            c.setAttribute('aria-pressed', String(sel))
        })
        this._currentSpec = spec
        const bootLabel = _fmtBoot(spec.boot_seconds_typical)
        if (this._cfgIcon) this._cfgIcon.textContent = spec.icon || '⬡'
        if (this._cfgName) this._cfgName.textContent = spec.display_name
        if (this._cfgDesc) this._cfgDesc.textContent = spec.capabilities?.join(', ') || ''
        if (this._cfgStab) {
            this._cfgStab.className = `cfg-stability ec2-pill ${spec.stability === 'stable' ? 'good' : 'warn'}`
            this._cfgStab.textContent = spec.stability
        }
        if (this._cfgBoot) this._cfgBoot.textContent = bootLabel
        if (this._barBoot) this._barBoot.textContent = bootLabel
        this._clearError()
        if (this._nameInput) this._nameInput.value = _genName(spec.spec_id)
        this._updateCostBar()
        this._cfgCol.hidden = false
        this.shadowRoot.querySelector('.compute-view')?.classList.add('spec-selected')
    }

    _closeCfg() {
        this._cfgCol.hidden = true
        this._currentSpec = null
        this.shadowRoot.querySelector('.compute-view')?.classList.remove('spec-selected')
        Array.from(this.shadowRoot.querySelectorAll('.spec-card')).forEach(c => c.classList.remove('selected'))
    }

    _updateCostBar() {
        const inst  = this._instanceSel?.value || 't3.medium'
        const hours = parseInt(this._hoursSel?.value || '4', 10)
        const rate  = COST_TABLE[inst] || 0
        const open  = this._openCheck?.checked ?? false
        if (this._barHourly) this._barHourly.textContent = rate ? `$${rate.toFixed(3)}` : '—'
        if (this._barMax)    this._barMax.textContent    = rate ? `$${(rate * hours).toFixed(2)}` : '—'
        if (this._barNet)    this._barNet.textContent    = open ? 'Open (0.0.0.0/0)' : 'Your IP only'
    }

    async _launch() {
        if (!this._currentSpec) return
        this._setLoading(true)
        this._clearError()
        const body = {
            stack_name:    this._nameInput?.value.trim()  || _genName(this._currentSpec.spec_id),
            region:        this._regionSel?.value         || REGIONS[0],
            instance_type: this._instanceSel?.value       || 't3.medium',
            max_hours:     parseInt(this._hoursSel?.value || '4', 10),
            public_ingress: this._openCheck?.checked ?? false,
        }
        try {
            const { apiClient } = await import('../../../../../../shared/api-client.js')
            const resp = await apiClient.post(this._currentSpec.create_endpoint_path, body)
            document.dispatchEvent(new CustomEvent('sp-cli:node.launched', {
                detail:  { entry: this._currentSpec, response: resp },
                bubbles: true, composed: true,
            }))
            document.dispatchEvent(new CustomEvent('sp-cli:launch.success', {   // DEPRECATED
                detail:  { entry: this._currentSpec, response: resp },
                bubbles: true, composed: true,
            }))
            this._closeCfg()
        } catch (err) {
            this._showError(err.message || 'Launch failed')
        } finally {
            this._setLoading(false)
        }
    }

    _setLoading(on) {
        if (this._btnLaunch)  this._btnLaunch.disabled  = on
        if (this._btnLabel)   this._btnLabel.hidden      = on
        if (this._btnSpinner) this._btnSpinner.hidden    = !on
    }

    _showError(msg) {
        if (!this._errorMsg) return
        this._errorMsg.textContent = msg
        this._errorMsg.hidden      = false
    }

    _clearError() {
        if (this._errorMsg) { this._errorMsg.textContent = ''; this._errorMsg.hidden = true }
    }

    _populateSelect(sel, items, labelFn) {
        if (!sel) return
        sel.innerHTML = ''
        for (const item of items) {
            const opt = document.createElement('option')
            opt.value = String(item)
            opt.textContent = labelFn(item)
            sel.appendChild(opt)
        }
    }
}

customElements.define('sp-cli-compute-view', SpCliComputeView)
