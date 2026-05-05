import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { apiClient   } from '../../../../../../../shared/api-client.js'

class SgComputeAmiPicker extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-ami-picker' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._select           = this.$('.ami-select')
        this._placeholder      = this.$('.ami-placeholder')
        this._placeholderText  = this.$('.placeholder-text')
        this._placeholderIcon  = this.$('.placeholder-icon')
        this._empty            = this.$('.ami-empty')
        this._specId           = null

        this._select?.addEventListener('change', () => {
            document.dispatchEvent(new CustomEvent('sg-compute:ami.selected', {
                detail: { spec_id: this._specId, ami_id: this.getSelectedAmiId() },
                bubbles: true, composed: true,
            }))
        })
    }

    async setSpecId(specId) {
        this._specId = specId
        this._showLoading()

        try {
            const data = await apiClient.get(`/api/amis?spec_id=${encodeURIComponent(specId)}`)
            this._populateAmis(data?.amis || [])
        } catch (err) {
            this._showError(err.message || 'Failed to load AMI list')
        }
    }

    _populateAmis(amis) {
        if (!amis.length) {
            this._hidePlaceholder()
            if (this._empty) this._empty.hidden = false
            return
        }

        if (this._select) {
            this._select.innerHTML = ''
            const blank = document.createElement('option')
            blank.value = ''
            blank.textContent = '— select an AMI —'
            this._select.appendChild(blank)

            amis.forEach(ami => {
                const opt = document.createElement('option')
                opt.value = ami.ami_id
                const label = ami.name
                    ? `${ami.name} (${ami.ami_id})`
                    : ami.ami_id
                opt.textContent = label
                opt.dataset.createdAt = ami.created_at || ''
                opt.dataset.sizeGb    = ami.size_gb    || ''
                this._select.appendChild(opt)
            })

            this._select.hidden = false
        }

        this._hidePlaceholder()
        if (this._empty) this._empty.hidden = true
    }

    getSelectedAmiId() {
        return this._select?.value || ''
    }

    setDisabled(disabled) {
        if (this._select) this._select.disabled = disabled
    }

    _showLoading() {
        if (this._placeholderIcon) this._placeholderIcon.textContent = '⏳'
        if (this._placeholderText) this._placeholderText.textContent = 'Loading AMIs…'
        if (this._placeholder)     this._placeholder.hidden = false
        if (this._select)          this._select.hidden      = true
        if (this._empty)           this._empty.hidden       = true
    }

    _showError(msg) {
        if (this._placeholderIcon) this._placeholderIcon.textContent = '⚠'
        if (this._placeholderText) this._placeholderText.textContent = `AMI load failed: ${msg}`
        if (this._placeholder)     this._placeholder.hidden = false
    }

    _hidePlaceholder() {
        if (this._placeholder) this._placeholder.hidden = true
    }
}

customElements.define('sg-compute-ami-picker', SgComputeAmiPicker)
