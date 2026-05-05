# T1.5 — `Pod__Manager` reads per-node key, not single env var

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.1-T1.4, T1.6).

## What's wrong

`Pod__Manager._sidecar_client` reads the sidecar API key from env `SG_COMPUTE__SIDECAR__API_KEY` — a **single global key shared across all Nodes**. After T1.3 + T1.4 ship per-Node random keys (recommended), this lookup will return the WRONG key. **Every Pods-tab call will 401 in production.**

The frontend code review caught this as a likely-imminent-failure that no test exercises today (only env-var fixture passes).

## Why it matters

- Without the fix, FV2.7 silently breaks the moment T1.3/T1.4 land.
- The architectural intent (per `architecture/03__sidecar-contract.md`) is per-Node keys; `Pod__Manager` is the only consumer that doesn't honour that.

## Tasks

1. **Refactor `Pod__Manager._sidecar_client`** — drop the env-var read. Take the `Node` object (or `node_id`) as input; look up the per-Node key from SSM (or vault — see T1.3) using `Schema__Node__Info.host_api_key_ssm_path`.
2. **Cache lookups** — per-call SSM reads are slow. Cache by `node_id` for the request's lifetime, not longer (so a key rotation doesn't get stale).
3. **Negative-path test** — `Pod__Manager.list_pods('node_with_known_key')` succeeds; `Pod__Manager.list_pods('node_with_wrong_key_in_ssm')` returns 401-equivalent.
4. **Live integration test** — launch a real Node; call `GET /api/nodes/{id}/pods/list` via the control plane; assert 200 (proves the per-Node key flows end-to-end through the proxy).

## Acceptance criteria

- `grep "SG_COMPUTE__SIDECAR__API_KEY" sg_compute/` returns zero hits in `Pod__Manager` (env var may stay for local dev defaults — comment why).
- `Pod__Manager` constructor (or `setup`) takes a `Platform` reference; uses `platform.get_node(node_id).host_api_key_ssm_path` (or vault path) to fetch the key per-call.
- Integration test: control-plane → Pod__Manager → sidecar round-trip succeeds.
- Negative-path test: wrong key → 401.

## "Stop and surface" check

If you find yourself thinking _"SSM read is slow, I'll just use the env var"_: **STOP**. The env var only works if all Nodes share a key, which is exactly the security failure we're fixing. Cache the lookup per request lifetime; surface to Architect if perf is a real concern (it shouldn't be for this scale).

## Live smoke test

Launch two Nodes via `POST /api/nodes` (auth'd). Each gets its own SSM-stored key. `GET /api/nodes/node-A/pods/list` → 200. `GET /api/nodes/node-B/pods/list` → 200. Then manually overwrite Node-A's SSM key with garbage; the next list call returns 5xx (because the proxy gets a 401 from the sidecar) — proves per-Node lookup is real.

## Source

Executive review T1.5; frontend-late review §"FV2.7 integration concern HIGH".
