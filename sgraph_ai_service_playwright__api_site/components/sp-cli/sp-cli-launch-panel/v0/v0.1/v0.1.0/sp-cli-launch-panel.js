import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient  } from '../../../../../../shared/api-client.js'
import { getAllDefaults } from '../../../../../../shared/settings-bus.js'

class SpCliLaunchPanel extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-launch-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._iconEl   = this.$('.header-icon')
        this._titleEl  = this.$('.header-title')
        this._descEl   = this.$('.header-desc')
        this._errorEl  = this.$('.error-msg')
        this._btnLaunch = this.$('.btn-launch')
        this._btnLabel  = this.$('.btn-label')
        this._btnSpin   = this.$('.btn-spinner')
        this._form      = this.$('.the-form')

        this.$('.btn-cancel')?.addEventListener('click', () => this._cancel())
        this._btnLaunch?.addEventListener('click', () => this._launch())

        if (this._pendingEntry) { this.open(this._pendingEntry); this._pendingEntry = null }
    }

    open(entry) {
        if (!this._form) { this._pendingEntry = entry; return }
        this._entry = entry
        if (this._iconEl)  this._iconEl.textContent  = entry.icon || ''
        if (this._titleEl) this._titleEl.textContent = `Launch ${entry.display_name}`
        if (this._descEl)  this._descEl.textContent  = entry.description || ''
        this._hideError()
        this._setLoading(false)
        this._form.populate?.(entry, getAllDefaults())
    }

    _cancel() {
        document.dispatchEvent(new CustomEvent('sp-cli:launch.cancelled', {
            detail: { entry: this._entry }, bubbles: true, composed: true,
        }))
    }

    async _launch() {
        if (!this._entry || this._btnLaunch?.disabled) return
        const values = this._form?.getValues?.() || {}
        if (!values.stack_name) { this._showError('Stack name is required.'); return }

        const body = {
            stack_name:     values.stack_name,
            instance_type:  values.instance_type  || 't3.medium',
            max_hours:      values.max_hours       || 4,
            region:         values.region          || '',
            caller_ip:      '',
            public_ingress: values.public_ingress  ?? false,
        }

        this._setLoading(true)
        this._hideError()

        try {
            const response = await apiClient.post(this._entry.create_endpoint_path, body)
            this._setLoading(false)
            document.dispatchEvent(new CustomEvent('sp-cli:launch.success', {
                detail:  { entry: this._entry, response },
                bubbles: true, composed: true,
            }))
        } catch (err) {
            this._setLoading(false)
            this._showError(err.message || 'Launch failed')
            document.dispatchEvent(new CustomEvent('sp-cli:launch.error', {
                detail:  { entry: this._entry, error: err.message },
                bubbles: true, composed: true,
            }))
        }
    }

    _setLoading(loading) {
        if (this._btnLaunch) this._btnLaunch.disabled = loading
        if (this._btnLabel)  this._btnLabel.hidden     = loading
        if (this._btnSpin)   this._btnSpin.hidden      = !loading
        this._form?.setDisabled?.(loading)
    }

    _showError(msg) {
        if (this._errorEl) { this._errorEl.textContent = msg; this._errorEl.hidden = false }
    }

    _hideError() {
        if (this._errorEl) { this._errorEl.textContent = ''; this._errorEl.hidden = true }
    }
}

customElements.define('sp-cli-launch-panel', SpCliLaunchPanel)
