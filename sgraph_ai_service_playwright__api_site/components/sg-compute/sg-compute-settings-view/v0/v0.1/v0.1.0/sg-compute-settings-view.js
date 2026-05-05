import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import {
    getUIPanelVisible, getDefault,
    setUIPanelVisible, setDefault, isLoaded,
} from '../../../../../../shared/settings-bus.js'

const ROOT_LAYOUT_KEY = 'sp-cli:admin:root-layout:v1'

const UI_PANELS = [
    { name: 'events_log',      label: 'Events Log'      },
    { name: 'vault_status',    label: 'Vault Status'    },
    { name: 'active_sessions', label: 'Active Sessions' },
    { name: 'cost_tracker',    label: 'Cost Tracker'    },
]

const REGIONS        = ['eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2']
const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge']
const MAX_HOURS      = [1, 2, 4, 8, 12, 24]

class SgComputeSettingsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-settings-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._panelList   = this.$('.panel-list')
        this._regionSel   = this.$('.def-region')
        this._hoursSel    = this.$('.def-hours')
        this._instSel     = this.$('.def-instance')
        this._resetBtn    = this.$('.btn-reset-layout')

        this._populateSelect(this._regionSel, REGIONS,        r => r)
        this._populateSelect(this._hoursSel,  MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)
        this._populateSelect(this._instSel,   INSTANCE_TYPES, t => t)

        this._regionSel?.addEventListener('change', () => setDefault('region',        this._regionSel.value))
        this._hoursSel?.addEventListener('change',  () => setDefault('max_hours',     parseInt(this._hoursSel.value, 10)))
        this._instSel?.addEventListener('change',   () => setDefault('instance_type', this._instSel.value))

        this._resetBtn?.addEventListener('click', () => this._resetLayout())

        document.addEventListener('sp-cli:settings.loaded',  () => this._render())

        if (isLoaded()) this._render()
    }

    _render() {
        this._renderPanels()
        this._renderDefaults()
    }

    _renderPanels() {
        if (!this._panelList) return
        this._panelList.innerHTML = ''
        for (const panel of UI_PANELS) {
            const visible = getUIPanelVisible(panel.name)
            const row     = document.createElement('label')
            row.className = 'toggle-row'
            row.innerHTML = `
                <input type="checkbox" class="toggle-cb"${visible ? ' checked' : ''}>
                <span class="toggle-label">${_esc(panel.label)}</span>
                <span class="toggle-boot">(right panel)</span>
            `
            row.querySelector('.toggle-cb')?.addEventListener('change', async (e) => {
                await setUIPanelVisible(panel.name, e.target.checked)
            })
            this._panelList.appendChild(row)
        }
    }

    _renderDefaults() {
        if (this._regionSel) this._regionSel.value = getDefault('region')        || 'eu-west-2'
        if (this._hoursSel)  this._hoursSel.value  = String(getDefault('max_hours') ?? 4)
        if (this._instSel)   this._instSel.value   = getDefault('instance_type') || 't3.medium'
    }

    _resetLayout() {
        try { localStorage.removeItem(ROOT_LAYOUT_KEY) } catch (_) {}
        window.location.reload()
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

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

customElements.define('sg-compute-settings-view', SgComputeSettingsView)
