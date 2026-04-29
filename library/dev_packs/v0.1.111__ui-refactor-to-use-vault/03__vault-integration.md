# 03 — Vault Integration

**Status:** PROPOSED
**Read after:** `README.md`, `02__component-architecture.md`
**Audience:** Sonnet implementing the vault layer

---

## What this doc gives you

The full vault integration design. Which paths are read, which are written, by whom. The connection flow. The events bus. The fallback behaviour when vault isn't connected. The exact data shapes living in each vault file.

## What "vault" means here

An SGraph zero-knowledge encrypted vault on `https://send.sgraph.ai`, accessed via a **friendly token** (`word-word-NNNN`) or a pre-derived **read key + vault ID** pair. The vault is a content-addressable encrypted blob store with branch refs, tree objects, and commit objects (git-shaped). Same primitive used by SG/Send, the website, and the rest of the SGraph product family.

For this brief, you don't need to understand the cryptography — `<sg-vault-connect>` and `core/vault-client/` handle it. You need to understand:

- **A vault is a set of named files** keyed by file IDs derived from the read key.
- **Reading** a known path is `await readFileAsJson(vault, fileId)` — fast (~50-100ms), uses CDN cache.
- **Writing** requires a write key and an "access token" (server-side credential). For the MVP, the UI has both (the operator pasted them when connecting). Future versions move writes server-side.
- **The vault is not a database.** No queries, no indexes, no transactions. Reads return whole files. Writes overwrite whole files. Concurrent writes use last-write-wins.

This last point matters: vault paths must be **shaped to be read and written whole**. Don't put 10,000 stack records in one file; do put 50.

## The MVP writer model: UI-only

Per the README, this brief uses **(a) UI-only writer**. The FastAPI doesn't change. This means:

- The UI both reads from and writes to vault.
- Anything the FastAPI is canonical for (the live truth of "what stacks exist", returned by `GET /catalog/stacks`) is fetched from FastAPI on each refresh, **then cached to vault** so the next page-load can render instantly while the fresh fetch happens.
- Anything the UI is canonical for (preferences, activity log of UI-initiated actions) is written directly to vault by the UI.

The follow-up brief (backend-as-vault-writer) makes the FastAPI the canonical writer of the live state. UI doesn't change at that point — it just starts seeing fresher data in the cache.

## The four vault paths

### 1. `sp-cli/preferences.json`

**Owner:** UI (this brief).
**Purpose:** the operator's preferred defaults — region, instance types, recent vaults to show in the picker, theme (when we have one).

```jsonc
// sp-cli/preferences.json
{
    "schema_version": 1,
    "default_region": "eu-west-2",
    "default_instance_types": {
        "linux":   "t3.medium",
        "docker":  "t3.medium",
        "elastic": "t3.medium"
    },
    "default_max_hours": 4,
    "recent_vaults": [
        { "vault_id": "abc123def456", "label": "clear-twig-0823", "last_used": "2026-04-29T01:42:08Z" },
        { "vault_id": "xyz789...",     "label": "storm-crisp-0285", "last_used": "2026-04-26T15:30:00Z" }
    ],
    "ui_settings": {
        "default_landing": "stacks",       // future: which tab opens first
        "show_advanced": false
    }
}
```

**Read on:** every page load (after vault connect).
**Write on:** any preference change (region picker, advanced disclosure toggle, etc.).

### 2. `sp-cli/active-stacks-cache.json`

**Owner:** UI (this brief). Will become FastAPI-owned in the follow-up brief.
**Purpose:** a cached snapshot of `GET /catalog/stacks` — so the page renders instantly on second-load while the fresh fetch happens.

```jsonc
// sp-cli/active-stacks-cache.json
{
    "schema_version": 1,
    "cached_at": "2026-04-29T01:42:08Z",
    "ttl_seconds": 60,
    "source_url": "GET /catalog/stacks",
    "stacks": [
        {
            "type_id":        "linux",
            "stack_name":     "linux-quiet-fermi",
            "state":          "RUNNING",
            "public_ip":      "18.132.60.220",
            "region":         "eu-west-2",
            "instance_id":    "i-0a1b2c3d…",
            "uptime_seconds": 272
        }
    ]
}
```

