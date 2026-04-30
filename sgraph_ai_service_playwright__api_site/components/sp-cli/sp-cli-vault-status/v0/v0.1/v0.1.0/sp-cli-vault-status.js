/**
 * sp-cli-vault-status — shows the current vault connection in the right column.
 *
 * @module sp-cli-vault-status
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { currentVault } from '../../../../../../shared/vault-bus.js'

class SpCliVaultStatus extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-vault-status' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._dot        = this.$('.status-dot')
        this._statusText = this.$('.status-text')
        this._vaultId    = this.$('.vault-id')
        this._endpoint   = this.$('.vault-endpoint')
        this._mode       = this.$('.vault-mode')
        this._browseBtn  = this.$('.btn-browse')

        document.addEventListener('vault:connected',    () => this._refresh())
        document.addEventListener('vault:disconnected', () => this._refresh())
        this._refresh()

        this._browseBtn?.addEventListener('click', () => {
            const v = currentVault()
            if (v?.vaultId) window.open(`https://dev.vault.sgraph.ai/en-gb/#${v.vaultId}`, '_blank')
        })
    }

    _refresh() {
        const v = currentVault()
        const connected = !!v

        this._dot.className        = `status-dot ${connected ? 'dot-connected' : 'dot-disconnected'}`
        this._statusText.textContent = connected ? 'Connected' : 'Disconnected'
        this._vaultId.textContent    = v?.vaultId   || '—'
        this._endpoint.textContent   = v?.apiBaseUrl ? v.apiBaseUrl.replace('https://', '') : '—'
        this._mode.textContent       = connected ? (v?.accessToken ? 'read + write' : 'read-only') : '—'
        this._browseBtn.hidden       = !connected
    }
}

customElements.define('sp-cli-vault-status', SpCliVaultStatus)
