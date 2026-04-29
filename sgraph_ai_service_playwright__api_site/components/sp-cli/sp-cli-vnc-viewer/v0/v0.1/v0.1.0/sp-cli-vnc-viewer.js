/**
 * @deprecated Use <sg-remote-browser provider="vnc"> from _shared/ instead.
 *             Kept for one release. Will be removed in PR-7.
 *
 * sp-cli-vnc-viewer — Embeds a running VNC stack's noVNC viewer (or mitmweb) in an iframe.
 *
 * Usage: create via document.createElement('sp-cli-vnc-viewer'), add to sg-layout via
 * addTabToStack, then call open(stack, password). Uses a timing guard so open() can be
 * called before onReady() fires.
 *
 * States: empty → not-running → cert → auth → ready
 *
 * sessionStorage keys:
 *   vnc:pwd:{stack_name}  — operator password (persists for browser session)
 *   vnc:cert:{stack_name} — flag: user acknowledged cert trust for this stack
 *
 * @module sp-cli-vnc-viewer
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _pwdKey  = (name) => `vnc:pwd:${name}`
const _certKey = (name) => `vnc:cert:${name}`

class SpCliVncViewer extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-vnc-viewer' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._ready      = true
        this._stack      = null
        this._mode       = 'viewer'                                 // 'viewer' | 'mitmweb'

        this._paneEmpty  = this.$('.pane-empty')
        this._paneNotRun = this.$('.pane-not-running')
        this._paneCert   = this.$('.pane-cert')
        this._paneAuth   = this.$('.pane-auth')
        this._paneReady  = this.$('.pane-ready')

        this._nrState    = this.$('.nr-state')
        this._pwdInput   = this.$('.pwd-input')
        this._authError  = this.$('.auth-error')
        this._toolbarName = this.$('.toolbar-stack-name')
        this._frame      = this.$('.viewer-frame')
        this._toggleBtn  = this.$('.btn-toggle')
        this._blankHint  = this.$('.blank-hint')

        this.$('.btn-cert-open')?.addEventListener('click',  () => this._openInTab(this._viewerUrl()))
        this.$('.btn-cert-done')?.addEventListener('click',  () => this._onCertTrusted())
        this.$('.btn-cert-retry')?.addEventListener('click', () => this._openInTab(this._currentUrl()))
        this.$('.btn-unlock')?.addEventListener('click',     () => this._onUnlock())
        this.$('.btn-toggle')?.addEventListener('click',     () => this._toggleMode())
        this.$('.btn-refresh')?.addEventListener('click',    () => this._refresh())
        this.$('.btn-new-tab')?.addEventListener('click',    () => this._openInTab(this._currentUrl()))
        this.$('.btn-copy')?.addEventListener('click',       () => this._copyUrl())
        this._pwdInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter') this._onUnlock() })
        this._frame?.addEventListener('load', () => { if (this._blankHint) this._blankHint.hidden = true })

        if (this._pendingOpen) {
            const { stack, password } = this._pendingOpen
            this._pendingOpen = null
            this._doOpen(stack, password)
        }
    }

    open(stack, password = '') {
        if (!this._ready) { this._pendingOpen = { stack, password }; return }
        this._doOpen(stack, password)
    }

    _doOpen(stack, password) {
        this._stack = stack
        this._mode  = 'viewer'
        const running = (stack.state || '').toLowerCase() === 'running'

        if (!running) {
            this._nrState.textContent = stack.state || 'unknown'
            this._showState('not-running')
            return
        }

        const storedPwd    = sessionStorage.getItem(_pwdKey(stack.stack_name))  || ''
        const certTrusted  = !!sessionStorage.getItem(_certKey(stack.stack_name))
        const effectivePwd = password || storedPwd

        if (effectivePwd) sessionStorage.setItem(_pwdKey(stack.stack_name), effectivePwd)

        if (!certTrusted) { this._showState('cert'); return }
        if (!effectivePwd) { this._showState('auth'); return }
        this._mountViewer(effectivePwd)
    }

    _onCertTrusted() {
        if (!this._stack) return
        sessionStorage.setItem(_certKey(this._stack.stack_name), '1')
        const pwd = sessionStorage.getItem(_pwdKey(this._stack.stack_name))
        if (!pwd) { this._showState('auth') } else { this._mountViewer(pwd) }
    }

    _onUnlock() {
        const pwd = this._pwdInput?.value.trim()
        if (!pwd) return
        this._authError.hidden = true
        sessionStorage.setItem(_pwdKey(this._stack.stack_name), pwd)
        this._mountViewer(pwd)
    }

    async _mountViewer(password) {
        const url = this._viewerUrl()
        this._toolbarName.textContent = this._stack.stack_name
        this._updateToggleLabel()
        this._showState('ready')
        await this._prewarm(url, password)
        this._frame.src  = url
        this._blankHint.hidden = true
        setTimeout(() => {
            try {
                if (!this._frame.contentDocument?.body?.childElementCount) this._blankHint.hidden = false
            } catch (_) {}                                          // cross-origin frame — assume loaded
        }, 5000)
    }

    async _prewarm(url, password) {
        try {
            await fetch(url, {
                credentials: 'include',
                headers: { Authorization: 'Basic ' + btoa(`operator:${password}`) },
            })
        } catch (_) {}                                              // cert-error expected — triggers browser auth cache
    }

    _toggleMode() {
        this._mode = this._mode === 'viewer' ? 'mitmweb' : 'viewer'
        this._updateToggleLabel()
        const pwd = sessionStorage.getItem(_pwdKey(this._stack?.stack_name || ''))
        const url = this._currentUrl()
        this._frame.src = ''
        setTimeout(async () => {
            if (pwd) await this._prewarm(url, pwd)
            this._frame.src = url
        }, 50)
    }

    _updateToggleLabel() {
        if (this._toggleBtn) this._toggleBtn.textContent = this._mode === 'viewer' ? '⇄ Mitmweb' : '⇄ Viewer'
    }

    _refresh() {
        const src = this._frame.src
        this._frame.src = ''
        setTimeout(() => { this._frame.src = src }, 50)
    }

    _openInTab(url) { if (url) window.open(url, '_blank') }

    _copyUrl() {
        const url = this._currentUrl()
        if (url) navigator.clipboard?.writeText(url).catch(() => {})
    }

    _viewerUrl()  { return this._stack?.public_ip ? `https://${this._stack.public_ip}/`         : '' }
    _mitmwebUrl() { return this._stack?.public_ip ? `https://${this._stack.public_ip}/mitmweb/` : '' }
    _currentUrl() { return this._mode === 'viewer' ? this._viewerUrl() : this._mitmwebUrl() }

    _showState(name) {
        const map = { empty: this._paneEmpty, 'not-running': this._paneNotRun,
                      cert: this._paneCert,   auth: this._paneAuth, ready: this._paneReady }
        for (const [key, el] of Object.entries(map)) { if (el) el.hidden = (key !== name) }
    }
}

customElements.define('sp-cli-vnc-viewer', SpCliVncViewer)
