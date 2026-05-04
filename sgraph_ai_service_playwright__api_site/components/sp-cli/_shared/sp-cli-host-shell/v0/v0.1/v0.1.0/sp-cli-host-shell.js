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

const XTERM_JS  = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js'
const XTERM_CSS = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css'
const FIT_JS    = 'https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js'

function _loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
        const s = document.createElement('script')
        s.src = src
        s.onload  = resolve
        s.onerror = reject
        document.head.appendChild(s)
    })
}

class SpCliHostShell extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-shell' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._unavailable   = this.$('.shell-unavailable')
        this._panel         = this.$('.shell-panel')
        this._select        = this.$('.cmd-select')
        this._output        = this.$('.shell-output')
        this._status        = this.$('.shell-status')
        this._xtermMount    = this.$('.xterm-mount')
        this._xtermStatus   = this.$('.xterm-status')
        this._quickBody     = this.$('.quick-body')
        this._quickToggle   = this.$('.btn-quick-toggle')

        this._terminal      = null
        this._fitAddon      = null
        this._ws            = null
        this._wsErrored     = false

        this.$('.btn-run')         ?.addEventListener('click', () => this._run())
        this.$('.btn-clear')       ?.addEventListener('click', () => { if (this._output) this._output.innerHTML = '' })
        this.$('.btn-reconnect')   ?.addEventListener('click', () => this._connectTerminal())
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
            this._connectTerminal()
        } else {
            this._unavailable.classList.remove('hidden')
            this._panel.classList.add('hidden')
            this._disconnectWs()
        }
    }

    disconnectedCallback() {
        super.disconnectedCallback?.()
        this._disconnectWs()
        this._terminal?.dispose()
        this._terminal = null
    }

    _disconnectWs() {
        if (this._ws) {
            this._ws.onopen = this._ws.onmessage = this._ws.onerror = this._ws.onclose = null
            try { this._ws.close() } catch (_) {}
            this._ws = null
        }
    }

    async _connectTerminal() {
        if (!this._xtermMount || !this._hostUrl) return

        try {
            await Promise.all([_loadScript(XTERM_JS), _loadScript(FIT_JS)])
        } catch (err) {
            if (this._xtermStatus) this._xtermStatus.textContent = 'Failed to load xterm'
            return
        }

        if (!window.FitAddon) {
            if (this._xtermStatus) this._xtermStatus.textContent = 'xterm not available'
            return
        }

        if (!this.shadowRoot.querySelector('link[data-xterm-css]')) {
            const link = document.createElement('link')
            link.rel = 'stylesheet'
            link.href = XTERM_CSS
            link.dataset.xtermCss = '1'
            this.shadowRoot.insertBefore(link, this.shadowRoot.firstChild)
        }

        if (this._terminal) {
            this._disconnectWs()
            this._terminal.dispose()
            this._terminal = null
        }

        const term = new window.Terminal({ cursorBlink: true, fontSize: 12, theme: { background: '#0d0d1a' } })
        const fit  = new window.FitAddon.FitAddon()
        term.loadAddon(fit)
        term.open(this._xtermMount)
        fit.fit()
        this._terminal = term
        this._fitAddon = fit

        if (this._xtermStatus) this._xtermStatus.textContent = 'Connecting…'
        this._wsErrored = false

        const hostForWs = this._hostUrl.replace(/^https?:\/\//, '')
        const wsUrl = `ws://${hostForWs}/host/shell/stream?api_key=${encodeURIComponent(this._hostApiKey)}`
        const ws = new WebSocket(wsUrl)
        ws.binaryType = 'arraybuffer'
        this._ws = ws

        ws.onopen = () => {
            if (this._xtermStatus) this._xtermStatus.textContent = 'Connected'
            term.write('\r\n\x1b[32m● Connected\x1b[0m\r\n')
        }

        ws.onmessage = (e) => {
            term.write(new Uint8Array(e.data))
        }

        ws.onerror = () => {
            this._wsErrored = true
        }

        ws.onclose = (e) => {
            if (this._xtermStatus) this._xtermStatus.textContent = 'Disconnected'
            term.write('\r\n\x1b[33mSession ended\x1b[0m')
            if (e.code === 1006) {
                term.write('\r\n\x1b[33m⚠ WS auth not yet supported — use Quick Commands below\x1b[0m')
                this._expandQuick()
            }
        }

        term.onData(data => {
            if (ws.readyState === WebSocket.OPEN) ws.send(data)
        })
    }

    _toggleQuick() {
        const expanded = !this._quickBody?.classList.contains('hidden')
        if (expanded) {
            this._quickBody?.classList.add('hidden')
            if (this._quickToggle) this._quickToggle.textContent = '▶ Quick Commands'
        } else {
            this._expandQuick()
        }
    }

    _expandQuick() {
        this._quickBody?.classList.remove('hidden')
        if (this._quickToggle) this._quickToggle.textContent = '▼ Quick Commands'
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
