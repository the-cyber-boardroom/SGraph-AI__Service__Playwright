import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { getDefault } from '../../../../../../shared/settings-bus.js'

// ── Spec catalogue (static until backend phase B4 ships /api/specs) ─────────
const CATALOG = [
    { group: 'CONTAINERS',      type_id: 'docker',     display_name: 'Docker host',             icon: '🐳', stability: 'stable',       boot: '~10min', soon: false, create_endpoint_path: '/docker/stack',     description: 'Docker Engine host on a fresh EC2 instance.'                           },
    { group: 'CONTAINERS',      type_id: 'podman',     display_name: 'Podman host',             icon: '🦭', stability: 'stable',       boot: '~10min', soon: false, create_endpoint_path: '/podman/stack',     description: 'Rootless Podman host on a fresh EC2 instance.'                         },
    { group: 'OBSERVABILITY',   type_id: 'elastic',    display_name: 'Elastic + Kibana',        icon: '🔍', stability: 'stable',       boot: '~90s',   soon: false, create_endpoint_path: '/elastic/stack',    description: 'Elasticsearch + Kibana node. Indices persist on attached gp3 storage.' },
    { group: 'OBSERVABILITY',   type_id: 'prometheus', display_name: 'Prometheus + Grafana',    icon: '📊', stability: 'experimental', boot: '~90s',   soon: false, create_endpoint_path: '/prometheus/stack', description: 'Prometheus scraper + Grafana dashboard node.'                          },
    { group: 'OBSERVABILITY',   type_id: 'opensearch', display_name: 'OpenSearch + Dashboards', icon: '🌐', stability: 'experimental', boot: '—',      soon: false, create_endpoint_path: '/opensearch/stack', description: 'OpenSearch cluster with Dashboards UI.'                                },
    { group: 'REMOTE BROWSERS', type_id: 'firefox',    display_name: 'Firefox + MITM',          icon: '🦊', stability: 'experimental', boot: '~90s',   soon: false, create_endpoint_path: '/firefox/stack',    description: 'Firefox with MITM proxy for traffic inspection via browser.'           },
    { group: 'REMOTE BROWSERS', type_id: 'vnc',        display_name: 'VNC bastion',             icon: '🖥',  stability: 'stable',       boot: '~90s',   soon: false, create_endpoint_path: '/vnc/stack',        description: 'VNC-accessible desktop bastion with noVNC web client.'                 },
    { group: 'REMOTE BROWSERS', type_id: 'neko',       display_name: 'Neko (WebRTC)',           icon: '🌐', stability: 'experimental', boot: '—',      soon: true,  create_endpoint_path: '/neko/stack',        description: 'Browser-in-browser via WebRTC.'                                        },
]

const REGIONS        = ['eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2']
const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge']
const MAX_HOURS      = [1, 2, 4, 8, 12, 24]

// Rough on-demand spot rates (USD/hr) for cost hint — intentionally approximate
const COST_TABLE = {
    't3.micro': 0.011, 't3.small': 0.023, 't3.medium': 0.047,
    't3.large': 0.094, 't3.xlarge': 0.188,
}

class SpCliComputeView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-compute-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

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

        this._populateSelect(this._regionSel,   REGIONS,        r => r)
        this._populateSelect(this._instanceSel, INSTANCE_TYPES, t => t)
        this._populateSelect(this._hoursSel,    MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)

        this._regionSel?.addEventListener('change',   () => this._updateCost())
        this._instanceSel?.addEventListener('change', () => this._updateCost())
        this._hoursSel?.addEventListener('change',    () => this._updateCost())

        this.$('.btn-close-cfg')?.addEventListener('click', () => this._closeCfg())
        this._btnLaunch?.addEventListener('click', () => this._launch())

        document.addEventListener('sp-cli:settings.loaded', () => this._applyDefaults())
        this._applyDefaults()
        this._renderGroups()   // catalog is static — render once
    }

    // Called by admin.js — no-op in new design (stacks live in nodes-view)
    setData(_) {}

    _applyDefaults() {
        const region   = getDefault('region')        || 'eu-west-2'
        const instance = getDefault('instance_type') || 't3.medium'
        const hours    = getDefault('max_hours')     || 4
        if (this._regionSel)   this._regionSel.value   = region
        if (this._instanceSel) this._instanceSel.value = instance
        if (this._hoursSel)    this._hoursSel.value     = String(hours)
        this._updateCost()
    }

    _renderGroups() {
        if (!this._specGroups) return
        const groups = [...new Set(CATALOG.map(s => s.group))]
        this._specGroups.innerHTML = ''

        for (const group of groups) {
            const specs = CATALOG.filter(s => s.group === group)
            if (!specs.length) continue

            const section = document.createElement('div')
            section.className = 'spec-section'
            section.innerHTML = `<div class="spec-group-label tlabel">${group}</div><div class="spec-card-row"></div>`
            const row = section.querySelector('.spec-card-row')

            for (const spec of specs) {
                const card = document.createElement('div')
                card.className = `spec-card${spec.soon ? ' spec-card--soon' : ''}`
                card.dataset.typeId = spec.type_id
                card.innerHTML = `
                    <div class="sc-icon">${spec.icon}</div>
                    <div class="sc-body">
                        <div class="sc-name">${spec.display_name}</div>
                        <div class="sc-meta">
                            ${spec.stability !== 'stable' ? `<span class="ec2-pill warn">${spec.stability}</span>` : '<span class="ec2-pill good">stable</span>'}
                            ${spec.soon ? '<span class="ec2-pill">soon</span>' : ''}
                            <span class="sc-boot">${spec.boot}</span>
                        </div>
                    </div>
                `
                if (!spec.soon) {
                    card.addEventListener('click', () => this._selectSpec(spec, card))
                }
                row.appendChild(card)
            }
            this._specGroups.appendChild(section)
        }
    }

    _selectSpec(spec, cardEl) {
        Array.from(this.shadowRoot.querySelectorAll('.spec-card')).forEach(c =>
            c.classList.toggle('selected', c === cardEl)
        )
        this._currentSpec = spec
        if (this._cfgIcon) this._cfgIcon.textContent = spec.icon
        if (this._cfgName) this._cfgName.textContent = spec.display_name
        if (this._cfgDesc) this._cfgDesc.textContent = spec.description || ''
        if (this._cfgStab) {
            this._cfgStab.className = `cfg-stability ec2-pill ${spec.stability === 'stable' ? 'good' : 'warn'}`
            this._cfgStab.textContent = spec.stability
        }
        if (this._cfgBoot) this._cfgBoot.textContent = spec.boot
        if (this._barBoot) this._barBoot.textContent = spec.boot
        this._clearError()
        if (this._nameInput) this._nameInput.value = ''
        this._updateCost()
        this._cfgCol.hidden = false
    }

    _closeCfg() {
        this._cfgCol.hidden = true
        this._currentSpec = null
        Array.from(this.shadowRoot.querySelectorAll('.spec-card')).forEach(c => c.classList.remove('selected'))
    }

    _updateCost() {
        const inst  = this._instanceSel?.value || 't3.medium'
        const hours = parseInt(this._hoursSel?.value || '4', 10)
        const rate  = COST_TABLE[inst]
        if (this._barHourly) this._barHourly.textContent = rate ? `$${rate.toFixed(3)}` : '—'
        if (this._barMax)    this._barMax.textContent    = rate ? `$${(rate * hours).toFixed(2)}` : '—'
    }

    async _launch() {
        if (!this._currentSpec) return
        this._setLoading(true)
        this._clearError()
        const body = {
            stack_name:    this._nameInput?.value.trim()  || null,
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
