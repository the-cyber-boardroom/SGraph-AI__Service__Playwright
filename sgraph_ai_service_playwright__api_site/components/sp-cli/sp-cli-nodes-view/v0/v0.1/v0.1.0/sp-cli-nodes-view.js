import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '../../../../_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js'
import '../../../../_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js'
import '../../../../_shared/sp-cli-stop-button/v0/v0.1/v0.1.0/sp-cli-stop-button.js'

const TYPE_ICONS = {
    docker: '🐳', podman: '🦭', elastic: '🔍', vnc: '🖥',
    prometheus: '📊', opensearch: '🌐', neko: '🌐', firefox: '🦊',
}

function _fmtUptime(sec) {
    if (!sec || sec < 0) return '—'
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m` : `${sec}s`
}

class SpCliNodesView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-nodes-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._rows     = this.$('.node-rows')
        this._empty    = this.$('.empty-state')
        this._counter  = this.$('.node-count')
        this._detail   = this.$('.node-detail')
        this._detName  = this.$('.detail-name')
        this._detIcon  = this.$('.detail-icon')
        this._infoKv   = this.$('.info-kv')
        this._shell    = this.$('.host-shell')
        this._hostApi  = this.$('.host-api-panel')
        this._stopBtn  = this.$('.stop-btn')

        this._tabs   = Array.from(this.shadowRoot.querySelectorAll('.sgl-tab'))
        this._panels = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))

        this.$('.btn-refresh')?.addEventListener('click', () =>
            document.dispatchEvent(new CustomEvent('sp-cli:stacks.refresh', { bubbles: true, composed: true }))
        )
        this.$('.btn-close-detail')?.addEventListener('click', () => this._closeDetail())
        this._tabs.forEach(t => t.addEventListener('click', () => this._activateTab(t.dataset.tab)))

        if (this._pendingStacks) {
            this.setStacks(this._pendingStacks)
            this._pendingStacks = null
        } else {
            this.setStacks([])
            // Request fresh data — this view may mount after the initial load
            document.dispatchEvent(new CustomEvent('sp-cli:stacks.refresh', { bubbles: true, composed: true }))
        }
    }

    setStacks(stacks = []) {
        if (!this._rows) { this._pendingStacks = stacks; return }
        this._stacks = stacks
        this._renderList(stacks)
    }

    _renderList(stacks) {
        const has = stacks.length > 0
        this._empty.hidden = has
        this._rows.hidden  = !has
        if (this._counter) this._counter.textContent = has ? `(${stacks.length})` : ''
        if (!has) { this._rows.innerHTML = ''; return }

        this._rows.innerHTML = ''
        for (const s of stacks) {
            const row = document.createElement('div')
            row.className = 'node-row'
            const stateClass = s.state === 'running' ? 'good' : s.state === 'stopped' ? 'bad' : 'warn'
            row.innerHTML = `
                <span class="row-icon">${TYPE_ICONS[s.type_id] || '⬡'}</span>
                <span class="row-name">${s.stack_name}</span>
                <span class="ec2-pill dot ${stateClass}">${s.state}</span>
                <span class="row-ip mono">${s.public_ip || '—'}</span>
                <span class="row-uptime">${_fmtUptime(s.uptime_seconds)}</span>
            `
            row.addEventListener('click', () => this._openDetail(s))
            this._rows.appendChild(row)
        }
    }

    _openDetail(stack) {
        this._currentStack = stack
        this._detail.hidden = false

        if (this._detIcon) this._detIcon.textContent = TYPE_ICONS[stack.type_id] || '⬡'
        if (this._detName) this._detName.textContent = stack.stack_name

        if (this._infoKv) this._infoKv.innerHTML = `
            <dt>Type</dt>      <dd>${stack.type_id}</dd>
            <dt>State</dt>     <dd>${stack.state}</dd>
            <dt>Instance</dt>  <dd>${stack.instance_type || '—'}</dd>
            <dt>Region</dt>    <dd>${stack.region || '—'}</dd>
            <dt>Public IP</dt> <dd>${stack.public_ip || '—'}</dd>
            <dt>Node ID</dt>   <dd class="mono">${stack.stack_name}</dd>
            <dt>Uptime</dt>    <dd>${_fmtUptime(stack.uptime_seconds)}</dd>
        `

        this._stopBtn?.setStack?.(stack)
        this._shell?.open?.(stack)
        this._hostApi?.open?.(stack)
        this._activateTab('overview')

        Array.from(this.shadowRoot.querySelectorAll('.node-row')).forEach(r =>
            r.classList.toggle('selected', r.querySelector('.row-name')?.textContent === stack.stack_name)
        )
    }

    _closeDetail() {
        this._detail.hidden = true
        this._currentStack = null
        Array.from(this.shadowRoot.querySelectorAll('.node-row')).forEach(r => r.classList.remove('selected'))
    }

    _activateTab(name) {
        this._tabs.forEach(t   => t.classList.toggle('active', t.dataset.tab === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
    }
}

customElements.define('sp-cli-nodes-view', SpCliNodesView)
