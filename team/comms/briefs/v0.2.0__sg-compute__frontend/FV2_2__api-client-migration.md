# FV2.2 — Switch dashboard to `/api/specs` + `/api/nodes`; field renames

## Goal

The dashboard still calls legacy URLs (`/catalog/types`, `/catalog/stacks`, `/{type_id}/stack/...`) and reads legacy field names (`stack_name`, `type_id`, `container_count`). Backend `Fast_API__Compute` is live with `/api/specs` and `/api/nodes`. Switch the dashboard's data source to the new API; rename field consumers.

## Tasks

1. **Add `useLegacyApiBase` toggle** to `shared/settings-bus.js` (default `false`). For one release window, operators can flip back to legacy URLs if a regression is found.
2. **Update `shared/api-client.js`** — accept the toggle; when `false`, prefix calls with `/api/`. Provide a single `apiClient.get('specs')` / `apiClient.get('nodes')` helper.
3. **In `admin/admin.js`** — replace:
   - `apiClient.get('/catalog/types')` → `apiClient.get('/api/specs')`.
   - `apiClient.get('/catalog/stacks${regionParam}')` → `apiClient.get('/api/nodes')`.
   - Per-spec create: `apiClient.post('/{type}/stack', body)` → `apiClient.post('/api/specs/{spec_id}/stack', body)`.
4. **Field renames across consumers** — sweep with grep:
   - `stack.stack_name` → `node.node_id` (or `node.node_name` where applicable — BV2.2 documents `Schema__Node__Info`).
   - `stack.type_id` → `node.spec_id`.
   - `stack.container_count` → `node.pod_count`.
   - Variable names (`mainStackId`, `_mainStackId`, etc.) — leave alone in this phase; FV2.12 may sweep.
   - HTML attributes (`data-stack-id` etc.) — leave alone in this phase.
5. **In `sp-cli-nodes-view.js`** — apply the field renames. Ensure `host_api_url = http://${node.public_ip}:19009` is the canonical derivation (the handover doc's recommended fallback is now the primary path).
6. **Browser DevTools verification** — open the dashboard, confirm Network tab shows `/api/specs` + `/api/nodes` calls. No `/catalog/*`. No `/{type}/stack/...` calls.
7. Update reality doc (UI domain) once it's migrated; if not, append to PR description.

## Acceptance criteria

- `shared/api-client.js` has the `useLegacyApiBase` switch.
- Dashboard works end-to-end against `Fast_API__Compute`.
- Setting `useLegacyApiBase: true` flips back to legacy successfully (manual smoke test).
- All `stack_name` / `type_id` / `container_count` field reads are renamed in the active code path.
- Snapshot tests updated.
- Reality doc / PR description has the API migration record.

## Open questions

- **`POST /api/nodes` vs `POST /api/specs/{spec_id}/stack`.** Both work after BV2.5. For per-spec UI cards (firefox card, docker card, etc.) the per-spec route is more natural (the URL carries the spec). For the new generic launch form (FV2.5), the generic `POST /api/nodes` is cleaner. Recommend: per-spec routes for v0.2.x, generic for v0.3+.

## Blocks / Blocked by

- **Blocks:** FV2.3, FV2.4, FV2.7 (all consumers of the new API surface).
- **Blocked by:** none. Backend `/api/specs` + `/api/nodes` are live (verified at v0.2.0).

## Notes

This is the **single most-impactful phase** for the frontend. Once shipped, the dashboard is on the new API surface; FV2.3 + FV2.4 + FV2.7 unlock immediately.
