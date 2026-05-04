# Debrief — Vault paused; settings-bus migrated to localStorage

**date** 02 May 2026
**session** claude/setup-dev-agent-ui-titBw
**commits** see git log (cleanup pass series, 02 May 2026)
**brief** governance decision 5.6 (`team/comms/briefs/v0.1.140__post-fractal-ui__frontend/05__governance-decisions.md`)

---

## What was done

Settings persistence in the Admin Dashboard was moved from vault to `localStorage`.
Three files changed; `vault-bus.js` was left intact (paused, not deleted).

### `shared/settings-bus.js`

- Removed import of `vaultReadJson`, `vaultWriteJson`, `isWritable` from `vault-bus.js`.
- Replaced `vault:connected` / `vault:disconnected` event listeners with a synchronous `_load()` call inside `startSettingsBus()`.
- Settings are now read from `localStorage` key `sp-cli:settings:v2` on page boot and written back on every change. No async, no network round-trip.
- `sp-cli:settings.loaded` fires synchronously on the next tick after `startSettingsBus()` — the dashboard no longer needs to wait for vault to become available before rendering.
- The `_migrate()` function is unchanged — existing vault-persisted preferences (if a user manually copies the JSON) still parse correctly.

### `admin/admin.js`

- Removed `import { startVaultBus }` and the `startVaultBus()` call.
- Removed the `vault:connected → _loadData()` listener. (Data load is triggered at boot and on `sg-auth-saved`; those two paths are sufficient without vault.)
- Trimmed the now-stale inline comment block about the vault-optional boot path.

### `sp-cli-settings-view` (JS + HTML)

- Removed `import { isWritable }` from `vault-bus.js`.
- Removed the `_updateRoBanner()` helper and its call from `_render()`.
- Removed the `vault:disconnected` listener.
- Removed the `<div class="ro-banner">` element from the HTML template. (With localStorage, settings are always writable — the warning is never true.)

---

## Why

The vault integration requires a meaningful refactor before it can be the primary persistence layer for settings:

1. **Coupling is too tight.** `settings-bus.js` was wired directly to `vault:connected` / `vault:disconnected` events, meaning the dashboard behaviour differed unpredictably between vault-attached and vault-absent states. The 04/29 brief assumed vault-required boot; commit `e34c2e6` removed that gate; but the code still mutated its own state on vault events, creating a hidden state machine that was hard to reason about.

2. **Vault is an append-only remote store with crypto overhead.** Using it as the primary settings store for lightweight UI toggles (which change frequently, survive page reload via localStorage anyway, and do not need to be shared across devices for most users) adds latency and dependency on vault availability without proportionate benefit.

3. **The right vault role is sync, not primary.** When vault integration is resumed, the correct architecture is:
   - localStorage is the authoritative settings store (fast, always available, offline-first).
   - On `vault:connected`, the bus can optionally *sync* settings to/from vault — importing vault preferences if they are newer, exporting local changes if vault is writable.
   - This is a one-way "merge on connect" pattern, not a dependency.

---

## What was paused

- `vault-bus.js` — untouched, fully functional. Left in place for future use.
- `sp-cli-vault-picker` / `sp-cli-vault-status` UI components — untouched. They will render and connect correctly if a vault is attached; they just no longer affect settings persistence.
- `sg-auth-panel` / `api-client.js` — unaffected. API key auth via localStorage continues to work identically.

---

## Vault re-integration: what to do when ready

1. After `vault:connected`, call a new `settings-bus.syncFromVault()` function.
2. That function reads `sp-cli/preferences.json` from the vault and *merges* it with the local state (vault wins for fields that differ, unless local is newer — track a `last_modified` timestamp).
3. On each settings write, also write to vault in the background if `isWritable()` — fire-and-forget, do not block the UI.
4. This is the pattern described in governance decision 5.6 ("vault optional") and aligns with `04__vault-write-contract.md` from the backend brief.

---

## Good failure / bad failure classification

**Good failure** — the tight coupling between vault state and settings-bus state was surfaced explicitly and fixed before it caused user-visible bugs. The hard gate was already removed (commit `e34c2e6`), but the residual state machine was still there. Removing it now keeps the dashboard predictable.

**No bad failures** in this slice.
