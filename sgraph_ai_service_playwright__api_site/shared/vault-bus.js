// ── vault-bus.js — page-level vault state management ──────────────────────── //
// Owns the page's connection to a single SGraph vault. Listens for            //
// vault:connected / vault:disconnected from <sg-vault-connect>, persists      //
// state, and exposes async helpers for path-based reads/writes.               //

import {
    deriveFileIdForPath,
    readFileAsJson,
} from 'https://dev.tools.sgraph.ai/core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js'

import { writeVaultFile } from 'https://dev.tools.sgraph.ai/core/vault-write/v1/v1.1/v1.1.1/sg-vault-write.js'

const LS_VAULT_ID = 'sp-cli:vault:last-vault-id'
const LS_READ_KEY = 'sp-cli:vault:last-read-key'
const LS_ENDPOINT = 'sp-cli:vault:last-endpoint'
const LS_ACCESS   = 'sp-cli:vault:last-access-token'
const LS_RECENTS  = 'sp-cli:vault:recents'

let _vault   = null
let _session = null

export function startVaultBus() {
    document.addEventListener('vault:connected', (e) => {
        const { vault, session, vaultId, apiBaseUrl, keys } = e.detail
        _vault   = { ...vault, accessToken: session?.accessToken || null }
        _session = session
        _persistConnection({ vaultId, apiBaseUrl, keys, accessToken: _vault.accessToken })
    })

    document.addEventListener('vault:disconnected', () => {
        _vault   = null
        _session = null
        localStorage.removeItem(LS_READ_KEY)
        localStorage.removeItem(LS_ACCESS)
    })
}

export function getRestorablePrefill() {
    return {
        vaultId:          localStorage.getItem(LS_VAULT_ID) || '',
        endpoint:         localStorage.getItem(LS_ENDPOINT) || 'https://send.sgraph.ai',
        accessToken:      localStorage.getItem(LS_ACCESS)   || '',
        readKeyBase64Url: localStorage.getItem(LS_READ_KEY) || '',
    }
}

export function isConnected()    { return _vault !== null }
export function isWritable()     { return !!(_vault?.accessToken && _vault?.keys?.writeKey) }
export function currentVault()   { return _vault }
export function currentSession() { return _session }

export async function vaultReadJson(path) {
    if (!_vault) throw new Error('vault-bus: not connected')
    const traceId = _nextTraceId()
    const start   = performance.now()
    _trace('read-started', { traceId, path, vaultId: _vault.vaultId })
    try {
        const fileId = await deriveFileIdForPath(_vault, path)
        _trace('read-derived-id', { traceId, path, fileId })
        const data  = await readFileAsJson(_vault, fileId)
        const ms    = Math.round(performance.now() - start)
        _trace('read-completed', { traceId, path, fileId, bytes: JSON.stringify(data).length, durationMs: ms })
        return data
    } catch (err) {
        const ms = Math.round(performance.now() - start)
        if (_isNotFound(err)) { _trace('read-not-found', { traceId, path, durationMs: ms }); return null }
        _trace('read-error', { traceId, path, error: err.message, durationMs: ms })
        throw err
    }
}

export async function vaultWriteJson(path, data, options = {}) {
    if (!_vault)      throw new Error('vault-bus: not connected')
    if (!isWritable()) {
        const err = new Error('vault-bus: vault is read-only (no writeKey or no accessToken)')
        _trace('write-error', { path, error: err.message, reason: 'read-only' })
        throw err
    }
    const traceId = _nextTraceId()
    const start   = performance.now()
    const json    = JSON.stringify(data, null, 2)
    _trace('write-started', { traceId, path, bytes: json.length, vaultId: _vault.vaultId })
    try {
        const result = await writeVaultFile(
            _vault, path, json,
            { contentType: 'application/json', message: options.message || `Update ${path}` }
        )
        const ms = Math.round(performance.now() - start)
        _trace('write-completed', { traceId, path, bytes: json.length, commitId: result.commitId, blobId: result.blobId, durationMs: ms })
        return result
    } catch (err) {
        const ms = Math.round(performance.now() - start)
        _trace('write-error', { traceId, path, error: err.message, durationMs: ms })
        throw err
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────── //

let _traceCounter = 0
function _nextTraceId() { return `vb-${Date.now().toString(36)}-${(++_traceCounter).toString(36)}` }

function _trace(action, detail) {
    document.dispatchEvent(new CustomEvent(`sp-cli:vault-bus:${action}`, {
        detail:   { ...detail, action, timestamp: Date.now() },
        bubbles:  true,
        composed: true,
    }))
}

function _isNotFound(err) {
    return err?.message?.includes('404') || err?.message?.includes('not found')
}

function _bytesToBase64Url(bytes) {
    const b64 = btoa(String.fromCharCode(...bytes))
    return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

function _persistConnection({ vaultId, apiBaseUrl, keys, accessToken }) {
    try {
        localStorage.setItem(LS_VAULT_ID, vaultId)
        localStorage.setItem(LS_ENDPOINT, apiBaseUrl)
        if (keys?.readKeyBytes) localStorage.setItem(LS_READ_KEY, _bytesToBase64Url(keys.readKeyBytes))
        if (accessToken)        localStorage.setItem(LS_ACCESS, accessToken)
        _addToRecents(vaultId, apiBaseUrl)
    } catch { /* ignore */ }
}

function _addToRecents(vaultId, apiBaseUrl) {
    try {
        const list     = JSON.parse(localStorage.getItem(LS_RECENTS) || '[]')
        const filtered = list.filter(e => e.vault_id !== vaultId)
        filtered.unshift({ vault_id: vaultId, endpoint: apiBaseUrl, last_used: new Date().toISOString() })
        localStorage.setItem(LS_RECENTS, JSON.stringify(filtered.slice(0, 10)))
    } catch { /* ignore */ }
}
