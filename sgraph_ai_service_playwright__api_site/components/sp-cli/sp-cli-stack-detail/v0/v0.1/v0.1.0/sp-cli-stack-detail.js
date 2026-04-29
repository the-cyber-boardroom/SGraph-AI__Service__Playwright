// @deprecated Use <sp-cli-{type_id}-detail> per-plugin components instead.
/**
 * sp-cli-stack-detail — Stack detail pane for the sg-layout right column.
 *
 * Lives inside sg-layout as a tab. Listens to sp-cli:stack-selected and
 * sp-cli:stack-deleted on document. Fetches full detail from
 * GET /{type}/stack/{name} asynchronously. Provides a Delete button with
 * inline confirmation.
 *
 * Events emitted (on document):
 *   sp-cli:stack-deleted — { stack } — delete accepted by API
 *
 * @module sp-cli-stack-detail
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient    } from '../../../../../../shared/api-client.js'

function _fmtUptime(seconds) {
    if (!seconds || seconds <= 0) return '—'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m`
    return `${seconds}s`
}

function _stateClass(state) {
    const s = (state || '').toLowerCase()
    if (s === 'running')                       return 'state-running'
    if (s === 'stopped' || s === 'terminated') return 'state-stopped'
    return 'state-pending'
}

function _fmtLaunchTime(raw) {
    if (!raw) return '—'
    try { return new Date(raw).toLocaleString() } catch (_) { return raw }
}

class SpCliStackDetail extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-stack-detail' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._emptyState  = this.$('.pane-empty')
        this._detail      = this.$('.pane-detail')
        this._typeBadge   = this.$('.type-badge')
        this._nameEl      = this.$('.stack-name')
        this._stateBadge  = this.$('.state-badge')
        this._uptimeEl    = this.$('.uptime')
        this._confirmRow    = this.$('.confirm-row')
        this._btnDelete     = this.$('.btn-delete')
        this._loadingEl     = this.$('.loading-overlay')
        this._vncActions    = this.$('.vnc-actions')
        this._btnOpenViewer = this.$('.btn-open-viewer')

        this.$('.btn-delete')?.addEventListener('click',        () => this._showConfirm())
        this.$('.btn-cancel-delete')?.addEventListener('click', () => this._hideConfirm())
        this.$('.btn-confirm-delete')?.addEventListener('click',() => this._delete())
        this._btnOpenViewer?.addEventListener('click', () => {
            if (!this._stack) return
            document.dispatchEvent(new CustomEvent('sp-cli:vnc-open-viewer', {
                detail: { stack: this._stack }, bubbles: true, composed: true,
            }))
        })

        document.addEventListener('sp-cli:stack-selected', (e) => this.open(e.detail?.stack))
        document.addEventListener('sp-cli:stack-deleted',  ()  => this._showEmpty())
    }

    open(stack) {
        if (!stack) return
        this._stack = stack
        this._hideConfirm()
        this._setLoading(false)

        this._typeBadge.textContent  = stack.type_id
        this._typeBadge.className    = `type-badge type-${stack.type_id}`
        this._nameEl.textContent     = stack.stack_name
        this._stateBadge.textContent = stack.state
        this._stateBadge.className   = `state-badge ${_stateClass(stack.state)}`
        this._uptimeEl.textContent   = _fmtUptime(stack.uptime_seconds)

        this._setField('region',        stack.region      || '—')
        this._setField('public_ip',     stack.public_ip   || '—')
        this._setField('instance_id',   stack.instance_id || '—')
        this._setField('instance_type', '…')
        this._setField('launch_time',   '…')
        this._setField('allowed_ip',    '…')

        const isTerminated = (stack.state || '').toLowerCase() === 'terminated'
        const isVncRunning = stack.type_id === 'vnc' && (stack.state || '').toLowerCase() === 'running'
        this._btnDelete.hidden  = isTerminated
        if (this._vncActions) this._vncActions.hidden = !isVncRunning

        this._emptyState.hidden = true
        this._detail.hidden     = false

        this._fetchDetail(stack)
    }

    _showEmpty() {
        this._stack             = null
        this._emptyState.hidden = false
        this._detail.hidden     = true
    }

    async _fetchDetail(stack) {
        try {
            const info = await apiClient.get(`/${stack.type_id}/stack/${stack.stack_name}`)
            if (!this._stack || this._stack.stack_name !== stack.stack_name) return
            this._setField('instance_type', info.instance_type || '—')
            this._setField('launch_time',   _fmtLaunchTime(info.launch_time))
            this._setField('allowed_ip',    info.allowed_ip || '—')
            if (info.public_ip)       this._setField('public_ip', info.public_ip)
            if (info.uptime_seconds)  this._uptimeEl.textContent = _fmtUptime(info.uptime_seconds)
        } catch (_) {
            this._setField('instance_type', '—')
            this._setField('launch_time',   '—')
            this._setField('allowed_ip',    '—')
        }
    }

    async _delete() {
        if (!this._stack) return
        this._hideConfirm()
        this._setLoading(true)
        try {
            await apiClient.delete(`/${this._stack.type_id}/stack/${this._stack.stack_name}`)
            document.dispatchEvent(new CustomEvent('sp-cli:stack-deleted', {
                detail:  { stack: this._stack },
                bubbles: true, composed: true,
            }))
        } catch (err) {
            this._setLoading(false)
            this._showConfirm()
            console.error('[stack-detail] delete failed:', err.message)
        }
    }

    _showConfirm() {
        this._btnDelete.hidden  = true
        this._confirmRow.hidden = false
    }

    _hideConfirm() {
        this._confirmRow.hidden = true
        const isTerminated = (this._stack?.state || '').toLowerCase() === 'terminated'
        this._btnDelete.hidden = isTerminated
    }

    _setLoading(on) { this._loadingEl.hidden = !on }

    _setField(name, value) {
        const el = this.$(`[data-field="${name}"]`)
        if (el) el.textContent = value
    }
}

customElements.define('sp-cli-stack-detail', SpCliStackDetail)
