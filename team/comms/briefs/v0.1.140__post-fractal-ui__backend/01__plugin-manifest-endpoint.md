# 01 — Plugin manifest endpoint

## Goal

Publish a single typed source-of-truth for "what plugins this service exposes". Replace the four-place duplication on the UI side and the parallel `Plugin__Registry` on the backend side with one contract: an HTTP endpoint that returns a `Schema__Plugin__Manifest` describing every plugin's id, display metadata, launch endpoint, stability, default boot time, and capability flags.

## Today

- Backend: `Plugin__Registry` (Python) is the implicit truth; `tests/.../test_Plugin__Manifests__All.py` enforces the 8-type set (`docker`, `podman`, `elastic`, `vnc`, `prometheus`, `opensearch`, `neko`, `firefox`).
- UI duplicates the same list in four places (see `frontend/01__plugin-manifest-loader.md` for refs). Each new plugin requires five parallel edits.
- There is no `/catalog/manifest` (or equivalent) endpoint exposing the registry as JSON. `/catalog/types` exists but the launcher pane does not consume it.

## Required output

A new GET endpoint that returns the manifest. Owning route class: `Routes__Catalogue` (or `Routes__Plugins` if a fresh class is preferred — Architect call). Pure delegation to a service method on `Plugin__Registry`.

### Contract — request

```
GET /catalog/manifest
```

No body. No query parameters in v1.

### Contract — response

```python
class Schema__Plugin__Manifest__Entry(Type_Safe):
    type_id              : Safe_Str__Plugin__Type_Id
    display_name         : Safe_Str__Display_Name
    icon                 : Safe_Str__Emoji
    stability            : Enum__Plugin__Stability         # stable / experimental / deprecated
    boot_seconds_typical : Safe_Int__Seconds
    create_endpoint_path : Safe_Str__Url_Path              # e.g. /firefox/stack
    capabilities         : List__Enum__Plugin__Capability  # vault-writes, ami-bake, sidecar-attach, remote-shell, metrics
    soon                 : Safe_Bool                       # if true, UI shows "coming soon" badge
    nav_group            : Enum__Plugin__Nav_Group         # compute / storage / observability
```

```python
class Schema__Plugin__Manifest(Type_Safe):
    schema_version : Safe_Int__Schema_Version              # 1 in v1
    plugins        : List__Schema__Plugin__Manifest__Entry
```

Route returns `manifest.json()` — no raw dict.

### Acceptance criteria

- One Type_Safe schema file per class, named after the class. No Pydantic, no Literals.
- `Plugin__Registry` is the only place plugin metadata lives server-side. Removing a plugin from the registry removes it from `/catalog/manifest` automatically.
- Endpoint integration test under `tests/.../routes/` asserts the eight current plugins are present and the `firefox` entry has `capabilities=[vault-writes, sidecar-attach]` and the `podman` entry has `capabilities=[remote-shell, metrics]` (subject to Architect review).
- Reality doc shard updated under `team/roles/librarian/reality/v{version}/` adding the manifest endpoint.

## Open questions

1. **Route ownership.** New `Routes__Plugins` class, or extend `Routes__Catalogue`? Architect call.
2. **`stability` taxonomy.** Today it is a free string in cards (`'stable'`, `'experimental'`). Does `deprecated` belong, or is removal the only signal?
3. **Capability vocabulary.** Initial set proposed above; the firefox brief and ephemeral-infra brief together imply: `vault-writes`, `ami-bake`, `sidecar-attach`, `remote-shell`, `metrics`, `mitm-proxy`, `iframe-embed`. Architect to lock the closed set as `Enum__Plugin__Capability`.
4. **Versioning.** `schema_version: 1` from day one. v2 reserved for future "external plugin URL" extension (container-runtime brief implies plugins from external repos).
5. **Auth.** Anonymous read, or session-scoped? Probably anonymous — the manifest is structural, not data — but Architect to confirm.

## Out of scope

- Dynamic plugin loading from external URLs. The container-runtime brief gestures at it; this contract is fixed-set v1.
- Per-region capability variation (Lambda does not run podman). Capability profiles live in `Capability__Detector`; the manifest exposes the union and the UI filters client-side using deployment-target hints.

## Paired-with

- Frontend consumer: `../v0.1.140__post-fractal-ui__frontend/01__plugin-manifest-loader.md`.
