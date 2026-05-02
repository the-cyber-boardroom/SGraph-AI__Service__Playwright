import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import {
    getAllPluginToggles, getUIPanelVisible, getDefault,
    setPluginEnabled, setUIPanelVisible, setDefault, isLoaded,
} from '../../../../../../shared/settings-bus.js'
import { isWritable } from '../../../../../../shared/vault-bus.js'

const ROOT_LAYOUT_KEY = 'sp-cli:admin:root-layout:v1'

const PLUGINS = [
    { name: 'docker',     icon: '🐳', label: 'Docker host',             stability: 'stable',       boot: '~10min' },
    { name: 'podman',     icon: '🦭', label: 'Podman host',             stability: 'stable',       boot: '~10min' },
    { name: 'elastic',    icon: '🔍', label: 'Elastic + Kibana',        stability: 'stable',       boot: '~90s'   },
    { name: 'vnc',        icon: '🖥',  label: 'VNC bastion',             stability: 'stable',       boot: '~90s'   },
    { name: 'prometheus', icon: '📊', label: 'Prometheus + Grafana',    stability: 'experimental', boot: '—'      },
    { name: 'opensearch', icon: '🌐', label: 'OpenSearch + Dashboards', stability: 'experimental', boot: '—'      },
    { name: 'neko',       icon: '🌐', label: 'Neko (WebRTC browser)',   stability: 'experimental', boot: '—'      },
    { name: 'firefox',    icon: '🦊', label: 'Firefox (noVNC)',         stability: 'experimental', boot: '—'      },
]

const UI_PANELS = [
    { name: 'events_log',      label: 'Events Log'      },
    { name: 'vault_status',    label: 'Vault Status'    },
    { name: 'active_sessions', label: 'Active Sessions' },
    { name: 'cost_tracker',    label: 'Cost Tracker'    },
]

const REGIONS        = ['eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2']
const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge']
const MAX_HOURS      = [1, 2, 4, 8, 12, 24]

class SpCliSettingsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-settings-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._pluginList  = this.$('.plugin-list')
        this._panelList   = this.$('.panel-list')
        this._regionSel   = this.$('.def-region')
        this._hoursSel    = this.$('.def-hours')
        this._instSel     = this.$('.def-instance')
        this._roBanner    = this.$('.ro-banner')
        this._resetBtn    = this.$('.btn-reset-layout')

        this._populateSelect(this._regionSel, REGIONS,        r => r)
        this._populateSelect(this._hoursSel,  MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)
        this._populateSelect(this._instSel,   INSTANCE_TYPES, t => t)

        this._regionSel?.addEventListener('change', () => setDefault('region',        this._regionSel.value))
        this._hoursSel?.addEventListener('change',  () => setDefault('max_hours',     parseInt(this._hoursSel.value, 10)))
        this._instSel?.addEventListener('change',   () => setDefault('instance_type', this._instSel.value))

        this._resetBtn?.addEventListener('click', () => this._resetLayout())

        document.addEventListener('sp-cli:settings.loaded',  () => this._render())
        document.addEventListener('vault:disconnected',       () => { if (this._roBanner) this._roBanner.hidden = true })

        if (isLoaded()) this._render()
    }

    _render() {
        this._renderPlugins()
        this._renderPanels()
        this._renderDefaults()
        this._updateRoBanner()
    }

    _renderPlugins() {
        if (!this._pluginList) return
        const toggles = getAllPluginToggles()
        this._pluginList.innerHTML = ''
        for (const p of PLUGINS) {
            const enabled = toggles[p.name]?.enabled ?? false
            const row     = document.createElement('label')
            row.className = 'toggle-row'
            row.innerHTML = `
                <input type="checkbox" class="toggle-cb" data-plugin="${_esc(p.name)}"${enabled ? ' checked' : ''}>
                <span class="toggle-icon">${p.icon}</span>
                <span class="toggle-label">${_esc(p.label)}</span>
                ${p.stability === 'experimental' ? '<span class="badge-exp">experimental</span>' : ''}
                <span class="toggle-boot">${_esc(p.boot)}</span>
            `
            row.querySelector('.toggle-cb')?.addEventListener('change', async (e) => {
                await setPluginEnabled(p.name, e.target.checked)
            })
            this._pluginList.appendChild(row)
        }
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

    _updateRoBanner() {
        if (this._roBanner) this._roBanner.hidden = isWritable()
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

customElements.define('sp-cli-settings-view', SpCliSettingsView)
