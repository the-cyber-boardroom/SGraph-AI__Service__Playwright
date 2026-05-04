import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href

const KNOWN_KEYS = [
    // Auth
    { key: 'sg_api_url',                     label: 'SP CLI API URL',       group: 'Auth',  sensitive: false },
    { key: 'sg_api_key',                      label: 'SP CLI API Key',       group: 'Auth',  sensitive: true  },
    // Nodes
    { key: 'sp-cli:host-api-keys',            label: 'Host API Keys',        group: 'Nodes', sensitive: true,  json: true },
    // App state
    { key: 'sp-cli:settings:v2',              label: 'Settings',             group: 'App',   sensitive: false, json: true },
    { key: 'sp-cli:admin:root-layout:v2',     label: 'Admin Layout',         group: 'App',   sensitive: false, json: true },
    { key: 'sp-cli:user:layout',              label: 'User Layout',          group: 'App',   sensitive: false, json: true },
    // Vault
    { key: 'sp-cli:vault:last-vault-id',      label: 'Vault ID',             group: 'Vault', sensitive: false },
    { key: 'sp-cli:vault:last-endpoint',      label: 'Vault Endpoint',       group: 'Vault', sensitive: false },
    { key: 'sp-cli:vault:last-read-key',      label: 'Vault Read Key',       group: 'Vault', sensitive: true  },
    { key: 'sp-cli:vault:last-access-token',  label: 'Vault Access Token',   group: 'Vault', sensitive: true  },
    { key: 'sp-cli:vault:recents',            label: 'Vault Recents',        group: 'Vault', sensitive: false, json: true },
    { key: 'sg-vault:last-key',               label: 'Vault Picker Key',     group: 'Vault', sensitive: true  },
    { key: 'sg-vault:last-api',               label: 'Vault Picker API',     group: 'Vault', sensitive: false },
]

const KNOWN_SET = new Set(KNOWN_KEYS.map(k => k.key))

const GROUPS = ['Auth', 'Nodes', 'App', 'Vault']

class SpCliStorageViewer extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-storage-viewer' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._groups      = this.$('.sv-groups')
        this._unknownWrap = this.$('.sv-unknown')
        this._unknownRows = this.$('.sv-unknown-rows')
        this._revealed    = new Set()

        this.$('.btn-refresh')?.addEventListener('click', () => this.refresh())
        this.$('.btn-clear-all')?.addEventListener('click', () => this._clearAll())

        this.refresh()

        // re-render when storage changes in another tab
        window.addEventListener('storage', () => this.refresh())
    }

    refresh() {
        this._renderKnown()
        this._renderUnknown()
    }

    _renderKnown() {
        if (!this._groups) return
        this._groups.innerHTML = ''
        for (const group of GROUPS) {
            const keys = KNOWN_KEYS.filter(k => k.group === group)
            const groupEl = document.createElement('div')
            groupEl.className = 'sv-group'
            groupEl.innerHTML = `<div class="sv-group-label">${_esc(group)}</div>`
            for (const def of keys) {
                groupEl.appendChild(this._makeRow(def))
            }
            this._groups.appendChild(groupEl)
        }
    }

    _renderUnknown() {
        if (!this._unknownRows) return
        this._unknownRows.innerHTML = ''
        const unknown = []
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i)
            if (!KNOWN_SET.has(k)) unknown.push(k)
        }
        if (!unknown.length) {
            this._unknownWrap.style.display = 'none'
            return
        }
        this._unknownWrap.style.display = ''
        for (const k of unknown.sort()) {
            this._unknownRows.appendChild(this._makeRow({ key: k, label: k, sensitive: false }))
        }
    }

    _makeRow(def) {
        const raw = localStorage.getItem(def.key)
        const missing = raw === null

        const row = document.createElement('div')
        row.className = 'sv-row'

        const label   = document.createElement('div')
        label.className = 'sv-row-label'
        label.textContent = def.label || def.key

        const keyEl   = document.createElement('div')
        keyEl.className = 'sv-row-key'
        keyEl.textContent = def.key

        const actions = document.createElement('div')
        actions.className = 'sv-row-actions'

        if (def.sensitive && !missing) {
            const eye = document.createElement('button')
            eye.className = 'sv-btn'
            eye.title = 'Toggle reveal'
            eye.textContent = this._revealed.has(def.key) ? '🙈' : '👁'
            eye.addEventListener('click', () => {
                if (this._revealed.has(def.key)) this._revealed.delete(def.key)
                else this._revealed.add(def.key)
                this.refresh()
            })
            actions.appendChild(eye)
        }

        if (!missing) {
            const copy = document.createElement('button')
            copy.className = 'sv-btn'
            copy.title = 'Copy value'
            copy.textContent = '⎘'
            copy.addEventListener('click', () => navigator.clipboard?.writeText(raw))
            actions.appendChild(copy)

            const del = document.createElement('button')
            del.className = 'sv-btn del'
            del.title = 'Delete key'
            del.textContent = '✕'
            del.addEventListener('click', () => {
                localStorage.removeItem(def.key)
                this.refresh()
            })
            actions.appendChild(del)
        }

        const valueWrap = document.createElement('div')
        valueWrap.className = 'sv-value-wrap'

        const valueEl = document.createElement('pre')
        valueEl.className = 'sv-value'

        if (missing) {
            valueEl.classList.add('empty')
            valueEl.textContent = '(not set)'
        } else if (def.sensitive && !this._revealed.has(def.key)) {
            valueEl.classList.add('masked')
            valueEl.textContent = '••••••••••••••••'
        } else {
            valueEl.textContent = _formatValue(raw, def.json)
            if (def.json && !_isPlain(raw)) valueEl.classList.add('json')
        }

        valueWrap.appendChild(valueEl)
        row.appendChild(label)
        row.appendChild(keyEl)
        row.appendChild(actions)
        row.appendChild(valueWrap)
        return row
    }

    _clearAll() {
        const toClear = KNOWN_KEYS.map(k => k.key)
        if (!confirm(`Clear ${toClear.length} sp-cli localStorage keys?`)) return
        for (const k of toClear) localStorage.removeItem(k)
        this._revealed.clear()
        this.refresh()
    }
}

function _formatValue(raw, isJson) {
    if (isJson) {
        try { return JSON.stringify(JSON.parse(raw), null, 2) } catch (_) {}
    }
    if (raw.length > 400) return raw.slice(0, 400) + '\n… (' + raw.length + ' chars total)'
    return raw
}

function _isPlain(raw) {
    try { JSON.parse(raw); return false } catch (_) { return true }
}

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

customElements.define('sp-cli-storage-viewer', SpCliStorageViewer)
