# T1.4 — `POST /api/nodes` unauthenticated AND launches sidecars with empty key

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.1-T1.3, T1.5, T1.6).

## What's wrong

Two compounding problems:

1. `POST /api/nodes` is unauthenticated (T1.1 fixes this transitively when the base class flips to `Serverless__Fast_API`).
2. The base request schema `Schema__Node__Create__Request__Base` has **no `api_key_value` field**, so `_create_docker_node` (and other spec-create paths) call `Section__Sidecar.render(...)` with **empty string** as the API key. The sidecar starts with `FAST_API__AUTH__API_KEY__VALUE=""` — and the auth middleware accepts empty key as valid (no length check).

## Why it matters

Even after T1.1 lands, an authenticated caller can launch a Node whose sidecar accepts ANY request as authenticated. Empty string is a magic password.

## Tasks

1. **Verify T1.3 first.** Once T1.3 ships SSM-based key generation, the `Section__Sidecar` no longer takes a plaintext key parameter — it takes an SSM path. The empty-key bug evaporates.
2. **Add length / format validation** at the sidecar boot — `Fast_API__Host__Control` (or its `_Middleware`) should refuse to start if `FAST_API__AUTH__API_KEY__VALUE` is empty or shorter than 16 chars. Crash early, fail loud. (This is also part of T1.6.)
3. **Verify `POST /api/nodes` is auth'd** after T1.1 — negative-path test: unauthenticated POST → 401.
4. **Per-node-key contract** — `EC2__Platform.create_node` generates a new key per call; never reuses the env var. The key is written to SSM (T1.3) and never returned to the caller in the response body.
5. **Schema__Node__Info** carries the SSM path (or vault path) for consumers (Pod__Manager — T1.5).

## Acceptance criteria

- `Schema__Node__Create__Request__Base` no longer carries `api_key_value` (it's generated server-side).
- `POST /api/nodes` returns 401 without auth.
- A Node launched via `POST /api/nodes` has a unique sidecar API key (not the env var, not empty).
- Sidecar boot fails loud if API key is empty / too short.
- `Schema__Node__Info` exposes the key location (path), not the key value.

## "Stop and surface" check

If you find yourself reading "the field doesn't exist on the schema → use empty string": **STOP**. That's the exact mistake here. Generate the key server-side; surface to Architect if the design seems unclear.

## Live smoke test

`curl -X POST http://localhost:8000/api/nodes -d '{"spec_id":"docker"}'` (no auth) → 401. With auth header: launch succeeds; the sidecar on the launched Node refuses any unauthenticated request (verify by direct sidecar test).

## Source

Executive review T1.4; backend-early review §"Top 3 security issue".
