/**
 * sp-cli-events-log — live DOM-event trace for the admin right column.
 *
 * Generalised version of sp-cli-vault-activity: listens for vault-bus
 * trace events, stack lifecycle, launch flow, nav, and plugin events.
 * Supports a filter dropdown (All / Vault / Stacks / Launch / Errors).
 *
 * @module sp-cli-events-log
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const FAMILIES = {
    vault:  ['vault:connected','vault:disconnected',
             'sp-cli:vault-bus:read-started','sp-cli:vault-bus:read-derived-id',
             'sp-cli:vault-bus:read-completed','sp-cli:vault-bus:read-not-found',
             'sp-cli:vault-bus:read-error','sp-cli:vault-bus:write-started',
             'sp-cli:vault-bus:write-completed','sp-cli:vault-bus:write-error'],
    stacks: ['sp-cli:node.selected','sp-cli:node.deleted','sp-cli:node.launched',
             'sp-cli:nodes.refresh',
             'sp-cli:stack.selected','sp-cli:stack.deleted','sp-cli:stack.launched',  // DEPRECATED
             'sp-cli:stacks.refresh','sp-cli:stack-selected','sp-cli:stack-deleted'], // DEPRECATED
    launch: ['sp-cli:launch.success','sp-cli:launch.error','sp-cli:launch-success',
             'sp-cli:launch-error','sp-cli:activity-entry',
             'sp-cli:catalogue.loaded',
             'sp-cli:spec:docker.launch-requested','sp-cli:spec:podman.launch-requested',
             'sp-cli:spec:elastic.launch-requested','sp-cli:spec:vnc.launch-requested',
             'sp-cli:spec:prometheus.launch-requested','sp-cli:spec:opensearch.launch-requested',
             'sp-cli:spec:neko.launch-requested','sp-cli:spec:firefox.launch-requested',
             'sp-cli:plugin:docker.launch-requested','sp-cli:plugin:podman.launch-requested',   // DEPRECATED
             'sp-cli:plugin:elastic.launch-requested','sp-cli:plugin:vnc.launch-requested',     // DEPRECATED
             'sp-cli:plugin:prometheus.launch-requested','sp-cli:plugin:opensearch.launch-requested', // DEPRECATED
             'sp-cli:plugin:neko.launch-requested','sp-cli:plugin:firefox.launch-requested'],   // DEPRECATED
    nav:    ['sp-cli:nav.selected','sp-cli:spec.toggled','sp-cli:plugin.toggled',  // plugin.toggled DEPRECATED
             'sp-cli:settings.loaded','sp-cli:settings.saved','sp-cli:region-changed'],
}

const ICONS = {
    'vault:connected':                    '🗝',
    'vault:disconnected':                 '🔌',
    'sp-cli:vault-bus:read-started':      '🌐',
    'sp-cli:vault-bus:read-derived-id':   '🔑',
    'sp-cli:vault-bus:read-completed':    '✅',
    'sp-cli:vault-bus:read-not-found':    '🔍',
    'sp-cli:vault-bus:read-error':        '🔴',
    'sp-cli:vault-bus:write-started':     '✏️',
    'sp-cli:vault-bus:write-completed':   '✅',
    'sp-cli:vault-bus:write-error':       '🔴',
    'sp-cli:node.selected':               '📋',
    'sp-cli:node.deleted':                '🗑',
    'sp-cli:node.launched':               '🚀',
    'sp-cli:stack.selected':              '📋',  // DEPRECATED
    'sp-cli:stack.deleted':               '🗑',  // DEPRECATED
    'sp-cli:stack.launched':              '🚀',  // DEPRECATED
    'sp-cli:launch.success':              '✅',
    'sp-cli:launch.error':                '🔴',
    'sp-cli:activity-entry':              '📝',
    'sp-cli:nav.selected':                '🧭',
    'sp-cli:plugin.toggled':              '⚙',
    'sp-cli:settings.saved':              '💾',
    'sp-cli:settings.loaded':             '📂',
    'sp-cli:region-changed':              '🌍',
}

const ALL_EVENTS = [...new Set(Object.values(FAMILIES).flat())]

class SpCliEventsLog extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-events-log' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._list   = this.$('.entry-list')
        this._filter = this.$('.filter-select')

        this.$('.btn-clear')?.addEventListener('click', () => { this._list.innerHTML = '' })
        this._filter?.addEventListener('change', () => this._applyFilter())

        ALL_EVENTS.forEach(evt =>
            document.addEventListener(evt, (e) => this._add(evt, e.detail))
        )
    }

    _add(eventName, detail = {}) {
        const family = this._familyOf(eventName)

        const row       = document.createElement('div')
        row.className   = `entry family-${family}${eventName.includes('error') ? ' is-error' : ''}`
        row.dataset.family = family

        const icon  = ICONS[eventName] || '⚙️'
        const label = detail?.path || detail?.message || detail?.view || detail?.vaultId
                   || (detail?.name ? `spec: ${detail.name}` : null)
                   || eventName.split(':').pop()
        const sub   = [
            detail?.fileId  ? detail.fileId.slice(0, 20) + '…' : null,
            detail?.bytes   ? `${detail.bytes}B` : null,
            detail?.durationMs != null ? `${detail.durationMs}ms` : null,
            detail?.error   || null,
            detail?.stack?.node_id || null,
        ].filter(Boolean).join(' · ')

        row.innerHTML = `
            <span class="icon">${icon}</span>
            <span class="body">
                <span class="label">${_esc(label)}</span>
                ${sub ? `<span class="sub">${_esc(sub)}</span>` : ''}
            </span>
            <span class="time">${_relTime(detail?.timestamp || Date.now())}</span>
        `
        this._list.prepend(row)
        if (this._list.children.length > 300) this._list.lastChild?.remove()
        this._applyFilter()
    }

    _applyFilter() {
        const f = this._filter?.value || 'all'
        this._list.querySelectorAll('.entry').forEach(row => {
            row.hidden = f !== 'all' && row.dataset.family !== f
        })
    }

    _familyOf(eventName) {
        for (const [family, events] of Object.entries(FAMILIES)) {
            if (events.includes(eventName)) return family
        }
        return 'nav'
    }
}

function _esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}
function _relTime(ts) {
    const s = Math.round((Date.now() - ts) / 1000)
    return s < 60 ? `${s}s ago` : new Date(ts).toLocaleTimeString()
}

customElements.define('sp-cli-events-log', SpCliEventsLog)
