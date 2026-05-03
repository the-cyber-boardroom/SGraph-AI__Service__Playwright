import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href

class SpCliStopButton extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-stop-button' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._stack     = null
        this._idleWrap  = this.$('.stop-idle')
        this._cnfWrap   = this.$('.confirm-wrap')
        this._cnfName   = this.$('.confirm-name')
        this._stopBtn   = this.$('.btn-stop')
        this._cnfBtn    = this.$('.btn-confirm')
        this._cancelBtn = this.$('.btn-cancel')

        this._stopBtn  ?.addEventListener('click', () => this._askConfirm())
        this._cnfBtn   ?.addEventListener('click', () => this._doStop())
        this._cancelBtn?.addEventListener('click', () => this._resetConfirm())
        if (this._pendingStack) { this.setStack(this._pendingStack); this._pendingStack = null }
    }

    setStack(stack) {
        if (!this._stopBtn) { this._pendingStack = stack; return }
        this._stack = stack
        this._resetConfirm()
        const stopped = ['stopped', 'terminated', 'failed'].includes((stack?.state || '').toLowerCase())
        this._stopBtn.disabled = stopped
    }

    _askConfirm() {
        if (this._idleWrap) this._idleWrap.hidden = true
        if (this._cnfWrap)  this._cnfWrap.hidden  = false
        if (this._cnfName)  this._cnfName.textContent = this._stack?.stack_name || 'this node'
    }

    _resetConfirm() {
        if (this._idleWrap) this._idleWrap.hidden = false
        if (this._cnfWrap)  this._cnfWrap.hidden  = true
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
