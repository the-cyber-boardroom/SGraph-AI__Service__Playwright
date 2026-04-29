/**
 * sp-cli-vault-picker — top-bar vault connection button + dropdown.
 *
 * Embeds <sg-vault-connect> from Tools inside the dropdown panel.
 * Listens for vault:connected / vault:disconnected on document.
 * Shows a read-only amber banner when connected without an access token.
 *
 * Events emitted:
 *   sp-cli:vault-picker-opened
 *   sp-cli:vault-connected     — proxied from vault:connected
 *   sp-cli:vault-disconnected  — proxied from vault:disconnected
 *
 * @module sp-cli-vault-picker
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import 'https://dev.tools.sgraph.ai/components/vault/sg-vault-connect/v0/v0.1/v0.1.3/sg-vault-connect.js'

class SpCliVaultPicker extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()  { return 'sp-cli-vault-picker' }
    get sharedCssPaths() {
        return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css']
    }

    onReady() {
        this._btn        = this.$('.vault-btn')
        this._panel      = this.$('.panel')
        this._connView   = this.$('.connected-view')
        this._connectView= this.$('.connect-view')
        this._labelEl    = this.$('.vault-label')
        this._roWarn     = this.$('.readonly-warn')
        this._insecWarn  = this.$('.insecure-warn')

        if (!window.isSecureContext) {
            this._connectView.hidden = true
            this._insecWarn.hidden   = false
        }

        this._btn.addEventListener('click', () => this._toggle())

        this.$('.btn-disconnect')?.addEventListener('click', () => this._disconnect())

        document.addEventListener('click', (e) => {
            if (!this.contains(e.target) && !this.shadowRoot.contains(e.target)) this._close()
        })

        document.addEventListener('vault:connected',    (e) => this._onConnected(e.detail))
        document.addEventListener('vault:disconnected', ()  => this._onDisconnected())
    }

    _toggle() {
        const hidden = this._panel.hidden
        this._panel.hidden = !hidden
        if (!hidden) return
        this.emit('sp-cli:vault-picker-opened')
    }

    _close() { this._panel.hidden = true }

    _onConnected(detail) {
        const vaultId     = detail.vaultId || ''
        const writable    = !!(detail.session?.accessToken)
        const label       = vaultId.length > 14 ? vaultId.slice(-14) : vaultId

        this._labelEl.textContent = `🗝 ${label}`
        this._connView.hidden    = false
        this._connectView.hidden = true
        this._roWarn.hidden      = writable

        this.$('.connected-vault-id').textContent = vaultId

        this.emit('sp-cli:vault-connected', detail)
    }

    _onDisconnected() {
        this._labelEl.textContent    = 'Connect vault'
        this._connView.hidden        = true
        this._connectView.hidden     = false
        this._roWarn.hidden          = true
        this.emit('sp-cli:vault-disconnected')
    }

    _disconnect() {
        document.dispatchEvent(new CustomEvent('vault:disconnected', { bubbles: true, composed: true }))
        this._close()
    }
}

customElements.define('sp-cli-vault-picker', SpCliVaultPicker)
