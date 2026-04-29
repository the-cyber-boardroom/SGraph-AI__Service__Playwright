/**
 * sp-cli-launch-modal — Stack launch wizard modal.
 *
 * Call open(entry) where entry is a Schema__Stack__Type__Catalog__Entry object.
 * POSTs to entry.create_endpoint_path via apiClient.
 *
 * Events emitted (on document):
 *   sp-cli:launch-success — { entry, response } — stack accepted by API
 *   sp-cli:launch-error   — { entry, error }    — API or network failure
 *
 * @module sp-cli-launch-modal
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient    } from '../../../../../../shared/api-client.js'

class SpCliLaunchModal extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-launch-modal' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._backdrop  = this.$('.backdrop')
        this._form      = this.$('.modal-form')
        this._titleEl   = this.$('.modal-title')
        this._descEl    = this.$('.modal-desc')
        this._errorEl   = this.$('.error-msg')
        this._btnLaunch = this.$('.btn-launch')
        this._btnLabel  = this.$('.btn-label')
        this._btnSpin   = this.$('.btn-spinner')

        this.$('.btn-close')?.addEventListener('click',  () => this._close())
        this.$('.btn-cancel')?.addEventListener('click', () => this._close())
        this._backdrop.addEventListener('click', (e) => {
            if (e.target === this._backdrop) this._close()
        })
        this._form.addEventListener('submit', (e) => { e.preventDefault(); this._launch() })

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this._close()
        })
    }

    open(entry) {
        this._entry = entry
        this._titleEl.textContent = `Launch ${entry.display_name}`
        this._descEl.textContent  = entry.description || ''

        const itype = this.$('[name="instance_type"]')
        if (itype && entry.default_instance_type) {
            itype.value = entry.default_instance_type
        }

        const maxH = this.$('[name="max_hours"]')
        if (maxH && entry.default_max_hours) {
            maxH.value = String(entry.default_max_hours)
        }

        this._form.reset()
        if (itype) itype.value = entry.default_instance_type || 't3.medium'
        if (maxH)  maxH.value  = String(entry.default_max_hours || 4)

        this._hideError()
        this._setLoading(false)
        this._backdrop.hidden = false
        setTimeout(() => this.$('[name="stack_name"]')?.focus(), 50)
    }

    _close() {
        this._backdrop.hidden = true
        this._entry = null
    }

    async _launch() {
        if (!this._entry || this._btnLaunch.disabled) return

        const stackName    = this.$('[name="stack_name"]')?.value.trim() || ''
        const instanceType = this.$('[name="instance_type"]')?.value || 't3.medium'
        const maxHours     = parseInt(this.$('[name="max_hours"]')?.value || '4', 10)

        const body = {
            stack_name:    stackName,
            instance_type: instanceType,
            max_hours:     maxHours,
            region:        '',
            caller_ip:     '',
        }

        this._setLoading(true)
        this._hideError()

        try {
            const response = await apiClient.post(this._entry.create_endpoint_path, body)
            this._setLoading(false)
            document.dispatchEvent(new CustomEvent('sp-cli:launch-success', {
                detail:  { entry: this._entry, response },
                bubbles: true, composed: true,
            }))
            this._close()
        } catch (err) {
            this._setLoading(false)
            this._showError(err.message || 'Launch failed')
            document.dispatchEvent(new CustomEvent('sp-cli:launch-error', {
                detail:  { entry: this._entry, error: err.message },
                bubbles: true, composed: true,
            }))
        }
    }

    _setLoading(loading) {
        this._btnLaunch.disabled  = loading
        this._btnLabel.hidden     = loading
        this._btnSpin.hidden      = !loading
    }

    _showError(msg) {
        this._errorEl.textContent = msg
        this._errorEl.hidden      = false
    }

    _hideError() {
        this._errorEl.textContent = ''
        this._errorEl.hidden      = true
    }
}

customElements.define('sp-cli-launch-modal', SpCliLaunchModal)
