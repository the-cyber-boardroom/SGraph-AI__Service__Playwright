# FV2.7 — Pods tab via unified `/api/nodes/{id}/pods/*` URL

## Goal

Today the dashboard's Pods tab (`sp-cli-nodes-view`) talks directly to the sidecar (`{host_api_url}/pods/list`). Once BV2.3 ships `Pod__Manager` + `Routes__Compute__Pods`, the dashboard can talk to the **control plane** instead — `/api/nodes/{node_id}/pods/list`. This unifies the URL shape and reduces direct sidecar dependency for non-iframe operations.

## Tasks

1. **In `sp-cli-nodes-view.js`** Pods tab — replace direct sidecar calls:
   - `${host_api_url}/pods/list` → `/api/nodes/{node_id}/pods/list`
   - `${host_api_url}/pods/{name}` → `/api/nodes/{node_id}/pods/{name}`
   - `${host_api_url}/pods/{name}/logs?tail=100` → `/api/nodes/{node_id}/pods/{name}/logs?tail=100`
   - `${host_api_url}/pods/{name}/stats` → `/api/nodes/{node_id}/pods/{name}/stats`
2. **Iframe-based operations stay direct** — Terminal tab and Host API tab still use `{host_api_url}/host/shell/page` and `{host_api_url}/docs-auth?...`. The iframe pattern requires same-origin auth cookie; that doesn't change.
3. **Smoke test** — Pods tab works against a running node. Logs / stats / start / stop all functional.
4. Update reality doc / PR description.

## Acceptance criteria

- Pods tab calls the control plane (`/api/nodes/{id}/pods/...`), not the sidecar directly.
- Iframe tabs (Terminal, Host API) still go direct.
- Smoke test passes.
- Snapshot tests updated.

## Open questions

- **Performance.** Adding the control plane as a hop slightly increases latency for each pod call. For interactive usage (logs, stats) this should be tolerable; if it isn't, fallback path is a query param on `/pods/list?direct=true` for power users — but defer that until measured.

## Blocks / Blocked by

- **Blocks:** FV2.8 (no `/containers/*` URLs).
- **Blocked by:** BV2.3 (`Pod__Manager` + `Routes__Compute__Pods`).

## Notes

After this lands, the dashboard's only direct-sidecar surface is the iframe pattern. Everything else goes through the control plane — clean separation of concerns.
