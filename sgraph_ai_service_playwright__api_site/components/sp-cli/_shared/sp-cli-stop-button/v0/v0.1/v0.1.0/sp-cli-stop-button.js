import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliStopButton extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-stop-button' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._stack    = null
        this._stopRow  = this.$('.stop-row')
        this._cnfRow   = this.$('.confirm-row')
        this._cnfLabel = this.$('.confirm-label')
        this._stopBtn  = this.$('.btn-stop')
        this._cnfBtn   = this.$('.btn-confirm')
        this._cancelBtn = this.$('.btn-cancel')

        this._stopBtn  ?.addEventListener('click', () => this._askConfirm())
        this._cnfBtn   ?.addEventListener('click', () => this._doStop())
        this._cancelBtn?.addEventListener('click', () => this._resetConfirm())
    }

    setStack(stack) {
        this._stack = stack
        this._resetConfirm()
        if (this._stopBtn) {
            const stopped = ['stopped', 'terminated', 'failed'].includes((stack?.state || '').toLowerCase())
            this._stopBtn.disabled = stopped
        }
    }

    _askConfirm() {
        if (this._stopRow) this._stopRow.hidden = true
        if (this._cnfRow)  this._cnfRow.hidden  = false
        if (this._cnfLabel) this._cnfLabel.textContent = `Stop ${this._stack?.stack_name}?`
    }

    _resetConfirm() {
        if (this._stopRow) this._stopRow.hidden = false
        if (this._cnfRow)  this._cnfRow.hidden  = true
    }

    _doStop() {
        if (!this._stack) return
        if (this._cnfBtn) this._cnfBtn.disabled = true
        document.dispatchEvent(new CustomEvent('sp-cli:stack.stop-requested', {
            detail:  { stack: this._stack },
            bubbles: true, composed: true,
        }))
        this._resetConfirm()
        if (this._stopBtn) this._stopBtn.disabled = true
    }
}

customElements.define('sp-cli-stop-button', SpCliStopButton)
