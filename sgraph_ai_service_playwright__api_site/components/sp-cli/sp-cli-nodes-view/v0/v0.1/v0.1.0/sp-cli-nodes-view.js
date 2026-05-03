import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '../../../../_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js'
import '../../../../_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js'
import '../../../../_shared/sp-cli-stop-button/v0/v0.1/v0.1.0/sp-cli-stop-button.js'

const _EC2_CSS = new URL('../../../../../../shared/ec2-tokens.css', import.meta.url).href

const TYPE_ICONS = {
    docker: '🐳', podman: '🦭', elastic: '🔍', vnc: '🖥',
    prometheus: '📊', opensearch: '🌐', neko: '🌐', firefox: '🦊',
}

function _fmtUptime(sec) {
    if (!sec || sec < 0) return '—'
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m` : `${sec}s`
}

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

class SpCliNodesView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-nodes-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._rows          = this.$('.node-rows')
        this._empty         = this.$('.empty-state')
        this._counter       = this.$('.node-count')
        this._detail        = this.$('.node-detail')
        this._detName       = this.$('.detail-name')
        this._detIcon       = this.$('.detail-icon')
        this._infoKv        = this.$('.info-kv')
        this._shell         = this.$('.host-shell')
        this._hostApi       = this.$('.host-api-panel')
        this._stopBtn       = this.$('.stop-btn')
        this._ctList        = this.$('.ct-list')
        this._ctEmpty       = this.$('.ct-empty')
        this._ctError       = this.$('.ct-error')
        this._ctStatus      = this.$('.ct-status')
        this._ctHostStats   = this.$('.ct-host-stats')

        this._tabs   = Array.from(this.shadowRoot.querySelectorAll('.sgl-tab'))
        this._panels = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))

        this.$('.btn-refresh')?.addEventListener('click', () =>
            document.dispatchEvent(new CustomEvent('sp-cli:stacks.refresh', { bubbles: true, composed: true }))
        )
        this.$('.btn-close-detail')?.addEventListener('click', () => this._closeDetail())
        this.$('.btn-refresh-ct')?.addEventListener('click', () => this._fetchContainers())
        this._tabs.forEach(t => t.addEventListener('click', () => this._activateTab(t.dataset.tab)))

        if (this._pendingStacks) {
            this.setStacks(this._pendingStacks)
            this._pendingStacks = null
        } else {
            this.setStacks([])
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
        this.shadowRoot.querySelector('.nodes-view')?.classList.add('detail-open')

        if (this._detIcon) this._detIcon.textContent = TYPE_ICONS[stack.type_id] || '⬡'
        if (this._detName) this._detName.textContent = stack.stack_name

        const hostUrl = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : null)
        if (this._infoKv) this._infoKv.innerHTML = `
            <dt>Type</dt>      <dd>${_esc(stack.type_id)}</dd>
            <dt>State</dt>     <dd>${_esc(stack.state)}</dd>
            <dt>Instance</dt>  <dd>${_esc(stack.instance_type || '—')}</dd>
            <dt>Region</dt>    <dd>${_esc(stack.region || '—')}</dd>
            <dt>Public IP</dt> <dd class="mono">${_esc(stack.public_ip || '—')}</dd>
            ${hostUrl ? `<dt>Host API</dt> <dd class="mono">${_esc(hostUrl)}</dd>` : ''}
            ${stack.host_api_key ? `<dt>API Key</dt> <dd class="mono key-trunc">${_esc(stack.host_api_key.slice(0,12))}…</dd>` : ''}
            <dt>Node ID</dt>   <dd class="mono">${_esc(stack.stack_name)}</dd>
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
        this.shadowRoot.querySelector('.nodes-view')?.classList.remove('detail-open')
        Array.from(this.shadowRoot.querySelectorAll('.node-row')).forEach(r => r.classList.remove('selected'))
    }

    _activateTab(name) {
        this._tabs.forEach(t   => t.classList.toggle('active', t.dataset.tab === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
        if (name === 'containers') this._fetchContainers()
    }

    async _fetchContainers() {
        const s = this._currentStack
        if (!s) return
        const base = s.host_api_url || (s.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s.host_api_key || ''
        if (!base) {
            if (this._ctStatus) this._ctStatus.textContent = 'No host URL'
            return
        }
        if (this._ctStatus) this._ctStatus.textContent = 'Loading…'
        if (this._ctError)  this._ctError.hidden = true
        try {
            const headers = key ? { 'X-API-Key': key } : {}
            const [ctResp, stResp] = await Promise.all([
                fetch(`${base}/containers/list`,  { headers }),
                fetch(`${base}/host/status`,      { headers }),
            ])
            if (!ctResp.ok) throw new Error(`HTTP ${ctResp.status}`)
            const ct = await ctResp.json()
            const st = stResp.ok ? await stResp.json() : null
            this._renderContainers(ct, st)
        } catch (err) {
            if (this._ctStatus) this._ctStatus.textContent = 'Unreachable'
            if (this._ctError)  { this._ctError.textContent = err.message; this._ctError.hidden = false }
            if (this._ctHostStats) this._ctHostStats.innerHTML = ''
        }
    }

    _renderContainers(ct, st) {
        const containers = ct.containers || []
        const count = ct.count ?? containers.length
        if (this._ctStatus) this._ctStatus.textContent = `${count} container${count !== 1 ? 's' : ''}`

        if (this._ctHostStats && st) {
            this._ctHostStats.innerHTML = `
                <span class="ct-stat"><span class="ct-stat-lbl">CPU</span>${(st.cpu_percent || 0).toFixed(1)}%</span>
                <span class="ct-stat"><span class="ct-stat-lbl">MEM</span>${st.mem_used_mb || 0} / ${st.mem_total_mb || 0} MB</span>
                <span class="ct-stat"><span class="ct-stat-lbl">DISK</span>${st.disk_used_gb || 0} / ${st.disk_total_gb || 0} GB</span>
                <span class="ct-stat"><span class="ct-stat-lbl">UPTIME</span>${_fmtUptime(st.uptime_seconds)}</span>
            `
        }

        if (!containers.length) {
            if (this._ctList)  this._ctList.innerHTML = ''
            if (this._ctEmpty) this._ctEmpty.hidden = false
            return
        }
        if (this._ctEmpty) this._ctEmpty.hidden = true
        if (this._ctList)  this._ctList.innerHTML = ''

        for (const c of containers) {
            const stateClass = c.status === 'running' ? 'good' : c.status === 'exited' ? 'bad' : 'warn'
            const row = document.createElement('div')
            row.className = 'ct-row'
            row.innerHTML = `
                <span class="ct-name">${_esc(c.name)}</span>
                <span class="ec2-pill dot ${stateClass} ct-pill">${_esc(c.status)}</span>
                <span class="ct-image">${_esc(c.image)}</span>
                <span class="ct-state">${_esc(c.state)}</span>
            `
            this._ctList?.appendChild(row)
        }
    }
}

customElements.define('sp-cli-nodes-view', SpCliNodesView)
