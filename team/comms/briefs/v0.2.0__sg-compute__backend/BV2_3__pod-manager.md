# BV2.3 — `Pod__Manager` + `Routes__Compute__Pods`

## Goal

The control plane exposes `/api/specs`, `/api/nodes` but has no `/api/nodes/{id}/pods/*` surface. Code review confirmed `Pod__Manager` and `Routes__Compute__Pods` are missing entirely. Frontend's FV2.7 (Pods tab unified URL) blocks on this.

The Pod__Manager bridges the control plane's typed surface to each Node's sidecar API — when the dashboard calls `GET /api/nodes/{node_id}/pods/list` against the control plane, the manager looks up the Node's `public_ip`, derives `host_api_url = http://{public_ip}:19009`, calls the sidecar's `/pods/list`, and returns the response.

## Tasks

1. Create `sg_compute/core/pod/Pod__Manager.py`:
   ```python
   class Pod__Manager(Type_Safe):
       platform: Platform
       
       def list_pods(self, node_id: Safe_Str__Node__Id) -> Schema__Pod__List: ...
       def start_pod(self, node_id: Safe_Str__Node__Id, request: Schema__Pod__Start__Request) -> Schema__Pod__Info: ...
       def get_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Info | None: ...
       def get_pod_logs(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name, tail: int = 100) -> Schema__Pod__Logs__Response: ...
       def stop_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Stop__Response: ...
       def remove_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Stop__Response: ...
   ```
   Each method:
   - Calls `self.platform.get_node(node_id)` to retrieve `public_ip`.
   - Derives `host_api_url`.
   - Reads the sidecar API key from vault (BV2.9 will provide this; until then use the env var path).
   - Calls the sidecar with `httpx` (or whatever HTTP client osbot-utils provides).
   - Wraps the response in the typed schema and returns.
2. Create `sg_compute/control_plane/routes/Routes__Compute__Pods.py`:
   ```
   GET    /api/nodes/{node_id}/pods/list
   POST   /api/nodes/{node_id}/pods
   GET    /api/nodes/{node_id}/pods/{name}
   GET    /api/nodes/{node_id}/pods/{name}/logs
   POST   /api/nodes/{node_id}/pods/{name}/stop
   DELETE /api/nodes/{node_id}/pods/{name}
   ```
   Pure delegation to `Pod__Manager`. **No business logic in routes.** Returns `<schema>.json()`.
3. Mount the route class on `Fast_API__Compute` in `setup_routes()`.
4. Tests under `sg_compute__tests/control_plane/test_Routes__Compute__Pods.py` — **in-memory composition, no mocks.** Use a fake sidecar (a test FastAPI app on a random port, or an in-process callable) to simulate the sidecar response shape.

## Acceptance criteria

- `Pod__Manager` exists, is `Type_Safe`-clean, has full unit-test coverage.
- `Routes__Compute__Pods` mounts and serves all 6 endpoints.
- A round-trip test (control-plane → fake sidecar → control-plane) passes for each endpoint.
- Zero `unittest.mock.patch` in the new test file.
- Reality doc updated.

## Open questions

- **API key sourcing.** Until BV2.9 provides `sg_compute/vault/`, where does `Pod__Manager` get the sidecar key? Recommend: an env-var convention (`SG_COMPUTE__SIDECAR__API_KEY`) for v0.2.x; vault read for v0.3+.

## Blocks / Blocked by

- **Blocks:** FV2.7 (frontend Pods tab against the unified URL).
- **Blocked by:** none strict; can land in parallel with BV2.1 / BV2.2.

## Notes

The unified URL shape (`/api/nodes/{id}/pods/*`) lets the frontend stop talking to sidecar IPs directly for non-iframe operations. Iframe operations (Terminal, Host API tab) continue to talk to the sidecar directly because they need the same-origin auth cookie.
