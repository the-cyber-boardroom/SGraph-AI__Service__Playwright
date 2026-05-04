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
        this._podLogDrawer  = this.$('.pod-log-drawer')
        this._podLogName    = this.$('.pod-log-name')
        this._podLogContent = this.$('.pod-log-content')
        this._blContent     = this.$('.bl-content')
        this._blStatus      = this.$('.bl-status')
        this._blSource      = this.$('.bl-source')
        this._ec2iStatus    = this.$('.ec2i-status')
        this._ec2iLoading   = this.$('.ec2i-loading')
        this._ec2iError     = this.$('.ec2i-error')
        this._ec2iContent   = this.$('.ec2i-content')

        this._liveLogTimer = null
        this._livePodName  = null
        this._liveBtnEl    = this.$('.btn-live-log')

        this.$('.btn-close-log')?.addEventListener('click', () => this._closeLogDrawer())
        this._liveBtnEl?.addEventListener('click', () => this._toggleLiveLog())
        this.$('.btn-refresh-boot')?.addEventListener('click', () => this._fetchBootLog())
        this.$('.btn-refresh-ec2')?.addEventListener('click',  () => this._fetchEc2Info())
        this._nodesView     = this.$('.nodes-view')
        this._nodesList     = this.$('.nodes-list')
        this._resizeHandle  = this.$('.resize-handle')

        this._tabs   = Array.from(this.shadowRoot.querySelectorAll('.sgl-tab'))
        this._panels = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))

        this.$('.btn-refresh')?.addEventListener('click', () =>
            document.dispatchEvent(new CustomEvent('sp-cli:stacks.refresh', { bubbles: true, composed: true }))
        )
        this.$('.btn-close-detail')?.addEventListener('click', () => this._closeDetail())
        this.$('.btn-refresh-ct')?.addEventListener('click', () => this._fetchContainers())
        this.$('.btn-collapse')?.addEventListener('click', () => this._toggleCollapse())
        this._tabs.forEach(t => t.addEventListener('click', () => this._activateTab(t.dataset.tab)))
        this._initResize()

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

        // Update currentStack if it is in the refreshed list (state may have changed)
        if (this._currentStack) {
            const updated = stacks.find(s => s.stack_name === this._currentStack.stack_name)
            if (updated) {
                const wasRunning = this._currentStack.state === 'running'
                this._currentStack = { ...this._currentStack, ...updated }
                // update overview fields live
                const stEl = this._infoKv?.querySelector('[data-kv="state"]')
                if (stEl) stEl.textContent = updated.state
                const upEl = this._infoKv?.querySelector('[data-kv="uptime"]')
                if (upEl) upEl.textContent = _fmtUptime(updated.uptime_seconds)
                // node just became running — switch health poll to sidecar mode
                if (!wasRunning && updated.state === 'running') {
                    if (this._healthPollTimer) { clearInterval(this._healthPollTimer); this._healthPollTimer = null }
                    this._healthPollTimer = setInterval(() => this._pollHealth(), 15000)
                    // now that sidecar is up, fetch boot log if that tab is active
                    const activePanel = this.shadowRoot.querySelector('.tab-panel.active')
                    if (activePanel?.dataset?.panel === 'bootlog') this._fetchBootLog()
                }
            }
        }

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

    _renderApiKeyRow(stack) {
        const key = stack?.host_api_key || ''
        const dt  = document.createElement('dt')
        dt.textContent = 'API Key'

        const dd = document.createElement('dd')
        dd.className = 'api-key-row'

        if (!key) {
            dd.innerHTML = '<span class="api-key-missing">not captured</span>'
            this._infoKv.appendChild(dt)
            this._infoKv.appendChild(dd)
            return
        }

        const val = document.createElement('span')
        val.className = 'mono api-key-val'
        val.textContent = this._keyRevealed ? key : key.slice(0, 8) + '••••••••'

        const eye = document.createElement('button')
        eye.className = 'api-key-btn'
        eye.title = this._keyRevealed ? 'Hide' : 'Reveal'
        eye.textContent = this._keyRevealed ? '🙈' : '👁'
        eye.addEventListener('click', () => {
            this._keyRevealed = !this._keyRevealed
            this._renderApiKeyRow(this._currentStack)
        })

        const copy = document.createElement('button')
        copy.className = 'api-key-btn'
        copy.title = 'Copy'
        copy.textContent = '⎘'
        copy.addEventListener('click', () => navigator.clipboard?.writeText(key))

        // remove old dt/dd if re-rendering
        this._infoKv.querySelector('.api-key-row')?.previousElementSibling?.remove()
        this._infoKv.querySelector('.api-key-row')?.remove()

        dd.appendChild(val)
        dd.appendChild(eye)
        dd.appendChild(copy)
        this._infoKv.appendChild(dt)
        this._infoKv.appendChild(dd)
    }

    _toggleCollapse() {
        this._nodesView?.classList.toggle('list-collapsed')
    }

    _initResize() {
        if (!this._resizeHandle) return
        let startX = 0, startW = 0
        const onMove = (e) => {
            const dx = (e.clientX || e.touches?.[0]?.clientX || 0) - startX
            const w  = Math.max(140, Math.min(600, startW + dx))
            this._nodesView?.style.setProperty('--list-w', `${w}px`)
        }
        const onUp = () => {
            this._resizeHandle?.classList.remove('dragging')
            document.removeEventListener('mousemove', onMove)
            document.removeEventListener('mouseup', onUp)
        }
        this._resizeHandle.addEventListener('mousedown', (e) => {
            e.preventDefault()
            startX = e.clientX
            startW = this._nodesList?.offsetWidth ?? 280
            this._resizeHandle.classList.add('dragging')
            document.addEventListener('mousemove', onMove)
            document.addEventListener('mouseup', onUp)
        })
    }

    _openDetail(stack) {
        if (this._healthPollTimer) { clearInterval(this._healthPollTimer); this._healthPollTimer = null }
        this._currentStack  = stack
        this._keyRevealed   = false
        this._detail.hidden = false
        this.shadowRoot.querySelector('.nodes-view')?.classList.add('detail-open')

        if (this._detIcon) this._detIcon.textContent = TYPE_ICONS[stack.type_id] || '⬡'
        if (this._detName) this._detName.textContent = stack.stack_name

        const hostUrl = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : null)
        if (this._infoKv) {
            this._infoKv.innerHTML = `
                <dt>Type</dt>      <dd>${_esc(stack.type_id)}</dd>
                <dt>State</dt>     <dd data-kv="state">${_esc(stack.state)}</dd>
                <dt>Instance</dt>  <dd>${_esc(stack.instance_type || '—')}</dd>
                <dt>Region</dt>    <dd>${_esc(stack.region || '—')}</dd>
                <dt>Public IP</dt> <dd class="mono">${_esc(stack.public_ip || '—')}</dd>
                ${hostUrl ? `<dt>Host API</dt><dd class="mono">${_esc(hostUrl)}</dd>` : ''}
                <dt>Node ID</dt>   <dd class="mono">${_esc(stack.stack_name)}</dd>
                <dt>Uptime</dt>    <dd data-kv="uptime">${_fmtUptime(stack.uptime_seconds)}</dd>
            `
            this._renderApiKeyRow(stack)
        }

        if (!this._nodesView?.classList.contains('detail-open')) {
            const w = this._nodesList?.offsetWidth ?? 280
            this._nodesView?.style.setProperty('--list-w', `${w}px`)
        }

        this._stopBtn?.setStack?.(stack)
        this._shell?.open?.(stack)
        this._hostApi?.open?.(stack)
        this._activateTab('overview')

        if (stack.state !== 'running') this._activateTab('bootlog')

        // running: poll sidecar every 15s; pending/other: poll SP CLI backend every 5s
        const interval = stack.state === 'running' ? 15000 : 5000
        this._healthPollTimer = setInterval(() => this._pollHealth(), interval)

        Array.from(this.shadowRoot.querySelectorAll('.node-row')).forEach(r =>
            r.classList.toggle('selected', r.querySelector('.row-name')?.textContent === stack.stack_name)
        )
    }

    _closeDetail() {
        if (this._healthPollTimer) { clearInterval(this._healthPollTimer); this._healthPollTimer = null }
        this._detail.hidden = true
        this._currentStack = null
        this.shadowRoot.querySelector('.nodes-view')?.classList.remove('detail-open')
        Array.from(this.shadowRoot.querySelectorAll('.node-row')).forEach(r => r.classList.remove('selected'))
    }

    async _pollHealth() {
        const s = this._currentStack
        if (!s) { clearInterval(this._healthPollTimer); this._healthPollTimer = null; return }

        // Non-running: request a same-origin refresh — setStacks() will handle the transition
        if (s.state !== 'running') {
            document.dispatchEvent(new CustomEvent('sp-cli:nodes.refresh', { bubbles: true, composed: true }))
            return
        }

        const base = s.host_api_url || (s.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s.host_api_key || ''
        if (!base) return
        try {
            const resp = await fetch(`${base}/host/status`, { headers: key ? { 'X-API-Key': key } : {} })
            if (!resp.ok) return
            const st = await resp.json()
            const uptimeEl = this._infoKv?.querySelector('[data-kv="uptime"]')
            if (uptimeEl) uptimeEl.textContent = _fmtUptime(st.uptime_seconds)
            const stateEl = this._infoKv?.querySelector('[data-kv="state"]')
            if (stateEl) stateEl.textContent = `${s.state} (CPU: ${(st.cpu_percent || 0).toFixed(1)}%)`
        } catch (_) {}
    }

    _activateTab(name) {
        this._tabs.forEach(t   => t.classList.toggle('active', t.dataset.tab === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
        if (name === 'containers') this._fetchContainers()
        if (name === 'bootlog')    this._fetchBootLog()
        if (name === 'ec2info')    this._fetchEc2Info()
    }

    async _fetchBootLog() {
        const s    = this._currentStack
        const base = s?.host_api_url || (s?.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s?.host_api_key || ''
        if (!base || !this._blContent) return

        // Sidecar not running yet — show placeholder, no cross-origin fetch
        if (s?.state !== 'running') {
            if (this._blStatus)  this._blStatus.textContent  = 'Waiting for sidecar…'
            if (this._blSource)  this._blSource.textContent  = ''
            if (this._blContent) this._blContent.textContent = '⏳ Node is booting — boot log will appear once the sidecar is up.'
            return
        }

        if (this._blStatus)  this._blStatus.textContent  = 'Loading…'
        if (this._blSource)  this._blSource.textContent  = ''
        if (this._blContent) this._blContent.textContent = ''

        try {
            const resp = await fetch(`${base}/host/logs/boot?lines=300`, {
                headers: key ? { 'X-API-Key': key } : {},
            })
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
            const data = await resp.json()
            if (this._blSource)  this._blSource.textContent  = data.source || ''
            if (this._blStatus)  this._blStatus.textContent  = data.truncated ? `${data.lines} lines (truncated)` : `${data.lines} lines`
            if (this._blContent) {
                this._blContent.textContent = data.content || '(empty)'
                this._blContent.scrollTop   = this._blContent.scrollHeight
            }
        } catch (err) {
            if (this._blStatus)  this._blStatus.textContent  = 'Unreachable — node may still be booting'
            if (this._blContent) this._blContent.textContent = err.message
        }
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
        this._closeLogDrawer()
        if (this._ctStatus) this._ctStatus.textContent = 'Loading…'
        if (this._ctError)  this._ctError.hidden = true
        try {
            const headers = key ? { 'X-API-Key': key } : {}
            const [ctResp, stResp] = await Promise.all([
                fetch(`${base}/pods/list`,   { headers }),
                fetch(`${base}/host/status`, { headers }),
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

    _portLinks(ports, publicIp) {
        const LABELS = { '5601': 'Kibana', '9090': 'Prometheus', '3000': 'Grafana', '8080': 'Web', '80': 'HTTP', '4444': 'Selenium', '8888': 'Jupyter' }
        if (!ports || !publicIp) return []
        const links = []
        for (const [portProto, bindings] of Object.entries(ports)) {
            const hostPort = bindings?.[0]?.HostPort
            if (!hostPort) continue
            const port = portProto.split('/')[0]
            links.push({ url: `http://${publicIp}:${hostPort}`, label: LABELS[port] || `:${hostPort}` })
        }
        return links
    }

    _renderContainers(ct, st) {
        const pods  = ct.pods || []
        const count = ct.count ?? pods.length
        if (this._ctStatus) this._ctStatus.textContent = `${count} pod${count !== 1 ? 's' : ''}`

        if (this._ctHostStats && st) {
            this._ctHostStats.innerHTML = `
                <span class="ct-stat"><span class="ct-stat-lbl">CPU</span>${(st.cpu_percent || 0).toFixed(1)}%</span>
                <span class="ct-stat"><span class="ct-stat-lbl">MEM</span>${st.mem_used_mb || 0} / ${st.mem_total_mb || 0} MB</span>
                <span class="ct-stat"><span class="ct-stat-lbl">DISK</span>${st.disk_used_gb || 0} / ${st.disk_total_gb || 0} GB</span>
                <span class="ct-stat"><span class="ct-stat-lbl">UPTIME</span>${_fmtUptime(st.uptime_seconds)}</span>
            `
        }

        if (!pods.length) {
            if (this._ctList)  this._ctList.innerHTML = ''
            if (this._ctEmpty) this._ctEmpty.hidden = false
            return
        }
        if (this._ctEmpty) this._ctEmpty.hidden = true
        if (this._ctList)  this._ctList.innerHTML = ''

        // fetch stats for all pods in parallel (non-blocking)
        const s    = this._currentStack
        const base = s?.host_api_url || (s?.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s?.host_api_key || ''
        const hdrs = key ? { 'X-API-Key': key } : {}

        for (const c of pods) {
            const stateClass = c.status === 'running' ? 'good' : c.status === 'exited' ? 'bad' : 'warn'
            const links = this._portLinks(c.ports, this._currentStack?.public_ip)
            const linksHtml = links.length
                ? `<div class="ct-ports">${links.map(l => `<a class="ct-port-link" href="${_esc(l.url)}" target="_blank" rel="noopener">${_esc(l.label)}</a>`).join('')}</div>`
                : ''
            const row = document.createElement('div')
            row.className = 'ct-row'
            row.dataset.pod = c.name
            row.innerHTML = `
                <span class="ct-name">${_esc(c.name)}</span>
                <span class="ec2-pill dot ${stateClass} ct-pill">${_esc(c.status)}</span>
                <span class="ct-image">${_esc(c.image)}</span>
                ${linksHtml}
                <span class="ct-stats ct-state"></span>
                <button class="ct-log-btn" title="View logs">📋</button>
            `
            const statsEl = row.querySelector('.ct-stats')
            row.querySelector('.ct-log-btn')?.addEventListener('click', (e) => {
                e.stopPropagation()
                this._fetchPodLogs(c.name)
            })
            this._ctList?.appendChild(row)

            if (base) {
                fetch(`${base}/pods/${encodeURIComponent(c.name)}/stats`, { headers: hdrs })
                    .then(r => r.ok ? r.json() : null)
                    .then(st => {
                        if (st && statsEl) {
                            statsEl.textContent = `CPU ${st.cpu_percent.toFixed(1)}%  MEM ${st.mem_usage_mb.toFixed(0)}MB`
                        }
                    })
                    .catch(() => {})
            }
        }
    }

    async _fetchPodLogs(name) {
        this._stopLiveLog()
        const s    = this._currentStack
        const base = s?.host_api_url || (s?.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s?.host_api_key || ''
        if (!base || !this._podLogDrawer) return

        if (this._podLogName)    this._podLogName.textContent = name
        if (this._podLogContent) this._podLogContent.textContent = 'Loading…'
        this._podLogDrawer.hidden = false

        try {
            const resp = await fetch(`${base}/pods/${encodeURIComponent(name)}/logs?tail=200`, {
                headers: key ? { 'X-API-Key': key } : {},
            })
            const data = await resp.json()
            if (this._podLogContent) {
                this._podLogContent.textContent = resp.ok
                    ? (data.content || '(no output)')
                    : `Error ${resp.status}: ${data.detail || ''}`
                this._podLogContent.scrollTop = this._podLogContent.scrollHeight
            }
        } catch (err) {
            if (this._podLogContent) this._podLogContent.textContent = `Unreachable: ${err.message}`
        }
    }

    _closeLogDrawer() {
        this._stopLiveLog()
        if (this._podLogDrawer) this._podLogDrawer.hidden = true
    }

    _toggleLiveLog() {
        if (this._liveLogTimer) {
            this._stopLiveLog()
        } else {
            this._livePodName = this._podLogName?.textContent || null
            if (!this._livePodName) return
            this._liveLogTimer = setInterval(() => this._pollLiveLogs(), 3000)
            if (this._liveBtnEl) this._liveBtnEl.textContent = '⏸ Live'
            this._liveBtnEl?.classList.add('live-active')
        }
    }

    _stopLiveLog() {
        if (this._liveLogTimer) { clearInterval(this._liveLogTimer); this._liveLogTimer = null }
        this._livePodName = null
        if (this._liveBtnEl) this._liveBtnEl.textContent = '▶ Live'
        this._liveBtnEl?.classList.remove('live-active')
    }

    async _fetchEc2Info() {
        const s    = this._currentStack
        const base = s?.host_api_url || (s?.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s?.host_api_key || ''
        if (!base) return

        if (s?.state !== 'running') {
            if (this._ec2iStatus)  this._ec2iStatus.textContent  = 'Waiting for sidecar…'
            if (this._ec2iLoading) this._ec2iLoading.textContent = '⏳ Node is booting — EC2 info available once sidecar is up.'
            return
        }

        if (this._ec2iLoading) { this._ec2iLoading.textContent = 'Loading…'; this._ec2iLoading.hidden = false }
        if (this._ec2iError)   this._ec2iError.hidden = true
        if (this._ec2iContent) this._ec2iContent.hidden = true
        if (this._ec2iStatus)  this._ec2iStatus.textContent = ''

        try {
            const resp = await fetch(`${base}/host/ec2-info`, { headers: key ? { 'X-API-Key': key } : {} })
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
            const data = await resp.json()
            if (data.error) throw new Error(data.error)
            if (this._ec2iLoading) this._ec2iLoading.hidden = true
            if (this._ec2iContent) this._ec2iContent.hidden = false
            if (this._ec2iStatus)  this._ec2iStatus.textContent = `${data.instance_id} · ${data.instance_type} · ${data.region}`
            this._renderEc2Info(data)
        } catch (err) {
            if (this._ec2iLoading) this._ec2iLoading.hidden = true
            if (this._ec2iError)   { this._ec2iError.textContent = err.message; this._ec2iError.hidden = false }
            if (this._ec2iStatus)  this._ec2iStatus.textContent = 'Error fetching EC2 info'
        }
    }

    _renderEc2Info(d) {
        const kv = (el, pairs) => {
            if (!el) return
            el.innerHTML = pairs.map(([k, v]) =>
                `<dt>${_esc(k)}</dt><dd>${_esc(String(v || '—'))}</dd>`
            ).join('')
        }

        kv(this._ec2iContent?.querySelector('.instance-kv'), [
            ['Instance ID',  d.instance_id],
            ['Type',         d.instance_type],
            ['AMI',          d.ami_id],
            ['State',        d.state],
            ['AZ',           d.availability_zone],
            ['Launch Time',  d.launch_time],
        ])
        kv(this._ec2iContent?.querySelector('.network-kv'), [
            ['Public IP',    d.public_ip],
            ['Private IP',   d.private_ip],
            ['Public DNS',   d.public_dns],
            ['Private DNS',  d.private_dns],
            ['VPC',          d.vpc_id],
            ['Subnet',       d.subnet_id],
        ])
        kv(this._ec2iContent?.querySelector('.iam-kv'), [
            ['Profile Name', d.iam_profile_name],
            ['Profile ARN',  d.iam_profile_arn],
        ])

        const tagsEl = this._ec2iContent?.querySelector('.tags-kv')
        if (tagsEl) {
            const pairs = Object.entries(d.tags || {})
            tagsEl.innerHTML = pairs.length
                ? pairs.map(([k, v]) => `<dt>${_esc(k)}</dt><dd>${_esc(v)}</dd>`).join('')
                : '<dt>—</dt><dd>no tags</dd>'
        }

        const volsEl = this._ec2iContent?.querySelector('.ec2i-volumes')
        if (volsEl) {
            volsEl.innerHTML = (d.volumes || []).map(v => `
                <div class="ec2i-vol">
                  <span class="ec2i-vol-dev">${_esc(v.device)}</span>
                  <span class="ec2i-vol-id">${_esc(v.volume_id)}</span>
                  <span class="ec2i-vol-size">${v.size_gb || 0} GB · ${_esc(v.volume_type || '—')}</span>
                  ${v.encrypted ? '<span class="ec2i-vol-enc">🔒 encrypted</span>' : ''}
                </div>
            `).join('') || '<span style="font-size:11px;color:var(--text-3)">No volumes</span>'
        }

        const sgsEl = this._ec2iContent?.querySelector('.ec2i-sgs')
        if (sgsEl) {
            sgsEl.innerHTML = (d.security_groups || []).map(sg => {
                const fmtRules = (rules) => rules.length
                    ? rules.map(r => `
                        <div class="ec2i-rule">
                          <span class="ec2i-rule-proto">${_esc(r.protocol)}</span>
                          <span class="ec2i-rule-ports">${_esc(r.ports)}</span>
                          <span class="ec2i-rule-src">${_esc((r.sources || []).join(', '))}</span>
                          ${r.description ? `<span class="ec2i-rule-desc">${_esc(r.description)}</span>` : ''}
                        </div>`).join('')
                    : '<span style="font-size:10px;color:var(--text-4)">none</span>'
                return `
                  <div class="ec2i-sg">
                    <div class="ec2i-sg-title">${_esc(sg.name)} <span style="color:var(--text-3);font-size:10px">${_esc(sg.id)}</span></div>
                    <div class="ec2i-sg-subtitle">Inbound</div>${fmtRules(sg.inbound)}
                    <div class="ec2i-sg-subtitle">Outbound</div>${fmtRules(sg.outbound)}
                  </div>`
            }).join('') || '<span style="font-size:11px;color:var(--text-3)">No security groups</span>'
        }
    }

    async _pollLiveLogs() {
        if (this._podLogDrawer?.hidden || !this._livePodName) { this._stopLiveLog(); return }
        const s    = this._currentStack
        const base = s?.host_api_url || (s?.public_ip ? `http://${s.public_ip}:19009` : '')
        const key  = s?.host_api_key || ''
        if (!base) { this._stopLiveLog(); return }
        try {
            const resp = await fetch(`${base}/pods/${encodeURIComponent(this._livePodName)}/logs?tail=100`, {
                headers: key ? { 'X-API-Key': key } : {},
            })
            if (!resp.ok) return
            const data = await resp.json()
            if (this._podLogContent) {
                this._podLogContent.textContent = data.content || '(no output)'
                this._podLogContent.scrollTop = this._podLogContent.scrollHeight
            }
        } catch (_) {}
    }
}

customElements.define('sp-cli-nodes-view', SpCliNodesView)
