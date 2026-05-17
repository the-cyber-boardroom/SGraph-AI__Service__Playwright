# vault — Reality Index

**Domain:** `vault/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** seeded from current `sgraph_ai_service_playwright__cli/vault/` shims + `sg_compute/vault/` canonical home (BV2.9, 2026-05-05).

Vault primitives + per-spec (formerly per-plugin) namespaced writer + FastAPI route surface. The vault hosts artefacts written by spec services — settings (UI preferences), per-stack receipts, future cert material.

**Canonical package (post-BV2.9):** `sg_compute/vault/`. The legacy `sgraph_ai_service_playwright__cli/vault/` paths are now **re-export shims** (11 files) kept for one-release backwards compatibility — deletion scheduled BV2.12.

---

## EXISTS (code-verified)

### Primitives — at canonical `sg_compute/vault/primitives/`

| Class | Pattern / purpose |
|-------|-------------------|
| `Safe_Str__Spec__Type_Id` | Spec slug; regex rejects chars outside `[a-z0-9\-_]` (renamed from `Plugin__Type_Id` in BV2.9) |
| `Safe_Str__Stack__Id` | Node stack-id; `_shared` is the cross-node sentinel |
| `Safe_Str__SHA256` | 64-char hex |
| `Safe_Str__ISO_Datetime` | ISO-8601 datetime string |
| `Safe_Str__Vault__Handle` | Handle slug — names the artefact within (spec_id, stack_id) namespace |
| `Safe_Str__Vault__Path` | Vault storage path |
| `Safe_Int__Bytes` | Non-negative byte count |

Shims at `sgraph_ai_service_playwright__cli/vault/primitives/` re-export the same classes under the old import paths.

### Enums

- `Enum__Vault__Error_Code` — `NO_VAULT_ATTACHED / UNKNOWN_SPEC / DISALLOWED_HANDLE / PAYLOAD_TOO_LARGE`.

### Schemas

- `Schema__Vault__Write__Receipt` — `spec_id / stack_id / handle / bytes_written / sha256 / written_at / vault_path`.

### Collections

- `List__Schema__Vault__Write__Receipt` — typed list of receipts.
- `List__Vault__Handle` — typed list of handles.

### Service

- `Vault__Spec__Writer` (canonical name; legacy alias `Vault__Plugin__Writer`) — `write / get_metadata / list_spec / delete`. `SHARED_STACK_ID = '_shared'`. In-memory dict backing store today; `vault_attached=True` in production wiring (BV2.4b); real vault I/O deferred to v0.3.

### Routes

- `Routes__Vault__Spec` (canonical; legacy alias `Routes__Vault__Plugin`) — `PUT/GET/DELETE /vault/spec/{spec_id}/{stack_id}/{handle}`; mounted at `/api/vault` on `Fast_API__Compute` (post-BV2.4b).

### Shim layout (`sgraph_ai_service_playwright__cli/vault/`)

| Path | Content |
|------|---------|
| `vault/__init__.py` | empty |
| `vault/primitives/*.py` | Re-export shims for `Safe_Str__SHA256`, `Safe_Int__Bytes`, `Safe_Str__ISO_Datetime`, `Safe_Str__Plugin__Type_Id`, `Safe_Str__Stack__Id`, `Safe_Str__Vault__Path`, `Safe_Str__Vault__Handle` |
| `vault/enums/Enum__Vault__Error_Code.py` | Re-export shim |
| `vault/schemas/Schema__Vault__Write__Receipt.py` | Re-export shim |
| `vault/collections/List__Schema__Vault__Write__Receipt.py` + `List__Vault__Handle.py` | Re-export shims |
| `vault/service/Vault__Plugin__Writer.py` | Shim: `from sg_compute.vault.service.Vault__Spec__Writer import Vault__Spec__Writer as Vault__Plugin__Writer` |
| `vault/fast_api/routes/Routes__Vault__Plugin.py` | Shim: `from sg_compute.vault.api.routes.Routes__Vault__Spec import Routes__Vault__Spec as Routes__Vault__Plugin` |

---

### Consumers — what writes to vault today

| Consumer | What it writes | Vault path shape |
|----------|----------------|------------------|
| UI settings bus (`api_site/shared/settings-bus.js`) | `preferences.json` (plugin enablement, UI-panel visibility, defaults) | `sp-cli/preferences.json` (read by `vault-bus.js` / `vaultReadJson` / `vaultWriteJson`) |
| Vault-publish slug registry (v0.2.23) | SSM-backed slug → stack mapping | SSM `/sg-compute/vault-publish/slugs/{slug}` (see [`sg-compute/index.md`](../sg-compute/index.md)) |
| Per-stack receipts (future) | Compose YAML, env, cert material | `/vault/spec/{spec_id}/{stack_id}/{handle}` |

### Tests

Vault tests live in the `sg_compute` test suite (`sg_compute__tests/`). The legacy shim folder has minimal coverage — main test bodies sit beside the canonical classes.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Canonical home: [`sg-compute/index.md`](../sg-compute/index.md) — `sg_compute/vault/` (BV2.9), `sg_compute_specs/vault_publish/` (v0.2.23 — slug registry + Waker Lambda + CloudFront)
- UI consumer: [`ui/index.md`](../ui/index.md) — `settings-bus.js`, `vault-bus.js`
- CLI consumer: [`cli/duality.md`](../cli/duality.md) — `sp vault` subgroup (Phase D regroup)
- Security policy on vault key hygiene: [`security/index.md`](../security/index.md)
- No v0.1.31 archive source — this domain seeded from code + the BV2.9/v0.2.23 history table in [`sg-compute/index.md`](../sg-compute/index.md).
