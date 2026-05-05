import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '../../../../sg-compute-status-chip/v0/v0.1/v0.1.0/sg-compute-status-chip.js'

const TYPE_ICONS = {
    docker: '🐳', podman: '🦭', elastic: '🔍', vnc: '🖥',
    prometheus: '📊', opensearch: '🌐', neko: '🌐', firefox: '🦊', playwright: '🎯',
}

class SgComputeStackHeader extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-stack-header' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._iconEl    = this.$('.hdr-icon')
        this._nameEl    = this.$('.hdr-name')
        this._chipEl    = this.$('sg-compute-status-chip')
        this._uptimeEl  = this.$('.hdr-uptime')
        this._metaEl    = this.$('.hdr-meta')
        this._stopEl    = this.$('.hdr-autostop')
        this._interval  = null
        this._stack     = null
        if (this._pendingStack) { this.setStack(this._pendingStack); this._pendingStack = null }
    }

    setStack(stack) {
        if (!this._iconEl) { this._pendingStack = stack; return }
        this._stack = stack
        this._render()
        clearInterval(this._interval)
        this._interval = setInterval(() => this._updateUptime(), 10_000)
    }

    disconnectedCallback() {
        super.disconnectedCallback?.()
        clearInterval(this._interval)
    }

    _render() {
        const s = this._stack
        if (!s) return
        if (this._iconEl)   this._iconEl.textContent   = TYPE_ICONS[s.spec_id] || '⬡'
        if (this._nameEl)   this._nameEl.textContent   = s.node_id || '—'
        this._chipEl?.setState(s.state)
        this._updateUptime()
        if (this._metaEl)   this._metaEl.textContent   = [s.instance_type, s.region].filter(Boolean).join(' · ')
        const launched = s.created_at ? new Date(s.created_at).toLocaleString() : '—'
        if (this._stopEl) {
            const hours = s.max_hours ? `Auto-stop in ${_uptimeFromNow(s.created_at, s.max_hours)}` : ''
            this._stopEl.textContent = `Launched: ${launched}${hours ? '  ·  ' + hours : ''}`
        }
    }

    _updateUptime() {
        if (!this._stack || !this._uptimeEl) return
        const secs = this._stack.uptime_seconds || 0
        this._uptimeEl.textContent = _fmtUptime(secs)
    }
}

function _fmtUptime(sec) {
    if (!sec) return '—'
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = sec % 60
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
}

function _uptimeFromNow(createdAt, maxHours) {
    if (!createdAt || !maxHours) return ''
    const startMs  = new Date(createdAt).getTime()
    const endMs    = startMs + maxHours * 3_600_000
    const remaining = Math.max(0, endMs - Date.now()) / 1000
    return _fmtUptime(Math.round(remaining))
}

customElements.define('sg-compute-stack-header', SgComputeStackHeader)
