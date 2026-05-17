# Pod Management & Control Plane

**Domain:** `sg-compute/` | **Subarea:** `sg_compute/core/pod/` + `sg_compute/control_plane/` + `api_site/components/sg-compute/` | **Last updated:** 2026-05-17

Pod schemas, the `Pod__Manager` / `Sidecar__Client` runtime introduced in BV2.3 (with full typing from T2.6b/T2.6c), the `Fast_API__Compute` control-plane app and its routes, AMI listing, and the dashboard web components that consume the control plane.

---

## EXISTS

### sg_compute/core/pod/ — BV2.3 + T2.6b/T2.6c (fully typed)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Pod__Info` | `core/pod/schemas/Schema__Pod__Info.py` | `pod_name: Safe_Str__Pod__Name`, `node_id: Safe_Str__Node__Id`, `image: Safe_Str__Docker__Image`, `state`, `ports: Safe_Str__Message` |
| `Schema__Pod__List` | `core/pod/schemas/Schema__Pod__List.py` | `pods: List[Schema__Pod__Info]` |
| `Schema__Pod__Stats` | `core/pod/schemas/Schema__Pod__Stats.py` | `container: Safe_Str__Pod__Name`, float metrics, `pids: Safe_Int__Pids` |
| `Schema__Pod__Logs__Response` | `core/pod/schemas/Schema__Pod__Logs__Response.py` | `container: Safe_Str__Pod__Name`, `lines: Safe_Int__Log__Lines`, `content: Safe_Str__Log__Content`, `truncated: bool` |
| `Schema__Pod__Stop__Response` | `core/pod/schemas/Schema__Pod__Stop__Response.py` | `name: Safe_Str__Pod__Name`, `stopped/removed: bool`, `error: Safe_Str__Message` |
| `Schema__Pod__Start__Request` | `core/pod/schemas/Schema__Pod__Start__Request.py` | `name: Safe_Str__Pod__Name`, `image: Safe_Str__Docker__Image`, `type_id: Safe_Str__Spec__Id` (ports/env omitted — Type_Safe__Dict not Pydantic-serialisable) |
| `Dict__Pod__Ports` | `core/pod/collections/Dict__Pod__Ports.py` | `Type_Safe__Dict[str→str]` |
| `Dict__Pod__Env` | `core/pod/collections/Dict__Pod__Env.py` | `Type_Safe__Dict[str→str]` |
| `Sidecar__Client` | `core/pod/Sidecar__Client.py` | HTTP adapter for one node's `:19009` sidecar; `list/get/logs/start/stop/remove` |
| `Pod__Manager` | `core/pod/Pod__Manager.py` | Bridge: `node_id → public_ip → Sidecar__Client`; public methods typed `Safe_Str__Node__Id`/`Safe_Str__Pod__Name`; schema construction wraps sidecar values explicitly |

### sg_compute/control_plane/ — EXISTS (B4 + BV2.3 + BV2.4)

| Class | Path | Description |
|-------|------|-------------|
| `Fast_API__Compute` | `control_plane/Fast_API__Compute.py` | Mounts `/api/health`, `/api/specs`, `/api/nodes`, `/api/stacks`, `/api/vault`; `StaticFiles` at `/api/specs/{spec_id}/ui`; `/legacy/*` (deprecated SP CLI surface with `X-Deprecated: true` header) |
| `Routes__Ec2__Playwright` | `control_plane/legacy_routes/Routes__Ec2__Playwright.py` | Moved from `fast_api/routes/`; shim left at old path |
| `Routes__Observability` | `control_plane/legacy_routes/Routes__Observability.py` | Moved from `fast_api/routes/`; shim left at old path |
| `Routes__Compute__Health` | `control_plane/routes/Routes__Compute__Health.py` | `GET /api/health`, `GET /api/health/ready` |
| `Routes__Compute__Specs` | `control_plane/routes/Routes__Compute__Specs.py` | `GET /api/specs`, `GET /api/specs/{spec_id}`, `GET /api/specs/{spec_id}/readme` (text/markdown; 404 if absent) |
| `Routes__Compute__Nodes` | `control_plane/routes/Routes__Compute__Nodes.py` | `GET /api/nodes`, `GET /api/nodes/{node_id}`, `POST /api/nodes`, `DELETE /api/nodes/{node_id}`; `POST` calls `EC2__Platform.create_node` (docker spec only; others raise `NotImplementedError`) |
| `Routes__Compute__Pods` | `control_plane/routes/Routes__Compute__Pods.py` | 6 pod endpoints under `/api/nodes/{node_id}/pods/*`; constructor injection of `Pod__Manager` |
| `Routes__Compute__AMIs` | `control_plane/routes/Routes__Compute__AMIs.py` | `GET /api/amis?spec_id=<id>` → `Schema__AMI__List__Response`; delegates to `AMI__Lister` |
| `AMI__Lister` | `core/ami/service/AMI__Lister.py` | Lists AMIs filtered by spec_id; returns `Schema__AMI__List__Response` |
| `Schema__AMI__Info` | `core/ami/schemas/Schema__AMI__Info.py` | `ami_id / name / created_at / state / size_gb` |
| `Schema__AMI__List__Response` | `core/ami/schemas/Schema__AMI__List__Response.py` | `spec_id + amis: List__Schema__AMI__Info` |
| `List__Schema__AMI__Info` | `core/ami/collections/List__Schema__AMI__Info.py` | typed collection |
| `Routes__Compute__Stacks` | `control_plane/routes/Routes__Compute__Stacks.py` | PLACEHOLDER |

