/**
 * sp-cli-vault-activity — live trace of vault reads and writes.
 *
 * Listens for sp-cli:vault-bus:* events and vault:connected/disconnected.
 * Renders a reverse-chronological list showing operation type, path,
 * bytes, latency, and errors.
 *
 * @module sp-cli-vault-activity
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const ICONS = {
    'read-started':    '🌐',
    'read-derived-id': '🔑',
    'read-completed':  '✅',
    'read-not-found':  '🔍',
    'read-error':      '🔴',
    'write-started':   '✏️',
    'write-completed': '✅',
    'write-error':     '🔴',
}

class SpCliVaultActivity extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-vault-activity' }
    get sharedCssPaths() {
        return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css']
    }

    onReady() {
        this._list    = this.$('.entry-list')
        this._paused  = false

        this.$('.btn-clear')?.addEventListener('click', () => {
            this._list.innerHTML = ''
        })

        const BUS_EVENTS = [
            'read-started','read-derived-id','read-completed',
            'read-not-found','read-error',
            'write-started','write-completed','write-error',
        ]
        BUS_EVENTS.forEach(action =>
            document.addEventListener(`sp-cli:vault-bus:${action}`, (e) => this._addEntry(e.detail))
        )
        document.addEventListener('vault:connected',    (e) => this._addEntry({ action: 'vault-connected', vaultId: e.detail?.vaultId, timestamp: Date.now() }))
        document.addEventListener('vault:disconnected', ()  => this._addEntry({ action: 'vault-disconnected', timestamp: Date.now() }))
    }

    _addEntry(detail) {
        const { action, path, fileId, bytes, durationMs, error, vaultId } = detail

        const row  = document.createElement('div')
        row.className = `entry ${action.includes('error') ? 'is-error' : ''}`

        const icon   = ICONS[action] || '⚙️'
        const label  = path || (vaultId ? `vault: ${vaultId.slice(-12)}` : action)
        const sub    = [
            fileId  ? fileId.slice(0, 20) + '…' : null,
            bytes   ? `${bytes}B` : null,
            durationMs != null ? `${durationMs}ms` : null,
            error   ? error : null,
        ].filter(Boolean).join(' · ')

        row.innerHTML = `
            <span class="icon">${icon}</span>
            <span class="body">
                <span class="label">${_esc(label)}</span>
                ${sub ? `<span class="sub">${_esc(sub)}</span>` : ''}
            </span>
            <span class="time">${_relTime(detail.timestamp)}</span>
        `
        this._list.prepend(row)

        if (this._list.children.length > 200) {
            this._list.lastChild?.remove()
        }
    }
}

function _esc(s) { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }
function _relTime(ts) { const s = Math.round((Date.now() - ts) / 1000); return s < 60 ? `${s}s ago` : new Date(ts).toLocaleTimeString() }

customElements.define('sp-cli-vault-activity', SpCliVaultActivity)
