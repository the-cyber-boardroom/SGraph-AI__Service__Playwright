import { SgComponent  } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { currentVault } from '../../../../../../../shared/vault-bus.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href

const QUICK_COMMANDS = [
    { label: 'List containers',          cmd: 'docker ps'                   },
    { label: 'Container logs (control)', cmd: 'docker logs sp-host-control' },
    { label: 'Docker stats',             cmd: 'docker stats --no-stream'    },
    { label: 'Disk usage',               cmd: 'df -h'                       },
    { label: 'Memory',                   cmd: 'free -m'                     },
    { label: 'Uptime',                   cmd: 'uptime'                      },
    { label: 'Kernel version',           cmd: 'uname -r'                    },
    { label: 'CPU info',                 cmd: 'cat /proc/cpuinfo'           },
    { label: 'Memory info',              cmd: 'cat /proc/meminfo'           },
]

class SpCliHostShell extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-shell' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._unavailable  = this.$('.shell-unavailable')
        this._panel        = this.$('.shell-panel')
        this._iframe       = this.$('.shell-iframe')
        this._select       = this.$('.cmd-select')
        this._output       = this.$('.shell-output')
        this._status       = this.$('.shell-status')
        this._quickBody    = this.$('.quick-body')
        this._quickToggle  = this.$('.btn-quick-toggle')

        this.$('.btn-auth')        ?.addEventListener('click', () => this._openAuth())
        this.$('.btn-run')         ?.addEventListener('click', () => this._run())
        this.$('.btn-clear')       ?.addEventListener('click', () => { if (this._output) this._output.innerHTML = '' })
        this._quickToggle          ?.addEventListener('click', () => this._toggleQuick())

        for (const { label, cmd } of QUICK_COMMANDS) {
            const opt = document.createElement('option')
            opt.value = cmd; opt.textContent = label
            this._select?.appendChild(opt)
        }

        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._unavailable) { this._pendingStack = stack; return }
        this._hostUrl    = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
        this._hostApiKey = stack.host_api_key || ''

        if (this._hostUrl) {
            if (!this._hostApiKey) {
                const vaultPath = stack.host_api_key_vault_path || `/ec2/${stack.stack_name}/host-api-key`
                const vault = currentVault()
                if (vault && vaultPath) vault.read(vaultPath).then(k => { this._hostApiKey = k || '' })
            }
            this._unavailable.classList.add('hidden')
            this._panel.classList.remove('hidden')
            // Point iframe at the sidecar-served shell page (same-origin → cookie auth works for WS)
            if (this._iframe) this._iframe.src = `${this._hostUrl}/host/shell/page`
        } else {
            this._unavailable.classList.remove('hidden')
            this._panel.classList.add('hidden')
            if (this._iframe) this._iframe.src = 'about:blank'
        }
    }

    _openAuth() {
        if (!this._hostUrl || !this._iframe) return
        this._iframe.src = `${this._hostUrl}/auth/set-cookie-form`  // load inline; form auto-returns to /host/shell/page on success
    }

    _toggleQuick() {
        const expanded = !this._quickBody?.classList.contains('hidden')
        if (expanded) {
            this._quickBody?.classList.add('hidden')
            if (this._quickToggle) this._quickToggle.textContent = '▶ Quick Commands'
        } else {
            this._quickBody?.classList.remove('hidden')
            if (this._quickToggle) this._quickToggle.textContent = '▼ Quick Commands'
        }
    }

    async _run() {
        const cmd = this._select?.value
        if (!cmd || !this._hostUrl) return
        if (this._status) this._status.textContent = 'running…'
        try {
            const resp = await fetch(`${this._hostUrl}/host/shell/execute`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Key': this._hostApiKey },
                body:    JSON.stringify({ command: cmd, timeout: 30 }),
            })
            if (resp.status === 401) {
                this._appendOutput(cmd, 'Authentication failed — host API key may have changed.', false)
                if (this._status) this._status.textContent = '401'
                return
            }
            if (resp.status === 422) {
                const err = await resp.json().catch(() => ({}))
                this._appendOutput(cmd, `Command not allowed: ${JSON.stringify(err.detail || err)}`, false)
                if (this._status) this._status.textContent = '422'
                return
            }
            const data = await resp.json()
            this._appendOutput(cmd, (data.stdout || '') + (data.stderr || ''), resp.ok)
            if (this._status) this._status.textContent = resp.ok ? `exit ${data.exit_code}` : `HTTP ${resp.status}`
        } catch (err) {
            this._appendOutput(cmd, `Host unreachable (${this._hostUrl}): ${err.message}`, false)
            if (this._status) this._status.textContent = 'error'
        }
    }

    _appendOutput(cmd, text, ok) {
        if (!this._output) return
        const block = document.createElement('div')
        block.className = `output-block${ok ? '' : ' output-error'}`
        block.innerHTML = `<span class="output-prompt">$ ${_esc(cmd)}</span><pre class="output-text">${_esc(text || '(no output)')}</pre>`
        this._output.appendChild(block)
        this._output.scrollTop = this._output.scrollHeight
    }
}

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

customElements.define('sp-cli-host-shell', SpCliHostShell)
