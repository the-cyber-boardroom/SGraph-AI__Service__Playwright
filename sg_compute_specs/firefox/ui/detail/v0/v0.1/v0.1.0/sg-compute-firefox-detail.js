import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '/ui/shared/api-client.js'
import { isRunning   } from '/ui/shared/node-state.js'
import '/ui/components/sg-compute/_shared/sg-compute-stack-header/v0/v0.1/v0.1.0/sg-compute-stack-header.js'
import '/ui/components/sg-compute/_shared/sg-compute-ssm-command/v0/v0.1/v0.1.0/sg-compute-ssm-command.js'
import '/ui/components/sg-compute/_shared/sg-compute-network-info/v0/v0.1/v0.1.0/sg-compute-network-info.js'
import '/ui/components/sg-compute/_shared/sg-compute-stop-button/v0/v0.1/v0.1.0/sg-compute-stop-button.js'
import '/ui/components/sg-compute/_shared/sg-remote-browser/v0/v0.1/v0.1.0/sg-remote-browser.js'
import '/ui/components/sg-compute/_shared/sg-compute-host-shell/v0/v0.1/v0.1.0/sg-compute-host-shell.js'
import '/ui/components/sg-compute/_shared/sg-compute-host-api-panel/v0/v0.1/v0.1.0/sg-compute-host-api-panel.js'

const FIREFOX_IMAGE       = 'jlesage/firefox'
const FIREFOX_INNER_PORT  = '5800/tcp'
const DEFAULT_HOST_PORT   = 5801

