import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const STATE_MAP = {
    running:                { cls: 'state-running',  dot: '●', label: 'Ready'   },
    booting:                { cls: 'state-booting',  dot: '◐', label: 'Booting' },
    pending:                { cls: 'state-booting',  dot: '◐', label: 'Pending' },
    starting:               { cls: 'state-booting',  dot: '◐', label: 'Starting'},
    initializing:           { cls: 'state-booting',  dot: '◐', label: 'Init'    },
    provisioning:           { cls: 'state-booting',  dot: '◐', label: 'Provisioning'},
    creating:               { cls: 'state-booting',  dot: '◐', label: 'Creating'},
    failed:                 { cls: 'state-failed',   dot: '●', label: 'Failed'  },
    error:                  { cls: 'state-failed',   dot: '●', label: 'Error'   },
    terminated_with_errors: { cls: 'state-failed',   dot: '●', label: 'Failed'  },
    stopped:                { cls: 'state-stopped',  dot: '○', label: 'Stopped' },
    terminated:             { cls: 'state-stopped',  dot: '○', label: 'Stopped' },
    stopping:               { cls: 'state-stopped',  dot: '○', label: 'Stopping'},
}

class SpCliStatusChip extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-status-chip' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._dotEl   = this.$('.chip-dot')
        this._labelEl = this.$('.chip-label')
        const initial = this.getAttribute('state')
        if (initial) this.setState(initial)
    }

    setState(state) {
        const key  = (state || '').toLowerCase()
        const info = STATE_MAP[key] || { cls: 'state-unknown', dot: '●', label: state || '—' }
        if (this._dotEl)   this._dotEl.textContent   = info.dot
        if (this._labelEl) this._labelEl.textContent = info.label
        const el = this.shadowRoot?.querySelector('.chip')
        if (el) el.className = `chip ${info.cls}`
    }
}

customElements.define('sp-cli-status-chip', SpCliStatusChip)
