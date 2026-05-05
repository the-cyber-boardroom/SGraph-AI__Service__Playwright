import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

// PARTIAL — GET /api/amis not yet available. Picker renders placeholder until backend ships.
class SgComputeAmiPicker extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-ami-picker' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._select      = this.$('.ami-select')
        this._placeholder = this.$('.ami-placeholder')
        this._empty       = this.$('.ami-empty')
        this._specId      = null

        this._select?.addEventListener('change', () => {
            document.dispatchEvent(new CustomEvent('sg-compute:ami.selected', {
                detail: { spec_id: this._specId, ami_id: this.getSelectedAmiId() },
                bubbles: true, composed: true,
            }))
        })
    }

    setSpecId(specId) {
        this._specId = specId
        // GET /api/amis?spec_id={specId} not yet available — stays in placeholder state.
        // When backend ships, fetch here and populate this._select.
    }

    getSelectedAmiId() {
        return this._select?.value || ''
    }

    setDisabled(disabled) {
        if (this._select) this._select.disabled = disabled
    }
}

customElements.define('sg-compute-ami-picker', SgComputeAmiPicker)
