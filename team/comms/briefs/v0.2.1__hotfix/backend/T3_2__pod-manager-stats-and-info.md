# T3.2 — `Pod__Manager` finish: `/pods/{name}` and `/pods/{name}/stats`

⚠ **Tier 3 — integration cleanup.** Standalone PR. Frontend pair: see frontend `T3_2__pod-stats-control-plane.md`.

## What's wrong

BV2.3 `Pod__Manager` brief required the full pod surface: list, info, logs, start, stop, remove, **stats**. FV2.7 brief reiterated this. Reality: only `list` and `logs` shipped on the control plane proxy. **Pod stats still hits the sidecar cross-origin from the dashboard** at `:19009` — works, but defeats the FV2.7 purpose ("everything except iframe goes through control plane").

## Tasks

1. **Add `Pod__Manager.get_pod(node_id, pod_name) -> Schema__Pod__Info`** — proxies to the sidecar's `/pods/{name}`.
2. **Add `Pod__Manager.get_pod_stats(node_id, pod_name) -> Schema__Pod__Stats`** — proxies to the sidecar's `/pods/{name}/stats`.
3. **Add the route handlers** in `Routes__Compute__Pods`:
   - `GET /api/nodes/{node_id}/pods/{pod_name}`
   - `GET /api/nodes/{node_id}/pods/{pod_name}/stats`
4. **Tests** — round-trip via in-memory composition, no mocks.
5. **Coordinate with frontend** — once shipped, frontend can stop calling the sidecar directly for stats (the FV2.7 finish phase).

## Acceptance criteria

- Both new endpoints work end-to-end.
- Pure delegation — routes have no logic, return `<schema>.json()`.
- Tests cover both endpoints.
- After ship, frontend can sweep their direct-sidecar calls for stats.

## "Stop and surface" check

If the sidecar's `/pods/{name}/stats` returns a shape that doesn't fit `Schema__Pod__Stats`: **STOP**. Don't bridge with `dict | None` casts — surface the contract divergence.

## Source

Executive review Tier-3; frontend-late review §"FV2.7 integration concern MED".
