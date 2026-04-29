// ── vault-bus.js — page-level vault state management ──────────────────────── //
// Full implementation lands in PR-2. These stubs let PR-1 pages import the    //
// module without errors while the vault layer is still being built.           //

export function startVaultBus()       { /* PR-2 */ }
export function getRestorablePrefill() { return { vaultId: '', endpoint: 'https://send.sgraph.ai', accessToken: '', readKeyBase64Url: '' } }
export function isConnected()          { return false }
export function isWritable()           { return false }
export function currentVault()         { return null }
export function currentSession()       { return null }
export async function vaultReadJson()  { throw new Error('vault-bus: not implemented yet — PR-2') }
export async function vaultWriteJson() { throw new Error('vault-bus: not implemented yet — PR-2') }