**Read on:** page load (used as instant render before fresh fetch arrives).
**Write on:** every successful refresh of `GET /catalog/stacks`.
**Stale handling:** the UI always shows cached data immediately if available; once the fresh fetch returns, replaces. If the fresh fetch fails, shows cached with a "stale" indicator and the `cached_at` timestamp.

### 3. `sp-cli/activity-log.json`

**Owner:** UI (this brief). Will become FastAPI-owned later.
**Purpose:** append-only log of actions taken through the UI — launches, stops, errors.

```jsonc
// sp-cli/activity-log.json
{
    "schema_version": 1,
    "entries": [
        {
            "timestamp":  "2026-04-29T01:42:08Z",
            "action":     "ready",
            "stack_type": "linux",
            "stack_name": "linux-quiet-fermi",
            "outcome":    "success",
            "duration_ms": 54000,
            "detail":     "became ready (54s)"
        },
        {
            "timestamp":  "2026-04-29T01:41:14Z",
            "action":     "launch",
            "stack_type": "linux",
            "stack_name": "linux-quiet-fermi",
            "outcome":    "requested",
            "detail":     "requested by ui"
        }
    ],
    "max_entries": 500
}
```

**Read on:** page load (admin only — user page doesn't render the activity log section).
**Write on:** any action — launch requested, launch succeeded, launch failed, stop requested, stop succeeded, stop failed, ready transition observed.
**Truncation:** when `entries` exceeds `max_entries`, oldest are dropped on next write. (This is naive — proper rotation is a follow-up.)

### 4. `sp-cli/catalog-overrides.json`

**Owner:** UI (this brief). Will become FastAPI-owned later.
**Purpose:** team-specific overrides on top of the FastAPI catalog — admins can mark types as "coming soon" even if available, customise descriptions, override default boot times.

```jsonc
// sp-cli/catalog-overrides.json
{
    "schema_version": 1,
    "overrides": {
        "vnc": {
            "available": false,
            "description": "Coming soon — Q2 2026",
            "expected_boot_seconds": 90
        },
        "linux": {
            "default_instance_type": "t3.large"   // team prefers larger default
        }
    }
}
```

**Read on:** page load, before rendering type cards. Merged with the FastAPI catalog.
**Write on:** admin Catalog tab actions (disclosure toggle, edit description, etc.).
**Merge logic:** for each type, the FastAPI catalog entry is the base; any matching key in `overrides` replaces. `null` removes (e.g., `linux.description: null` means use FastAPI's description).

For MVP, the admin Catalog editor UI is **out of scope** — overrides exist as a vault file but there's no UI to edit them yet. Operators can edit the file directly via vault tools if needed. The merge logic is in scope so the file's effects are visible.

---

## How vault paths map to vault files

The vault is path-addressed at the API level — the high-level read/write functions take a path string (`'sp-cli/preferences.json'`) and handle file-ID derivation, encryption, and tree-model bookkeeping internally. **You do not need to derive file IDs by hand** for the write path; the canonical helpers do it.

For reads of well-known paths, the vault-client exposes:

```javascript
import { deriveFileIdForPath } from 'https://dev.tools.sgraph.ai/core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js'

const fileId = await deriveFileIdForPath(vault, 'sp-cli/preferences.json')
const data   = await readFileAsJson(vault, fileId)
```

For writes, the canonical entry point is `writeVaultFile(vault, path, content, options)` from `vault-write/v1.1.1/` — see "Write API" below. It does the path → ID derivation, encrypts the blob, builds the sub-trees, creates the commit, and updates the branch ref. All in one call.

The four well-known sp-cli paths are:

| Path | Reader | Writer |
|---|---|---|
| `sp-cli/preferences.json` | `readFileAsJson` | `writeVaultFile` |
| `sp-cli/active-stacks-cache.json` | `readFileAsJson` | `writeVaultFile` |
| `sp-cli/activity-log.json` | `readFileAsJson` | `writeVaultFile` |
| `sp-cli/catalog-overrides.json` | `readFileAsJson` | `writeVaultFile` |

## Write API — `writeVaultFile`

Verified against `https://dev.tools.sgraph.ai/core/vault-write/v1/v1.1/v1.1.1/sg-vault-write.js`:

```javascript
/**
 * @param {object} vault     - vault handle from openVault(), MUST include keys.readKeyBytes,
 *                             keys.writeKey, AND vault.accessToken (for the server to accept the write)
 * @param {string} filePath  - 'sp-cli/preferences.json'
 * @param {string|Uint8Array} content  - strings are UTF-8 encoded
 * @param {object} [options]
 * @param {string} [options.message]      - commit message; default: `Update ${path}`
 * @param {string} [options.contentType]  - default: guessed from extension; pass 'application/json' for our paths
 * @param {string} [options.branchId]     - default: vault.keys.refFileId
 * @returns {Promise<{ commitId: string, treeId: string, blobId: string }>}
 */
async function writeVaultFile(vault, filePath, content, options = {})
```

**Critical:** writes require **all three** of:

1. `vault.keys.readKeyBytes` — for blob encryption
2. `vault.keys.writeKey` — set by `deriveWriteKeys()` / `deriveWriteKeysFromSimpleToken()`. **NOT** set by the read-only `deriveVaultKeys()`.
3. `vault.accessToken` — server-level credential. The operator pasted this into `<sg-vault-connect>` when connecting.

If any is missing, the write throws. The vault is then *read-only* until the operator reconnects with the access token.

## Read API — `readFileAsJson`

Verified against `vault-client/v1.2.2/`:

```javascript
import {
    deriveFileIdForPath,
    readFileAsJson,
} from 'https://dev.tools.sgraph.ai/core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js'

const fileId = await deriveFileIdForPath(vault, 'sp-cli/preferences.json')
const data   = await readFileAsJson(vault, fileId)   // throws on 404 — catch and treat as null
```

`readFileAsJson` returns the parsed JSON (which we wrote as a JSON.stringify above) or throws if the file doesn't exist. **Always wrap in try/catch** and treat 404-like errors as "not yet written, use defaults".

---

## The events bus and connection flow

The vault state is global to the page. Both pages use the same connection lifecycle.

### Connection flow

```
Page load (admin or user)
  │
  ├─ admin.js / user.js loads
  ├─ Imports of sp-cli-* components register custom elements
  ├─ <sp-cli-top-bar> with vault picker slot renders
  ├─ vault-bus.startVaultBus() runs — listens for vault:connected/disconnected
  │
  ├─ <sp-cli-vault-picker> reads getRestorablePrefill():
  │     vaultId, endpoint, accessToken, readKeyBase64Url
  │
  ├─ If saved state exists → picker renders pre-filled <sg-vault-connect>
  │     form with one-click "Connect" button. Operator clicks Connect.
  │
  ├─ <sg-vault-connect> derives keys + opens session + fires:
  │     document.dispatchEvent('vault:connected', { session, vault, vaultId, ... })
  │
  ├─ vault-bus listens for vault:connected, copies session.accessToken onto
  │   the vault handle, persists state to localStorage
  │
  └─ Else → page renders the dim-everything "Connect a vault" prompt
            (operator pastes a fresh vault key + access token)
```

For MVP, "auto-connect" means **one-click Connect with prefilled fields** — not silent reconnect. Silent reconnect requires re-implementing key derivation in vault-bus, duplicating what `<sg-vault-connect>` does. The one extra click on cold load is a deliberate trade-off; a follow-up brief can address it if it becomes annoying.

### After connection

```
vault:connected fires
  │
  ├─ <sp-cli-vault-picker> updates its display ("Connected to clear-twig-0823")
  │
  ├─ admin.js / user.js listens, runs:
  │   1. await loadCatalog()                        ← merges FastAPI + vault overrides
  │   2. populate type cards with merged catalog
  │   3. render activity log (admin only) from sp-cli/activity-log.json
  │   4. start the active-stacks refresh cycle:
  │      a. read sp-cli/active-stacks-cache.json → render immediately
  │      b. fetch GET /catalog/stacks → render fresh
  │      c. write fresh result back to sp-cli/active-stacks-cache.json
  │      d. setInterval(15_000, repeat from b)
  │
  └─ User can now launch / stop / inspect stacks
```

### On vault disconnect

```
User clicks "Disconnect" in vault picker
  │
  ├─ <sp-cli-vault-picker> calls vault session disconnect
  │   → fires document.dispatchEvent('vault:disconnected')
  │
  ├─ admin.js / user.js listens, runs:
  │   1. clear active-stacks table
  │   2. clear activity log (admin)
  │   3. clear type cards
  │   4. clear localStorage 'sp-cli:vault:last-read-key' (NOT vaultId or endpoint — those stay for "recent vaults")
  │
  ├─ Page re-renders the "Connect a vault" prompt
  └─ Operator can connect a different vault or reconnect
```

### Switching vaults

```
User picks a different vault from the picker dropdown
  │
  ├─ Treated as: disconnect → connect-with-different-key
  ├─ <sp-cli-vault-picker> opens the vault-key form (sg-vault-connect)
  ├─ On successful connect, the cycle starts fresh against the new vault's data
  │
  └─ Note: the live AWS state (visible via FastAPI) is independent of vault.
            Switching vaults switches caches, preferences, activity history.
            The FastAPI's view of "what stacks exist right now" is unchanged.
```

---

## `shared/vault-bus.js` — the glue module

Lives in `sgraph_ai_service_playwright__api_site/shared/vault-bus.js`. **Verified against `vault-client/v1.2.2/`, `vault-write/v1.1.1/`, and `vault-session/v1.0.0/` at brief-drafting time.**

```javascript
/**
 * vault-bus — page-level vault state management.
 *
 * Owns the page's connection to a single SGraph vault. Listens for
 * vault:connected / vault:disconnected events from <sg-vault-connect>,
 * persists enough state to auto-reconnect on page reload (vaultId,
 * readKey-as-base64url, endpoint, accessToken), and exposes simple async
 * helpers for path-based reads/writes.
 *
 * NB: passphrase is never persisted — only the derived readKey bytes.
 * NB: writes require accessToken to be attached to the vault handle.
 */

import {
    deriveFileIdForPath,
    readFileAsJson,
    importReadKey,
} from 'https://dev.tools.sgraph.ai/core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js'

import { writeVaultFile } from 'https://dev.tools.sgraph.ai/core/vault-write/v1/v1.1/v1.1.1/sg-vault-write.js'

const LS_VAULT_ID    = 'sp-cli:vault:last-vault-id'
const LS_READ_KEY    = 'sp-cli:vault:last-read-key'      // base64url of readKeyBytes
const LS_ENDPOINT    = 'sp-cli:vault:last-endpoint'
const LS_ACCESS      = 'sp-cli:vault:last-access-token'  // optional; needed for writes
const LS_RECENTS     = 'sp-cli:vault:recents'

let _vault   = null   // { keys, apiBaseUrl, vaultId, accessToken }
let _session = null   // VaultSession instance (from createSession + open)

/**
 * Bootstrap. Listens for vault:connected / vault:disconnected events
 * (fired by <sg-vault-connect>), persists state, and re-fires the same
 * events on auto-reconnect.
 *
 * NOTE: this is event-listening only. The actual reconnect from saved
 * state requires re-opening a session — for MVP we delegate that to
 * <sp-cli-vault-picker>, which embeds <sg-vault-connect> with prefilled
 * fields when LS state is present, lets the user click Connect, and
 * receives the new vault:connected event. This avoids re-implementing
 * key derivation in vault-bus.
 */
export function startVaultBus() {

    document.addEventListener('vault:connected', (e) => {
        const { vault, session, vaultId, apiBaseUrl, keys } = e.detail
        // Attach accessToken to the vault handle for write operations.
        // sg-vault-connect's session has accessToken; the vault object doesn't by default.
        _vault   = { ...vault, accessToken: session?.accessToken || null }
        _session = session
        _persistConnection({ vaultId, apiBaseUrl, keys, accessToken: _vault.accessToken })
    })

    document.addEventListener('vault:disconnected', () => {
        _vault   = null
        _session = null
        // Clear the secrets but keep vault-id and endpoint for "recents"
        localStorage.removeItem(LS_READ_KEY)
        localStorage.removeItem(LS_ACCESS)
    })
}

/**
 * Restore prefill values for the vault picker from localStorage.
 * Used by <sp-cli-vault-picker> to pre-populate <sg-vault-connect>'s
 * fields when the operator returns to the page.
 */
export function getRestorablePrefill() {
    return {
        vaultId:     localStorage.getItem(LS_VAULT_ID)  || '',
        endpoint:    localStorage.getItem(LS_ENDPOINT)  || 'https://send.sgraph.ai',
        accessToken: localStorage.getItem(LS_ACCESS)    || '',
        // Note: we DO persist the derived readKeyBytes — but reconstructing
        // a usable vault from it requires re-deriving the keys. For MVP,
        // the operator pastes the vault key on each cold load; future
        // versions can auto-reconstruct via importReadKey + manual key build.
        readKeyBase64Url: localStorage.getItem(LS_READ_KEY) || '',
    }
}

function _persistConnection({ vaultId, apiBaseUrl, keys, accessToken }) {
    localStorage.setItem(LS_VAULT_ID, vaultId)
    localStorage.setItem(LS_ENDPOINT, apiBaseUrl)
    if (keys.readKeyBytes) {
        localStorage.setItem(LS_READ_KEY, _bytesToBase64Url(keys.readKeyBytes))
    }
    if (accessToken) {
        localStorage.setItem(LS_ACCESS, accessToken)
    }
    _addToRecents(vaultId, apiBaseUrl)
}

// ── Public API for components ────────────────────────────────────────────────

export function isConnected()  { return _vault   !== null }
export function isWritable()   { return _vault?.accessToken && _vault?.keys?.writeKey }
export function currentVault() { return _vault }
export function currentSession() { return _session }

/**
 * Read a JSON file at a known sp-cli path. Returns null if not found.
 * Dispatches sp-cli:vault-bus:* trace events at each step.
 *
 * @param {string} path — e.g. 'sp-cli/preferences.json'
 * @returns {Promise<object|null>}
 */
export async function vaultReadJson(path) {
    if (!_vault) throw new Error('vault-bus: not connected')
    const traceId = _nextTraceId()
    const start   = performance.now()

    _trace('read-started', { traceId, path, vaultId: _vault.vaultId })

    try {
        const fileId = await deriveFileIdForPath(_vault, path)
        _trace('read-derived-id', { traceId, path, fileId })

        const data = await readFileAsJson(_vault, fileId)
        const ms   = Math.round(performance.now() - start)
        const bytes = JSON.stringify(data).length
        _trace('read-completed', { traceId, path, fileId, bytes, durationMs: ms })
        return data
    } catch (err) {
        const ms = Math.round(performance.now() - start)
        if (_isNotFound(err)) {
            _trace('read-not-found', { traceId, path, durationMs: ms })
            return null
        }
        _trace('read-error', { traceId, path, error: err.message, durationMs: ms })
        throw err
    }
}

/**
 * Write a JSON file at a known sp-cli path. Requires writable vault
 * (accessToken + writeKey must be present). Throws if read-only.
 * Dispatches sp-cli:vault-bus:* trace events at each step.
 *
 * @param {string} path — e.g. 'sp-cli/preferences.json'
 * @param {object} data — will be JSON.stringify'd
 * @param {object} [options]
 * @param {string} [options.message]      — commit message; defaults to "Update {path}"
 * @returns {Promise<{ commitId: string, treeId: string, blobId: string }>}
 */
export async function vaultWriteJson(path, data, options = {}) {
    if (!_vault) throw new Error('vault-bus: not connected')
    if (!isWritable()) {
        const err = new Error('vault-bus: vault is read-only (no writeKey or no accessToken — reconnect with a write-capable token)')
        _trace('write-error', { path, error: err.message, reason: 'read-only' })
        throw err
    }
    const traceId = _nextTraceId()
    const start   = performance.now()
    const json    = JSON.stringify(data, null, 2)
    const bytes   = json.length

    _trace('write-started', { traceId, path, bytes, vaultId: _vault.vaultId })

    try {
        const result = await writeVaultFile(
            _vault, path, json,
            {
                contentType: 'application/json',
                message:     options.message || `Update ${path}`,
            }
        )
        const ms = Math.round(performance.now() - start)
        _trace('write-completed', {
            traceId, path, bytes,
            commitId: result.commitId,
            blobId:   result.blobId,
            durationMs: ms,
        })
        return result
    } catch (err) {
        const ms = Math.round(performance.now() - start)
        _trace('write-error', { traceId, path, error: err.message, durationMs: ms })
        throw err
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

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

function _addToRecents(vaultId, apiBaseUrl) {
    const raw = localStorage.getItem(LS_RECENTS)
    const list = raw ? JSON.parse(raw) : []
    const filtered = list.filter(e => e.vault_id !== vaultId)
    filtered.unshift({ vault_id: vaultId, endpoint: apiBaseUrl, last_used: new Date().toISOString() })
    localStorage.setItem(LS_RECENTS, JSON.stringify(filtered.slice(0, 10)))
}
```

**Three design choices worth flagging here:**

1. **Auto-reconnect is delegated to `<sp-cli-vault-picker>`, not `vault-bus.js`.** Reconstructing a usable vault from a stored `readKeyBytes` requires walking through key import + key derivation + session creation — duplicating what `<sg-vault-connect>` already does. For MVP, vault-bus stores the vault ID + endpoint + access token to *prefill* the picker's connect form on page reload; the operator clicks Connect to actually reconnect. That's one click per cold load. A follow-up brief can implement headless reconnect if that proves annoying.

2. **The `accessToken` lives on `_vault.accessToken`, not on `_session.accessToken` alone.** `<sg-vault-connect>`'s `vault:connected` event includes `vault` (without accessToken) and `session` (with accessToken). Vault-bus copies `session.accessToken` onto its private vault handle so `writeVaultFile` works. **This is a small but critical detail** — without it, all writes throw "missing access token" errors.

3. **Every read and write dispatches `sp-cli:vault-bus:*` trace events.** This is what powers `<sp-cli-vault-activity>` — see the next section. Without these events the operator-facing trace pane has no data source.

## Vault activity trace events

Every read and write fires a sequence of `sp-cli:vault-bus:*` events on `document`. The `<sp-cli-vault-activity>` component subscribes to all of them and renders a chronological log. Other consumers (debug overlays, integration tests, telemetry) can subscribe too.

### Event vocabulary

| Event | When | Detail |
|---|---|---|
| `sp-cli:vault-bus:read-started`    | `vaultReadJson` called  | `{ traceId, path, vaultId }` |
| `sp-cli:vault-bus:read-derived-id` | After file ID derived   | `{ traceId, path, fileId }` |
| `sp-cli:vault-bus:read-completed`  | After successful read   | `{ traceId, path, fileId, bytes, durationMs }` |
| `sp-cli:vault-bus:read-not-found`  | 404 — treated as null   | `{ traceId, path, durationMs }` |
| `sp-cli:vault-bus:read-error`      | Any other read failure  | `{ traceId, path, error, durationMs }` |
| `sp-cli:vault-bus:write-started`   | `vaultWriteJson` called | `{ traceId, path, bytes, vaultId }` |
| `sp-cli:vault-bus:write-completed` | After successful write  | `{ traceId, path, bytes, commitId, blobId, durationMs }` |
| `sp-cli:vault-bus:write-error`     | Write failure           | `{ traceId, path, error, durationMs, reason? }` |

The `traceId` lets a viewer group related events together (one read pair, one write pair) — useful when rapid concurrent reads/writes interleave.

The events are independent of the `sg-vault-fetch:*` events fired by Tools' embed components. If the page also uses `<sg-vault-fetch>` directly (e.g., for raw file viewing in Settings), both event families fire and the trace component shows both.

### `<sp-cli-vault-activity>` — the operator-facing tracer

Subscribes to:
- `sp-cli:vault-bus:*` (our reads/writes — the primary source)
- `vault:connected`, `vault:disconnected` (connection state)
- Optionally `sg-vault-fetch:*`, `sg-vault-key:*` (when other Tools embed components are used on the page)

Renders a reverse-chronological list with:

- **Icon** per event type (🌐 read-started, ✅ read-completed, ✏ write-started, ✅ write-completed, 🔴 error, etc.)
- **Path** (`sp-cli/preferences.json`) — the data the operator cares about
- **Short fileId** (`obj-cas-imm-a3f4d2…`) — for the operator who knows what to look for
- **Bytes** and **latency** for completion events
- **Error message** prominent for error events
- **Timestamp** (relative: "2s ago" up to a minute, then absolute)

Visual:

```
✏  write-started               sp-cli/activity-log.json · 256B
                                ↑ shows file ID once derived
✅ write-completed             commit abc123de · blobId d4e5f6… · 142ms
🌐 read-started                sp-cli/preferences.json
🌐 read-derived-id             obj-cas-imm-a3f4d2…
✅ read-completed              1.2 KB · 87ms
🔴 read-error                  sp-cli/missing.json
                                404 — treated as null
```

Implementation: ~200 lines of `SgComponent` extending the same pattern as `<sg-vault-trace>`. **Worth promoting to Tools later** as a generic vault-bus tracer once the `sp-cli:vault-bus:*` event vocabulary stabilises.

### Why one bus module instead of N components

The vault state is genuinely global. Every component that needs it would have to walk up to `[data-vault-bus]` and grab the session — that's possible but fragile. A single module-level singleton (`_vault`, `_session`) plus exported async helpers (`vaultReadJson`, `vaultWriteJson`) is cleaner: one source of truth, one place to update if the vault API changes, components consume via simple imports.

This is the same pattern `api-client.js` uses (module-level singleton). The vault bus is the vault's parallel.

---

## How components use the vault

### Reading on connect — example: type cards

```javascript
// admin.js (controller)

import { vaultReadJson } from '../shared/vault-bus.js'
import { apiClient }     from '../shared/api-client.js'

document.addEventListener('vault:connected', async () => {
    // 1. Read overrides from vault (may not exist on first run)
    const overrides = await vaultReadJson('sp-cli/catalog-overrides') || { overrides: {} }

    // 2. Fetch fresh catalog from FastAPI
    const apiCatalog = await apiClient.get('/catalog/types')

    // 3. Merge: API base + vault overrides
    const merged = {
        entries: apiCatalog.entries.map(entry => ({
            ...entry,
            ...(overrides.overrides[entry.type_id] || {}),
        })),
    }

    // 4. Hand to the type-cards container
    renderTypeCards(merged.entries)
})
```

### Writing on action — example: activity log

```javascript
// admin.js (controller) — when a launch is requested

import { vaultReadJson, vaultWriteJson } from '../shared/vault-bus.js'

async function appendActivity(entry) {
    const log = await vaultReadJson('sp-cli/activity-log') || { schema_version: 1, entries: [], max_entries: 500 }
    log.entries.unshift({
        timestamp: new Date().toISOString(),
        ...entry,
    })
    if (log.entries.length > log.max_entries) {
        log.entries = log.entries.slice(0, log.max_entries)
    }
    await vaultWriteJson('sp-cli/activity-log', log)
    document.dispatchEvent(new CustomEvent('sp-cli:activity-updated', { detail: { entries: log.entries } }))
}

document.addEventListener('sp-cli:launch-completed', (e) => {
    appendActivity({
        action:     'ready',
        stack_type: e.detail.type,
        stack_name: e.detail.name,
        outcome:    'success',
        duration_ms: e.detail.duration_ms,
    })
})
```

### Cache-then-fresh — example: active stacks

```javascript
async function refreshStacks(table) {
    // 1. Render cached immediately (instant first paint)
    const cached = await vaultReadJson('sp-cli/active-stacks-cache')
    if (cached && cached.stacks) {
        table.stacks = cached.stacks
        table.dataset.stale = (Date.now() - new Date(cached.cached_at).getTime() > cached.ttl_seconds * 1000)
    }

    // 2. Fresh fetch from FastAPI
    table.loading = true
    try {
        const fresh = await apiClient.get('/catalog/stacks')
        table.stacks = fresh.stacks || []
        table.dataset.stale = false

        // 3. Write back to cache for next time
        await vaultWriteJson('sp-cli/active-stacks-cache', {
            schema_version: 1,
            cached_at:      new Date().toISOString(),
            ttl_seconds:    60,
            source_url:     'GET /catalog/stacks',
            stacks:         fresh.stacks || [],
        })
    } catch (err) {
        // Cache stays visible; mark as stale
        toast(`Could not refresh — using cached data`, 'warning')
    } finally {
        table.loading = false
    }
}
```

---

## Failure modes

| Scenario | Behaviour |
|---|---|
| Vault unreachable on auto-connect | Try once with 5s timeout, then fall back to "Connect a vault" prompt. Don't repeatedly retry — let the operator click reconnect. |
| Vault file doesn't exist (e.g. fresh vault, no preferences yet) | `vaultReadJson` returns `null`. Caller uses sensible defaults. **Never crash on missing files.** |
| Vault write fails (e.g. network blip) | Toast "Couldn't save preferences — retry?" with `[Retry]`. Don't lose the in-memory state. |
| Vault key wrong (decryption fails) | Treated as auth error: clear `sp-cli:vault:last-read-key`, fire `vault:disconnected`, show "Vault key was rejected — reconnect" toast. |
| Two browser tabs writing the same vault file | Last write wins. UI shows the last-written state. Acceptable for MVP — proper conflict resolution is a follow-up. |
| FastAPI returns 401 (X-API-Key invalid) | Independent of vault. Auth panel opens for X-API-Key entry. Vault state unchanged. |
| FastAPI returns the wrong shape (schema mismatch) | Toast "Unexpected response" + log to console. Don't write garbage to the cache. |

The principle: **vault is not the source of truth for live state — FastAPI is.** Vault is a faster alternative path. If anything goes wrong with vault, fall back to FastAPI; if FastAPI is also broken, show cached and tell the user.

---

## What about secrets in vault?

For MVP, **the only "secrets" we'd put in vault are the X-API-Key for the FastAPI** — and we shouldn't, because the vault key is also a secret and chaining secrets adds surface. Keep the X-API-Key in localStorage (`sp-cli:api-key`) for now.

For follow-up briefs:
- The Stripe API key (when billing lands) → vault `sp-cli/secrets/stripe.json`
- AWS credentials for self-managed accounts → vault `sp-cli/secrets/aws/{profile-name}.json`
- Per-user passwords/tokens → vault per-user paths

When that lands, the vault becomes a real secrets manager. Until then, it's data + state, not secrets.

---

## What does NOT live in vault

| State | Where it lives | Why |
|---|---|---|
| The current modal's `open` state | In-memory in the modal component | Per-tab session detail |
| The currently-selected stack in the detail panel | URL fragment (`#stack=linux-quiet-fermi`) | Shareable, bookmarkable |
| The current FastAPI X-API-Key | localStorage (`sp-cli:api-key`) | Independent of vault for now (see above) |
| The progress bar's current % during a launch | In-memory in the wizard component | Transient |
| Toast messages | In-memory in `<sg-toast-host>` | Transient by design |
| Active health-poll cadence | In-memory in the wizard component | Per-launch session detail |

---

## What good looks like

When the vault layer is in:

1. Refresh either page after connecting once → vault picker shows pre-filled connect form with a single Connect button (no need to re-paste vault key); one click reconnects and the page renders cached active stacks instantly, with fresh data appearing within ~500ms.
2. Disconnect the vault → page reverts to "Connect" prompt; no stale data lingers.
3. Switch vaults → previous data clears, new vault's data loads fresh.
4. Open the page on a fresh vault that has never been used → no errors, all sections show empty states, first interaction creates the relevant vault file.
5. Kill the FastAPI → page still renders cached active-stacks list with a "stale" indicator.
6. Kill the vault endpoint → page still works against the FastAPI; a banner says "Vault offline — preferences won't save".
7. Confirm `grep -r "localStorage" sgraph_ai_service_playwright__api_site/` returns hits only with `sp-cli:` or `sg-vault:` prefixes.

If any of those is wrong, the vault integration is not done.
