/**
 * sg-compute-storage-view — Storage view placeholder.
 *
 * Full vault browser coming in a follow-up brief.
 *
 * @module sg-compute-storage-view
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { currentVault } from '../../../../../../shared/vault-bus.js'

class SgComputeStorageView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-storage-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._vaultIdEl  = this.$('.vault-id')
        this._endpointEl = this.$('.vault-endpoint')
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
        if (this._vaultIdEl)  this._vaultIdEl.textContent  = v?.vaultId  || '—'
        if (this._endpointEl) this._endpointEl.textContent = v?.apiBaseUrl || '—'
        if (this._browseBtn)  this._browseBtn.hidden        = !v
    }
}

customElements.define('sg-compute-storage-view', SgComputeStorageView)
