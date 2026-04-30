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
const SS_FILE_PFX = 'vb:fc:'                                        // sessionStorage prefix for file cache

let _vault   = null
let _session = null

export function startVaultBus() {
    document.addEventListener('vault:connected', (e) => {
        const { vault, session, vaultId, apiBaseUrl, keys } = e.detail
        _vault   = { ...vault, accessToken: session?.accessToken || null }
        _session = session
        if (!e.detail.restored) {
            _persistConnection({ vaultId, apiBaseUrl, keys, accessToken: _vault.accessToken })
        }
    })

    document.addEventListener('vault:disconnected', () => {
        _vault   = null
        _session = null
        localStorage.removeItem(LS_READ_KEY)
        localStorage.removeItem(LS_ACCESS)
    })

    // Fire vault:connected immediately from cached credentials so the UI is
    // unblocked instantly. sg-vault-connect still verifies in the background
    // and will overwrite _vault with the freshly-verified object when done.
    _tryFastRestore()
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

        // Session-level cache: fileId is deterministic (path+vault+key), so the
        // response is safe to cache for the lifetime of this browser session.
        const cacheKey = SS_FILE_PFX + fileId
        const cached   = sessionStorage.getItem(cacheKey)
        if (cached) {
            const data = JSON.parse(cached)
            _trace('read-completed', { traceId, path, fileId, bytes: cached.length, durationMs: 0, cached: true })
            return data
        }

        const data  = await readFileAsJson(_vault, fileId)
        const ms    = Math.round(performance.now() - start)
        _trace('read-completed', { traceId, path, fileId, bytes: JSON.stringify(data).length, durationMs: ms })
        try { sessionStorage.setItem(cacheKey, JSON.stringify(data)) } catch (_) {}
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
        // Derive fileId before writing so we can invalidate the session cache.
        const fileId = await deriveFileIdForPath(_vault, path).catch(() => null)
        if (fileId) sessionStorage.removeItem(SS_FILE_PFX + fileId)

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

function _base64UrlToBytes(b64url) {
    try {
        const b64 = b64url.replace(/-/g, '+').replace(/_/g, '/')
        const raw = atob(b64)
        return Uint8Array.from(raw, c => c.charCodeAt(0))
    } catch (_) { return null }
}

// Fire vault:connected from localStorage credentials so the UI shows immediately.
// The real sg-vault-connect will complete its network verification shortly after
// and fire a second vault:connected (with restored=false) that updates _vault.
function _tryFastRestore() {
    const vaultId   = localStorage.getItem(LS_VAULT_ID)
    const apiBase   = localStorage.getItem(LS_ENDPOINT) || 'https://send.sgraph.ai'
    const readKey   = localStorage.getItem(LS_READ_KEY)
    const accessTok = localStorage.getItem(LS_ACCESS) || null
    if (!vaultId || !readKey) return

    const readKeyBytes = _base64UrlToBytes(readKey)
    if (!readKeyBytes) return

    const vault = { vaultId, apiBaseUrl: apiBase, keys: { readKeyBytes } }

    // Defer one tick so the page controller's vault:connected listener is
    // registered before this fires (startVaultBus() is called synchronously
    // before the listener is added in DOMContentLoaded).
    setTimeout(() => {
        document.dispatchEvent(new CustomEvent('vault:connected', {
            detail:  {
                vault, session: { accessToken: accessTok },
                vaultId, apiBaseUrl: apiBase,
                keys: { readKeyBytes },
                restored: true,
            },
            bubbles:  true,
            composed: true,
        }))
    }, 0)
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
