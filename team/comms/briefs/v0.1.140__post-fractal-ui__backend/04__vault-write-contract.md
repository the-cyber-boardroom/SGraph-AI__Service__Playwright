# 04 — Per-plugin vault-write contract

## Goal

Publish a single contract for "the UI is sending a piece of secret-bearing data that needs to land in the user's vault, scoped to this plugin and (optionally) this stack". Every plugin that needs to persist credentials, scripts, profiles, or other binaries goes through this one path. The first consumer is firefox (credentials, MITM scripts, profile tarballs). The next consumers are likely podman (sidecar configs) and elastic (saved searches).

## Today

- Vault is read-oriented from the dashboard. `sp-cli-vault-status` and `sp-cli-vault-picker` exist; there is no vault-write component.
- The vault gate was removed in commit `e34c2e6` — the dashboard now boots without a vault. Plugins that need persistence must therefore handle "no vault attached" as a degraded mode, not as a hard error.
- Backend exposes generic vault read paths via the existing vault layer; there is no published per-plugin write contract.

## Required output

A single endpoint family that scopes vault writes by plugin namespace and, optionally, by stack id. UI does not talk to the vault directly — it goes through the service, which holds the vault token.

### Contract — write

```
PUT /vault/plugin/{plugin_id}/{stack_id}/{handle}
```

Body: raw bytes (binary-safe). Content-type is the caller's responsibility.

`plugin_id` is one of the manifest type ids. `stack_id` may be the literal `_global` for plugin-wide blobs (e.g. shared MITM scripts that apply to every firefox stack of a user). `handle` is a slug naming the blob (e.g. `mitm-script`, `profile.tar.gz`, `credentials.json`).

Response: `Schema__Vault__Write__Receipt`:

```python
class Schema__Vault__Write__Receipt(Type_Safe):
    plugin_id     : Safe_Str__Plugin__Type_Id
    stack_id      : Safe_Str__Stack__Id            # or '_global'
    handle        : Safe_Str__Vault__Handle
    bytes_written : Safe_Int__Bytes
    sha256        : Safe_Str__SHA256
    written_at    : Safe_Str__ISO_Datetime
    vault_path    : Safe_Str__Vault__Path          # plugin/{plugin_id}/{stack_id}/{handle}
```

### Contract — read (metadata only)

```
GET /vault/plugin/{plugin_id}/{stack_id}/{handle}/metadata
```

Returns the receipt above plus `last_used_at` (best-effort). Never returns blob content over this endpoint — separate streaming download endpoint required if the UI needs the bytes back.

### Contract — list

```
GET /vault/plugin/{plugin_id}
```

Returns `List__Schema__Vault__Write__Receipt` for everything under that plugin namespace owned by the current user. Used by the firefox MITM-script picker.

### Contract — delete

```
DEL /vault/plugin/{plugin_id}/{stack_id}/{handle}
```

204 on success.

### Validation rules (in `Request__Validator`)

- Reject blobs over a per-plugin size cap. Default cap: 10 MB. Firefox-profile is the known outlier — handle separately if it exceeds.
- Reject `plugin_id` not present in `/catalog/manifest`.
- Reject `handle` outside the plugin's declared write-handle set (declared in `Plugin__Registry`).

### Acceptance criteria

- Owning route class: new `Routes__Vault__Plugin` (or extension of an existing vault routes class — Architect call). Routes are pure delegation to a `Vault__Plugin__Writer` service.
- All vault interaction goes through `osbot-aws` / the existing vault wrapper. No direct boto3.
- Receipt contains the SHA256 so the UI can detect "the same bytes were uploaded twice" and avoid duplicate writes.
- "No vault attached" returns 409 with a typed error code (`Enum__Vault__Error_Code.NO_VAULT_ATTACHED`) — the UI surfaces this as a degraded-mode toast.
- Each plugin that wants vault writes declares its `write_handles` set in the manifest (`01__plugin-manifest-endpoint.md`). Firefox writes initially: `credentials`, `mitm-script`, `profile`.
- Capability `vault-writes` flagged in the manifest entry for any plugin that uses this contract.

## Open questions

1. **Encryption-at-rest.** Does the vault layer already encrypt at rest, or is the plugin responsible for sealing before PUT? Architect to confirm.
2. **Auditing.** Should writes emit a `vault.written` event consumable by `sp-cli-events-log`? Recommendation: yes, with handle-only payload (no bytes).
3. **Multi-stack sharing.** Brief 03 (firefox MITM script picker) implies a script can be shared across stacks. The `_global` stack id covers this — but does the lifecycle of `_global` blobs need explicit user-owned cleanup, or does it ride with the user's vault deletion?
4. **Listing scope.** `GET /vault/plugin/{plugin_id}` returns global + per-stack blobs in one response. Confirm whether the UI prefers two endpoints or one with a flag.
5. **Cross-plugin reuse.** Does the same MITM script make sense across firefox AND a future "Chrome via mitmweb" plugin? If yes, namespace by capability (`mitm-script` shared across all `mitm-proxy`-capable plugins) — but this is v2 territory.

## Out of scope

- Streaming download of vault blob content. A separate `GET .../content` endpoint can ride later when the first UI consumer needs to display profile contents.
- Vault key creation / rotation. Existing vault layer handles this.

## Paired-with

- First frontend consumer: `../v0.1.140__post-fractal-ui__frontend/03__firefox-configuration-column.md`.
- Triggered by: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__firefox-browser-plugin.md` (lines 91-103).
