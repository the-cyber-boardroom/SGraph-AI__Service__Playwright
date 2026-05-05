# T2.4 — Real vault writer (BV2.9 shipped a fake-200 stub)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

BV2.9 was supposed to migrate `__cli/vault/` → `sg_compute/vault/` with a real per-Spec vault writer. Reality:

1. **`Vault__Spec__Writer` is a fake-200 stub** — returns a hardcoded receipt; never reads or writes vault.
2. **The endpoint URL is accidentally `/api/vault/vault/spec/...`** (double "vault") — tests bypass the prefix entirely so the bug went undetected.
3. **Routes return raw dicts** instead of `<schema>.json()` — violates the "routes have no logic" rule (which extends to "routes return typed schemas").

## Why it matters

The vault writer is the foundation for every spec that needs to persist secrets (firefox MITM scripts, S3 spec call-log archives, etc.). Shipping a fake-200 stub means downstream consumers will silently appear to work — and silently lose data — until someone notices.

## Tasks

1. **Fix the URL** — `/api/vault/spec/{spec_id}/{node_id}/{handle}`. Trace where the double `/vault/vault/` came from (likely the route's `prefix = '/vault/...'` plus the `Routes__Vault__Spec.tag = 'vault'` plus the FastAPI mount).
2. **Fix the test** — make it hit the actual mounted prefix. The test should use a `TestClient(app)` and the real URL — not call the route handler directly.
3. **Implement the real writer** — `Vault__Spec__Writer.write(spec_id, node_id, handle, content_bytes)`:
   - Validates inputs (capability gate: spec must declare `VAULT_WRITES`).
   - Stores the blob via the existing vault layer.
   - Computes SHA256.
   - Returns `Schema__Vault__Spec__Write__Receipt` with `vault_path`, `bytes_written`, `sha256`, `written_at`.
4. **Routes return `<receipt>.json()`**, not raw dicts. Routes have no logic; pure delegation.
5. **Real round-trip test** — write a 1KB blob via `PUT`, read it back via the metadata `GET`, assert SHA256 matches.

## Acceptance criteria

- URL is `/api/vault/spec/{spec_id}/{node_id}/{handle}` (single `/vault/`).
- `Vault__Spec__Writer.write(...)` actually persists to vault.
- `GET .../metadata` returns the persisted SHA256 + bytes_written.
- Routes return `<schema>.json()` everywhere.
- Round-trip test passes against a real vault.
- No `unittest.mock.patch` in the new tests.

## "Stop and surface" check

If you find the test passes against a fake handler but you're not sure the real route is hit: **STOP**. The URL bug existed precisely because the test bypassed the prefix. Tests must hit the mounted surface.

## Live smoke test

```
curl -X PUT -H "X-API-Key: $KEY" -d "hello" http://localhost:8000/api/vault/spec/firefox/test-node/test-handle
curl -H "X-API-Key: $KEY" http://localhost:8000/api/vault/spec/firefox/test-node/test-handle/metadata
```
Second call returns the SHA256 of "hello".

## Source

Executive review Tier-2; backend-late review §"BV2.9 — top issue".
