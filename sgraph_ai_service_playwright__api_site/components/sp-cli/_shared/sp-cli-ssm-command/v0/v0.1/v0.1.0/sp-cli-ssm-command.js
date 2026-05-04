import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliSsmCommand extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-ssm-command' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._cmdInput = this.$('.ssm-cmd')
        this._copyBtn  = this.$('.btn-copy')
        this._feedback = this.$('.copy-feedback')
        this._copyBtn?.addEventListener('click', () => this._copy())
        if (this._pendingStack) { this.setStack(this._pendingStack); this._pendingStack = null }
    }

    setStack(stack) {
        if (!this._cmdInput) { this._pendingStack = stack; return }
        const id     = stack?.instance_id || stack?.ec2_instance_id || '—'
        const region = stack?.region || 'eu-west-2'
        const cmd    = id !== '—'
            ? `aws ssm start-session --target ${id} --region ${region}`
            : '(instance ID not yet available)'
        this._cmdInput.value = cmd
    }

    async _copy() {
        const cmd = this._cmdInput?.value
        if (!cmd) return
        try {
            await navigator.clipboard.writeText(cmd)
            if (this._feedback) { this._feedback.hidden = false; setTimeout(() => { this._feedback.hidden = true }, 1500) }
        } catch (_) {}
    }
}

customElements.define('sp-cli-ssm-command', SpCliSsmCommand)