### api_site / dashboard — frontend components — EXISTS (v0.2.1 hotfix)

All dashboard web components live under `sgraph_ai_service_playwright__api_site/components/sg-compute/` (renamed from `sp-cli/` in T3.3b).

| Component | Path (relative to `api_site/`) | Status | Notes |
|-----------|-------------------------------|--------|-------|
| `sg-compute-specs-view` | `components/sg-compute/sg-compute-specs-view/v0/v0.1/v0.1.0/` | COMPLETE | Spec grid; card-body click + keyboard (Enter/Space) dispatch `sp-cli:spec.selected`; `tabindex="0"` + `:focus-visible` ring |
| `sg-compute-spec-detail` | `components/sg-compute/sg-compute-spec-detail/v0/v0.1/v0.1.0/` | COMPLETE | Full manifest panel; README placeholder (backend `GET /api/specs/{id}/readme` TBD); extends lineage text; baked AMIs placeholder |
| `sg-compute-launch-form` | `components/sg-compute/_shared/sg-compute-launch-form/v0/v0.1/v0.1.0/` | COMPLETE | Three-mode selector FRESH/BAKE_AMI/FROM_AMI; CSS-only show/hide; cost preview; `getValues()` returns `creation_mode/ami_id/ami_name`; `validate()` blocks FROM_AMI without AMI |
| `sg-compute-launch-panel` | `components/sg-compute/sg-compute-launch-panel/v0/v0.1/v0.1.0/` | COMPLETE | POST `/api/nodes` with full body including `ami_name`; error/loading states |
| `sg-compute-ami-picker` | `components/sg-compute/_shared/sg-compute-ami-picker/v0/v0.1/v0.1.0/` | COMPLETE | `setSpecId()` fetches `GET /api/amis?spec_id=...` via `apiClient`; loading/error/empty states; dispatches `sg-compute:ami.selected` |
| `sg-compute-compute-view` | `components/sg-compute/sg-compute-compute-view/v0/v0.1/v0.1.0/` | COMPLETE | Nodes list; launch constants from `shared/launch-defaults.js` |
| `sg-compute-nodes-view` | `components/sg-compute/sg-compute-nodes-view/v0/v0.1/v0.1.0/` | COMPLETE | Node cards with pod state; uses canonical `pod_name` / `state` field names |
| `sg-compute-settings-pane` | `components/sg-compute/sg-compute-settings-pane/v0/v0.1/v0.1.0/` | COMPLETE | Settings bus dual-dispatch; WCAG AA contrast |
| `shared/launch-defaults.js` | `shared/launch-defaults.js` | COMPLETE | Single source of truth for `REGIONS`, `INSTANCE_TYPES`, `MAX_HOURS`, `COST_TABLE` |
| `shared/api-client.js` | `shared/api-client.js` | COMPLETE | Shared fetch wrapper used by all components |
| `shared/settings-bus.js` | `shared/settings-bus.js` | COMPLETE | Settings event bus (`getAllDefaults()`) |

**Structural snapshot tests** (all green):
- `tests/ci/test_sg_compute_spec_detail__snapshot.py` — 13 assertions
- `tests/ci/test_sg_compute_ami_picker__snapshot.py` — 17 assertions

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`primitives.md`](primitives.md) — `Safe_Str__Pod__Name`, `Safe_Str__Docker__Image`, `Enum__Pod__State`
- [`platform.md`](platform.md) — `EC2__Platform` (resolves node_id → public_ip for `Pod__Manager`)
- [`host-plane.md`](host-plane.md) — pointer to the `:19009` host-control sidecar that `Sidecar__Client` talks to
- [`specs.md`](specs.md) — vault routes mounted at `/api/vault` on `Fast_API__Compute`
- [`cli.md`](cli.md) — CLI counterpart driving the same control-plane endpoints