class SgComputeFirefoxDetail extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-firefox-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        // ── Info tab ───────────────────────────────────────────────────── //
        this._header         = this.$('.detail-header')
        this._ssm            = this.$('.detail-ssm')
        this._net            = this.$('.detail-net')
        this._stop           = this.$('.detail-stop')
        this._browserSection = this.$('.browser-section')
        this._remoteBrowser  = this.$('.remote-browser')
        this._shell          = this.$('.host-shell')
        this._hostApi        = this.$('.host-api-panel')

        // ── Pods tab ───────────────────────────────────────────────────── //
        this._podsList       = this.$('.pods-list')
        this._podsStatus     = this.$('.pods-status')
        this._podNameInput   = this.$('.pod-name-input')
        this._podPortInput   = this.$('.pod-port-input')
        this._podPassInput   = this.$('.pod-pass-input')
        this._podImageInput  = this.$('.pod-image-input')
        this._podLaunchBtn   = this.$('.pod-launch-btn')
        this._podCreateStatus= this.$('.pod-create-status')
        this._viewerEmpty    = this.$('.pods-viewer-empty')
        this._viewerActive   = this.$('.pods-viewer-active')
        this._viewerLabel    = this.$('.pods-viewer-label')
        this._viewerNewTab   = this.$('.pods-viewer-newtab')
        this._podsIframe     = this.$('.pods-iframe')

        this.$('.pods-refresh')?.addEventListener('click', () => this._loadPods())
        this._podLaunchBtn?.addEventListener('click', () => this._createPod())

        // ── Tabs ───────────────────────────────────────────────────────── //
        this._tabs   = Array.from(this.shadowRoot.querySelectorAll('.tab-btn'))
        this._panels = Array.from(this.shadowRoot.querySelectorAll('.tab-panel'))
        this._tabs.forEach(btn => btn.addEventListener('click', () => this._activateTab(btn.dataset.tab)))

        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._header) { this._pendingStack = stack; return }
        this._stack = stack
        if (this._browserSection) this._browserSection.hidden = true
        this._header.setStack?.(stack)
        this._ssm.setStack?.(stack)
        this._net.setStack?.(stack)
        this._stop.setStack?.(stack)
        this._shell  ?.open?.(stack)
        this._hostApi?.open?.(stack)
        this._fetchDetail(stack)
        // load pods if tab is already active
        if (this._currentTab === 'pods') this._loadPods()
    }

    async _fetchDetail(stack) {
        try {
            const info = await apiClient.get(`/firefox/stack/${stack.node_id}`)
            if (!this._stack || this._stack.node_id !== stack.node_id) return
            const merged = { ...stack, ...info }
            this._header.setStack?.(merged)
            this._ssm.setStack?.(merged)
            this._net.setStack?.(merged)
            if (merged.public_ip && isRunning(merged.state)) {
                this._openBrowser(merged.public_ip)
            }
        } catch (_) {}
    }

    _openBrowser(ip) {
        if (this._browserSection) this._browserSection.hidden = false
        this._remoteBrowser?.open?.({ url: `http://${ip}:5800`, provider: 'iframe' })
    }

    _activateTab(name) {
        this._currentTab = name
        this._tabs  .forEach(b => b.classList.toggle('active', b.dataset.tab   === name))
        this._panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name))
        if (name === 'pods' && this._stack) this._loadPods()
    }

    // ── Pods tab ────────────────────────────────────────────────────────── //

    async _loadPods() {
        if (!this._stack) return
        this._setPodsStatus('Loading…')
        this._podsList.innerHTML = ''
        try {
            const data = await apiClient.get(`/api/nodes/${this._stack.node_id}/pods/list`)
            const pods = (data?.pods || []).filter(p => p.type_id === 'firefox')
            this._renderPods(pods)
            this._suggestNextPort(pods)
            this._setPodsStatus(pods.length ? '' : 'No Firefox pods running.')
        } catch (err) {
            this._setPodsStatus(`Error: ${err.message}`)
        }
    }

    _renderPods(pods) {
        this._podsList.innerHTML = ''
        for (const pod of pods) {
            this._podsList.appendChild(this._makePodRow(pod))
        }
    }

    _makePodRow(pod) {
        const hostPort = this._hostPortFor(pod)
        const url      = hostPort && this._stack?.public_ip
            ? `http://${this._stack.public_ip}:${hostPort}`
            : null

        const row = document.createElement('div')
        row.className = `pod-row ${pod.status === 'running' ? 'pod-running' : 'pod-stopped'}`

        const nameEl = document.createElement('div')
        nameEl.className = 'pod-row-name'
        nameEl.textContent = pod.name

        const stateEl = document.createElement('div')
        stateEl.className = 'pod-row-state'
        stateEl.textContent = pod.state || pod.status || '—'

        const portEl = document.createElement('div')
        portEl.className = 'pod-row-port'
        portEl.textContent = hostPort ? `:${hostPort}` : '—'

        const actions = document.createElement('div')
        actions.className = 'pod-row-actions'

        if (url) {
            const openBtn = document.createElement('button')
            openBtn.className = 'ec2-btn pod-open-btn'
            openBtn.title = 'Open in panel'
            openBtn.textContent = '⊡'
            openBtn.addEventListener('click', () => this._openPodViewer(pod, url))
            actions.appendChild(openBtn)

            const newTabLink = document.createElement('a')
            newTabLink.className = 'ec2-btn pod-newtab-btn'
            newTabLink.href = url
            newTabLink.target = '_blank'
            newTabLink.rel = 'noopener noreferrer'
            newTabLink.title = 'Open in new tab (authorise cert)'
            newTabLink.textContent = '↗'
            actions.appendChild(newTabLink)
        }

        const delBtn = document.createElement('button')
        delBtn.className = 'ec2-btn pod-del-btn'
        delBtn.title = 'Remove pod'
        delBtn.textContent = '✕'
        delBtn.addEventListener('click', async () => {
            if (!confirm(`Remove pod "${pod.name}"?`)) return
            delBtn.disabled = true
            try {
                await apiClient.delete(`/api/nodes/${this._stack.node_id}/pods/${pod.name}`)
                row.remove()
                if (this._viewerLabel?.textContent === pod.name) this._closeViewer()
            } catch (err) {
                this._setPodsStatus(`Delete failed: ${err.message}`)
                delBtn.disabled = false
            }
        })
        actions.appendChild(delBtn)

        row.appendChild(nameEl)
        row.appendChild(stateEl)
        row.appendChild(portEl)
        row.appendChild(actions)
        return row
    }

    _openPodViewer(pod, url) {
        if (this._viewerEmpty)  this._viewerEmpty.hidden  = true
        if (this._viewerActive) this._viewerActive.hidden = false
        if (this._viewerLabel)  this._viewerLabel.textContent = pod.name
        if (this._viewerNewTab) this._viewerNewTab.href = url
        if (this._podsIframe)   this._podsIframe.src = url
    }

    _closeViewer() {
        if (this._viewerEmpty)  this._viewerEmpty.hidden  = false
        if (this._viewerActive) this._viewerActive.hidden = true
        if (this._podsIframe)   this._podsIframe.src = ''
    }

    async _createPod() {
        const name  = this._podNameInput?.value.trim()
        const port  = parseInt(this._podPortInput?.value, 10)
        const pass  = this._podPassInput?.value.trim()
        const image = this._podImageInput?.value.trim() || FIREFOX_IMAGE

        if (!name)      { this._setPodCreateStatus('Name is required.'); return }
        if (!port || port < 1025 || port > 65535)
                        { this._setPodCreateStatus('Port must be 1025–65535.'); return }

        this._podLaunchBtn.disabled = true
        this._setPodCreateStatus('Launching…')

        const env = {}
        if (pass) env['VNC_PASSWORD'] = pass

        try {
            await apiClient.post(`/api/nodes/${this._stack.node_id}/pods`, {
                name,
                image,
                ports:   { [FIREFOX_INNER_PORT]: String(port) },
                env,
                type_id: 'firefox',
            })
            this._setPodCreateStatus(`✓ Pod "${name}" started on port ${port}.`)
            this._podNameInput.value = ''
            this._podPassInput.value = ''
            await this._loadPods()
        } catch (err) {
            this._setPodCreateStatus(`✗ Failed: ${err.message}`)
        } finally {
            this._podLaunchBtn.disabled = false
        }
    }

    _suggestNextPort(pods) {
        const used = pods.map(p => this._hostPortFor(p)).filter(Boolean).map(Number)
        let next = DEFAULT_HOST_PORT
        while (used.includes(next)) next++
        if (this._podPortInput && !this._podPortInput.value) this._podPortInput.value = next
        if (this._podNameInput && !this._podNameInput.value) {
            const idx = used.length + 1
            this._podNameInput.value = `firefox-${idx + 1}`
        }
    }

    _hostPortFor(pod) {
        const binding = pod.ports?.[FIREFOX_INNER_PORT]
        if (Array.isArray(binding)) return binding[0]?.HostPort || ''
        if (typeof binding === 'string') return binding
        return ''
    }

    _setPodsStatus(msg)      { if (this._podsStatus)     this._podsStatus.textContent     = msg }
    _setPodCreateStatus(msg) { if (this._podCreateStatus) this._podCreateStatus.textContent = msg }
}

customElements.define('sg-compute-firefox-detail', SgComputeFirefoxDetail)
