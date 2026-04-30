/**
 * sg-remote-browser — Generic iframe/VNC/Neko remote browser widget.
 *
 * Promoted from sp-cli-vnc-viewer. Supports providers: vnc | iframe | neko | auto.
 *
 * API: open({ url, auth, provider, stackName })
 *   url       — target URL to embed
 *   auth      — { type: 'basic', user, pass } | null
 *   provider  — explicit provider; falls back to 'provider' attribute, then 'auto'
 *   stackName — for sessionStorage scoping (passwords, cert-trust)
 *
 * States (VNC mode): empty → not-running → cert → auth → ready
 * States (iframe mode): empty → iframe
 * States (neko mode): empty → neko
 * States (auto mode): iframe → (on error) → VNC flow
 *
 * sessionStorage keys:
 *   vnc:pwd:{stackName}  — cached VNC password
 *   vnc:cert:{stackName} — cert-trust flag
 *
 * Events fired:
 *   sg-remote-browser:state.changed { state, provider }
 *   sg-remote-browser:fallback-applied { from, to }
 *
 * @module sg-remote-browser
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _pwdKey  = n => `vnc:pwd:${n}`
const _certKey = n => `vnc:cert:${n}`

class SgRemoteBrowser extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-remote-browser' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._ready     = true
        this._url       = ''
        this._mitmUrl   = ''
        this._auth      = null
        this._stackName = ''
        this._provider  = this.getAttribute('provider') || 'auto'
        this._mode      = 'viewer'                                      // 'viewer' | 'mitmweb'

        this._paneEmpty  = this.$('.pane-empty')
        this._paneNotRun = this.$('.pane-not-running')
        this._paneCert   = this.$('.pane-cert')
        this._paneAuth   = this.$('.pane-auth')
        this._paneReady  = this.$('.pane-ready')
        this._paneIframe = this.$('.pane-iframe')
        this._paneNeko   = this.$('.pane-neko')

        this._nrState    = this.$('.nr-state')
        this._pwdInput   = this.$('.pwd-input')
        this._authError  = this.$('.auth-error')
        this._toolbarName = this.$('.toolbar-stack-name')
        this._vncFrame   = this.$('.vnc-frame')
        this._iframeEl   = this.$('.direct-frame')
        this._toggleBtn  = this.$('.btn-toggle')
        this._blankHint  = this.$('.blank-hint')
        this._blankHintDirect = this.$('.blank-hint-direct')

        this.$('.btn-cert-open')?.addEventListener('click',  () => this._openInTab(this._url))
        this.$('.btn-cert-done')?.addEventListener('click',  () => this._onCertTrusted())
        this.$('.btn-cert-retry')?.addEventListener('click', () => this._openInTab(this._currentVncUrl()))
        this.$('.btn-unlock')?.addEventListener('click',     () => this._onUnlock())
        this._toggleBtn?.addEventListener('click',           () => this._toggleMode())
        this.$('.btn-refresh-vnc')?.addEventListener('click',  () => this._refresh(this._vncFrame))
        this.$('.btn-refresh-direct')?.addEventListener('click', () => this._refresh(this._iframeEl))
        this.$('.btn-new-tab-vnc')?.addEventListener('click',  () => this._openInTab(this._currentVncUrl()))
        this.$('.btn-new-tab-direct')?.addEventListener('click', () => this._openInTab(this._url))
        this.$('.btn-copy-vnc')?.addEventListener('click',   () => this._copyUrl(this._currentVncUrl()))
        this.$('.btn-copy-direct')?.addEventListener('click', () => this._copyUrl(this._url))
        this.$('.btn-switch-vnc')?.addEventListener('click', () => this._switchToVnc())
        this._pwdInput?.addEventListener('keydown', e => { if (e.key === 'Enter') this._onUnlock() })
        this._vncFrame?.addEventListener('load', () => { if (this._blankHint) this._blankHint.hidden = true })
        this._iframeEl?.addEventListener('error', () => this._onIframeError())

        if (this._pendingOpen) {
            const p = this._pendingOpen
            this._pendingOpen = null
            this._doOpen(p)
        }
    }

    open({ url = '', auth = null, provider = null, stackName = '' } = {}) {
        const args = { url, auth, provider: provider || this._provider, stackName }
        if (!this._ready) { this._pendingOpen = args; return }
        this._doOpen(args)
    }

    _doOpen({ url, auth, provider, stackName }) {
        this._url       = url
        this._auth      = auth
        this._stackName = stackName
        this._provider  = provider || this._provider
        this._mitmUrl   = url ? url.replace(/\/?$/, '/mitmweb/') : ''

        if      (this._provider === 'iframe') this._mountDirectIframe()
        else if (this._provider === 'neko')   this._showState('neko')
        else if (this._provider === 'auto')   this._doAuto()
        else                                   this._doVnc()
    }

    // ── VNC mode ─────────────────────────────────────────────────────────── //

    _doVnc() {
        if (!this._url) { this._showState('empty'); return }
        const storedPwd   = sessionStorage.getItem(_pwdKey(this._stackName)) || ''
        const certTrusted = !!sessionStorage.getItem(_certKey(this._stackName))
        const pwd         = this._auth?.pass || storedPwd
        if (pwd) sessionStorage.setItem(_pwdKey(this._stackName), pwd)
        if (!certTrusted) { this._showState('cert'); return }
        if (!pwd)         { this._showState('auth'); return }
        this._mountVncViewer(pwd)
    }

    _onCertTrusted() {
        if (!this._stackName) return
        sessionStorage.setItem(_certKey(this._stackName), '1')
        const pwd = sessionStorage.getItem(_pwdKey(this._stackName))
        if (!pwd) this._showState('auth')
        else      this._mountVncViewer(pwd)
    }

    _onUnlock() {
        const pwd = this._pwdInput?.value.trim()
        if (!pwd) return
        if (this._authError) this._authError.hidden = true
        sessionStorage.setItem(_pwdKey(this._stackName), pwd)
        this._mountVncViewer(pwd)
    }

    async _mountVncViewer(password) {
        const url = this._currentVncUrl()
        if (this._toolbarName) this._toolbarName.textContent = this._stackName || url
        this._updateToggleLabel()
        this._showState('ready')
        this._dispatch('sg-remote-browser:state.changed', { state: 'ready', provider: 'vnc' })
        await this._prewarm(url, password)
        if (this._vncFrame) {
            this._vncFrame.src = url
            if (this._blankHint) this._blankHint.hidden = true
            setTimeout(() => {
                try {
                    if (!this._vncFrame.contentDocument?.body?.childElementCount) {
                        if (this._blankHint) this._blankHint.hidden = false
                    }
                } catch (_) {}
            }, 5000)
        }
    }

    async _prewarm(url, password) {
        if (!url || !password) return
        try {
            await fetch(url, {
                credentials: 'include',
                headers: { Authorization: 'Basic ' + btoa(`operator:${password}`) },
            })
        } catch (_) {}
    }

    _toggleMode() {
        this._mode = this._mode === 'viewer' ? 'mitmweb' : 'viewer'
        this._updateToggleLabel()
        const pwd = sessionStorage.getItem(_pwdKey(this._stackName))
        const url = this._currentVncUrl()
        if (this._vncFrame) this._vncFrame.src = ''
        setTimeout(async () => {
            if (pwd) await this._prewarm(url, pwd)
            if (this._vncFrame) this._vncFrame.src = url
        }, 50)
    }

    _updateToggleLabel() {
        if (this._toggleBtn)
            this._toggleBtn.textContent = this._mode === 'viewer' ? '⇄ Mitmweb' : '⇄ Viewer'
    }

    _currentVncUrl() { return this._mode === 'viewer' ? this._url : this._mitmUrl }

    // ── iframe / auto mode ────────────────────────────────────────────────── //

    _doAuto() {
        this._mountDirectIframe()
        this._dispatch('sg-remote-browser:state.changed', { state: 'iframe', provider: 'auto' })
    }

    _mountDirectIframe() {
        if (!this._url) { this._showState('empty'); return }
        if (this._iframeEl) this._iframeEl.src = this._url
        this._showState('iframe')
        this._dispatch('sg-remote-browser:state.changed', { state: 'iframe', provider: this._provider })
        if (this._blankHintDirect) {
            this._blankHintDirect.hidden = true
            setTimeout(() => {
                try {
                    if (!this._iframeEl?.contentDocument?.body?.childElementCount)
                        if (this._blankHintDirect) this._blankHintDirect.hidden = false
                } catch (_) { /* cross-origin — assume loaded */ }
            }, 5000)
        }
    }

    _onIframeError() {
        this._dispatch('sg-remote-browser:fallback-applied', { from: 'iframe', to: 'vnc' })
        this._provider = 'vnc'
        this._doVnc()
    }

    _switchToVnc() {
        this._dispatch('sg-remote-browser:fallback-applied', { from: 'iframe', to: 'vnc' })
        this._provider = 'vnc'
        this._doVnc()
    }

    // ── Shared helpers ────────────────────────────────────────────────────── //

    _refresh(frame) {
        if (!frame) return
        const src = frame.src
        frame.src = ''
        setTimeout(() => { frame.src = src }, 50)
    }

    _openInTab(url) { if (url) window.open(url, '_blank') }

    _copyUrl(url) {
        if (url) navigator.clipboard?.writeText(url).catch(() => {})
    }

    _dispatch(name, detail) {
        document.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
    }

    _showState(name) {
        const map = {
            empty:        this._paneEmpty,
            'not-running': this._paneNotRun,
            cert:         this._paneCert,
            auth:         this._paneAuth,
            ready:        this._paneReady,
            iframe:       this._paneIframe,
            neko:         this._paneNeko,
        }
        for (const [key, el] of Object.entries(map)) {
            if (el) el.hidden = (key !== name)
        }
    }
}

customElements.define('sg-remote-browser', SgRemoteBrowser)
