# 03 — Firefox configuration endpoints

## Goal

Define the endpoint families the firefox detail panel needs in order to expose the configuration column the 05/01 firefox brief calls for: credentials, MITM proxy, security toggles, profile management, AMI bake, and health.

## Today

- Backend: a firefox stack can be created (`/firefox/stack`) and stopped. Self-signed cert, basic-auth, mitmweb on the same nginx terminator. Out-of-the-box: nothing else is exposed.
- Brief surface (per `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__firefox-browser-plugin.md`):
  - Configuration: username + password, "Update Credentials".
  - MITM Proxy: status, intercept-script picker, "Upload Script", "Open Proxy UI".
  - Security: self-signed certs toggle, SSL intercept toggle.
  - Firefox Settings: start page, "Load Profile".
  - Instance: "Bake AMI" (covered by brief 02), Stop, Health badge.
- UI today (`sp-cli-firefox-detail`) has the iframe shell only. Configuration column = PROPOSED — does not exist yet.

## Required output

Five new endpoint families on the firefox plugin, all under `/firefox/{stack_id}/...`. Each delegates to a method on `Firefox__Service` (sibling of `Playwright__Service`). Routes have no logic.

### 3.1 Credentials

```
PUT /firefox/{stack_id}/credentials
```

Request: `Schema__Firefox__Credentials__Update` containing `username : Safe_Str__Username`, `password : Safe_Str__Password__Write_Only`. Response: 204 + last-rotated timestamp on a follow-up `GET`.

```
GET /firefox/{stack_id}/credentials
```

Returns username only (never password) plus `last_rotated_at`.

Backend rotates the nginx basic-auth file on the running container. No restart required.

### 3.2 MITM proxy

```
GET /firefox/{stack_id}/mitm/status
PUT /firefox/{stack_id}/mitm/script
GET /firefox/{stack_id}/mitm/script
DEL /firefox/{stack_id}/mitm/script
GET /firefox/{stack_id}/mitm/url
```

Status returns `Schema__Firefox__Mitm__Status` (`enabled`, `mode` (intercept / passthrough), `script_handle`, `last_request_at`). Script PUT/GET use the vault-write contract (see `04__vault-write-contract.md`); the handle returned points at vault-stored content. URL endpoint returns the same `mitmweb_url` already on the stack record — convenience only.

### 3.3 Security toggles

```
PUT /firefox/{stack_id}/security
GET /firefox/{stack_id}/security
```

`Schema__Firefox__Security` carries `self_signed_certs : Safe_Bool`, `ssl_intercept : Safe_Bool`. Toggle changes are applied to the live container; no restart.

### 3.4 Profile

```
PUT /firefox/{stack_id}/profile/start_url
PUT /firefox/{stack_id}/profile/load
GET /firefox/{stack_id}/profile
```

`PUT start_url` takes `Safe_Str__Url`. `PUT load` takes a profile handle (vault-written tar.gz). `GET` returns `start_url` and the loaded profile handle (no tarball content).

### 3.5 Health

```
GET /firefox/{stack_id}/health
```

Returns `Schema__Firefox__Health`:

```python
class Schema__Firefox__Health(Type_Safe):
    container_running : Enum__Health__State          # GREEN / AMBER / RED
    firefox_process   : Enum__Health__State
    mitm_proxy        : Enum__Health__State
    network           : Enum__Health__State
    login_page        : Enum__Health__State
    overall           : Enum__Health__State          # worst-of
    checked_at        : Safe_Str__ISO_Datetime
    detail            : Safe_Str__Health__Detail | None  # human-readable when overall != GREEN
```

Polled by the detail panel every 10 s.

## Acceptance criteria

- Owning route class: new `Routes__Firefox` (or extension of an existing per-plugin routes class — Architect call).
- One Type_Safe schema file per class. Enums for state and mode are `Enum__*` classes.
- Credentials and MITM scripts go through the vault-write contract (`04__vault-write-contract.md`); never returned in plaintext over the wire after PUT.
- Health endpoint is anonymous-readable; mutation endpoints require the same auth as `/firefox/stack`.
- Capability detector marks `firefox` with `mitm-proxy`, `vault-writes`, `iframe-embed` capabilities (see `01__plugin-manifest-endpoint.md`).
- Routes have no logic — pure delegation to `Firefox__Service`.

## Open questions

1. **MITM script storage path.** Is the script blob held in vault under `firefox/{stack_id}/mitm-script.py` or under a per-user namespace with the stack-id as metadata? See vault-write brief.
2. **Profile size cap.** Browser profiles can be hundreds of MB. Is there a size limit before we push profiles to S3 + pre-signed URL instead of vault?
3. **Health polling cadence.** 10 s default is suggested — confirm against load on the host FastAPI.
4. **`start_url` vs full Firefox prefs.** Brief lists "start page" only; should the schema be open enough to carry arbitrary `prefs.js` patches later? Recommendation: keep narrow for v1, widen behind a follow-up brief.

## Out of scope

- Bake AMI: handled by brief 02 + a separate AMI bake endpoint family.
- Stop / delete: existing `/firefox/stack` lifecycle endpoints suffice.
- Sidecar UI (Neko / desktop streaming): container-runtime brief.

## Paired-with

- Frontend consumer: `../v0.1.140__post-fractal-ui__frontend/03__firefox-configuration-column.md`.
- Source: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__firefox-browser-plugin.md`.
