---
title: "Content-transformation proxy — Components & contracts"
file: 03__components-and-contracts.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — the exact wiring. The interceptor ↔ FastAPI contract is the load-bearing detail.
---

# Components & contracts

This doc pins the integration so the compose env and the tests are exactly right. The
load-bearing piece is the **interceptor addon ↔ FastAPI MITM service** contract — derived
verbatim from the operator-supplied `fastapi_interceptor.py` (v0.2.1).

---

## 1. mitmproxy — stock image + one interceptor addon

- **Image:** `mitmproxy/mitmproxy` (pin a 10.x — see open decision in the spec).
- **Command:** `mitmweb --listen-host 0.0.0.0 --listen-port <8080|8081> --scripts /interceptors/active.py [--proxyauth user:pass]`
- **`--proxyauth` only on `mitmproxy-ext`.** `mitmproxy-int` has none.
- **The addon is the same file** on both. It is dumb plumbing: capture the flow → POST to
  FastAPI → apply the returned modifications.

### 1.1 The interceptor's env (what the compose must set)

```
FASTAPI_BASE_URL        = http://mitm-service:10011     # the MITM service on the docker network
FASTAPI_API_KEY_NAME    = x-api-key                     # header name the MITM service expects
FASTAPI_API_KEY_VALUE   = <secret>                      # the key value
```

> Note the addon builds `FASTAPI_HEADERS` from these at import. If the name/value are unset the
> header dict is malformed — **the compose must always set all three.** (Improvement to fold in
> when we bake our own copy: default-guard these.)

### 1.2 What the addon decides locally (do NOT move this into FastAPI)

`should_process_request(flow)`:
- `method != GET` → **skip**
- path starts with `/mitm-proxy` → **always process** (the MITM service's own admin/static)
- strip query, take extension; if extension ∈ `STATIC_EXTENSIONS` (`.js .css .png .jpg .svg
  .woff .mp4 .pdf …`) → **skip**; else → **process**

`should_process_response(flow)`:
- `x-proxy-cached-in-request == true` → **skip** (already answered in the request phase)
- `content-type` not `text/html` → **skip** (images/json pass untouched)
- else → **process**

Everything else (the decision to transform, the script) is the FastAPI service's job.

---

## 2. The contract — `POST /proxy/process-request`

**Interceptor → FastAPI** (sent for processable GETs, before origin fetch):

```jsonc
{
  "method": "GET",
  "host": "news.site",
  "path": "/article/9",
  "original_path": "/article/9",
  "headers": { "...": "...", "Cookie": "mitm-show=1; mitm-inject=1" },   // Cookie included
  "stats":  { "request_count": 142, "errors_count": 1, "timestamp": "..." },
  "version": "v0.2.1"
}
```

**FastAPI → Interceptor** (any subset; `null`/no-response ⇒ fallback, request passes):

```jsonc
{
  "cached_response": { "status_code": 200, "body": "<html>...</html>", "headers": {...} },
  "block_request":  true, "block_status": 403, "block_message": "Blocked by proxy",
  "headers_to_add":    { "x-policy": "news-v3" },
  "headers_to_remove": [ "if-none-match" ]
}
```

Effects the addon applies, in order: **cached_response** (serve now, set
`x-proxy-cached-in-request: true`, stop) → **block_request** (make a 403, stop) →
header add/remove → forward. Tracking headers stamped: `x-proxy-request-count`,
`x-proxy-status` (`fastapi-connected` | `fastapi-unavailable`).

---

## 3. The contract — `POST /proxy/process-response` (the injection point)

**Interceptor → FastAPI** (only for `text/html`, body included):

```jsonc
{
  "request":  { "method":"GET","host":"news.site","path":"/article/9","url":"https://news.site/article/9",
                "headers": { "Cookie":"mitm-show=1; mitm-inject=1", "...":"..." } },
  "response": { "status_code":200, "headers":{...}, "content_type":"text/html",
                "body":"<html>...full origin HTML...</html>", "body_size":12701 },
  "stats":    { "response_count": 88, "request_count": 142, "errors_count": 1, "timestamp": "..." },
  "version":  "v0.2.1"
}
```

**FastAPI → Interceptor** (the response modifications — this is where the `<script>` is added):

```jsonc
{
  "override_response": true,
  "override_status": 200,
  "override_content_type": "text/html",
  "modified_body": "<html>... + <script src=\"/mitm-proxy/transform.js\"></script> ...</html>",
  "headers_to_add":    { "x-content-policy": "applied" },
  "headers_to_remove": [ "content-security-policy" ],     // often needed so the script can run
  "include_stats": true
}
```

The addon sets `flow.response.content = modified_body`, fixes `content-length`, applies header
edits, stamps `x-proxy-response-count` + `x-proxy-status`. **`modified_body` = origin page +
injected `<script>`** — that is the whole mechanism.

> CSP caveat: origin `Content-Security-Policy` can block an injected inline/script. The MITM
> service typically strips/relaxes CSP via `headers_to_remove`. Capture this in a test.

---

## 4. Activation — cookies (FastAPI-owned)

Activation is signalled by `mitm-*` cookies (`mitm-show`, `mitm-inject`, `mitm-debug`, …), but
**the decision logic lives in the FastAPI service** — the cookies arrive in the `Cookie` header
the addon forwards. The stack does not parse cookies.

- **Human path (Mode 1):** the user/UX sets the cookies in their browser.
- **QA path (Mode B):** the sg-playwright sequence sets the cookies on the browser context
  before navigating (so the no-cookie automation still activates). Confirm exact names/values
  with the MITM service (spec open decision #3).

---

## 5. FastAPI MITM service (external image; this stack consumes it)

`MGraph-AI__Service__Mitmproxy` — Python 3.12 / OSBot-Utils / OSBot-Fast-API / OSBot-AWS;
`x-api-key`; **:10011**; admin UI + console + mitm-scripts CLI; Lambda-deployable. For this
stack it runs as a **container** on the compose, reachable only on the docker network. It reads
the latest transformation script from the **script vault** and returns it inside
`modified_body`. We pull a pinned image (spec open decision #2); we do not re-implement it.

---

## 6. sg-playwright (this repo) — how it plugs in

- Container env: `SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy-int:8081`,
  `IGNORE_HTTPS_ERRORS=true`, `X-API-Key`.
- Driven by tests/agents over its existing 16-route HTTP surface (`/sequence/execute`,
  `/browser/*`, `/screenshot`). **No new endpoints.**
- The QA sequence: set `mitm-*` cookies on the context → navigate a corpus URL → extract
  DOM/text + screenshot → assert the transform. This is deliverable (b).
- Browser-page callers reach it same-origin via the vault `/pw` reverse proxy
  (`x-sgraph-access-token` → `X-API-Key`), per the v0.2.41 spec.

---

## 7. Vault app (external image) + vault loading

- Runs as a container; `SEND__STORAGE_MODE` → S3; serves the UX launcher + testing vaults; the
  append target for role-2 logging; hosts the `/pw` reverse proxy.
- **Vaults loaded at build/deploy** by the `content_proxy` user-data / `load-vaults` verb:
  `Schema__Content_Proxy__Vault__Source { kind: Enum (ZIP | SGIT), ref: Safe_Str, target: Safe_Str }`.
  - `ZIP` — copy a bundled archive into the vault app's store.
  - `SGIT` — `sgit clone <ref>` from a live server or `s3://bucket` (precedent:
    `Section__SGit_Venv.py`). Vault keys come out-of-band — **never in git**.

---

## 8. Schemas this repo adds (Type_Safe; one class per file)

| Schema / enum | Fields / values |
|---------------|-----------------|
| `Schema__Content_Proxy__Create__Request` | `name`, `mode: Enum__Content_Proxy__Mode`, `vaults_to_load: List__…__Vault__Source`, `proxyauth_user`, `proxyauth_pass`, `mitm_service_image`, `vault_app_image`, `region`, `instance_type` |
| `Schema__Content_Proxy__Vault__Source` | `kind: Enum (ZIP|SGIT)`, `ref: Safe_Str`, `target: Safe_Str__Id` |
| `Schema__Content_Proxy__Stack__Info` | instance id/state/ip, `mode`, component health, `active_script`, `vaults_present` |
| `Schema__Content_Proxy__Flow__Summary` | `via: Enum (EXT|INT)`, `method`, `host`, `path`, `status_code`, `action: Enum (INJECTED|BLOCKED|CACHED|SKIPPED|FALLBACK|PASSED)`, `fastapi: Enum (CONNECTED|UNAVAILABLE)` |
| `Enum__Content_Proxy__Mode` | `DIRECT_PROXY`, `VAULT_WEB` |
| `Enum__Content_Proxy__Flow__Action` | `INJECTED`, `BLOCKED`, `CACHED`, `SKIPPED`, `FALLBACK`, `PASSED` |

Flow actions map directly to the addon's `x-proxy-*` headers — so the TUI/Source derives them
without guessing.

---

## 9. Improvements to fold in when we bake our own interceptor copy

The supplied `fastapi_interceptor.py` is the starting point. When it lands in
`sg_compute_specs/content_proxy/interceptors/active.py`, fold in (each a tiny, tested change):

1. **Guard the env** — fail loud (or sane default) if `FASTAPI_API_KEY_NAME/VALUE` unset, so
   `FASTAPI_HEADERS` is never malformed.
2. **Make `should_process_*` data-driven** (`STATIC_EXTENSIONS` + processable content-types as
   module constants — already close) so tests can parametrise them.
3. **Surface the `action`** as an explicit `x-proxy-action` header (one of the enum values) so
   the TUI source reads one header instead of inferring from several.
4. Keep it **dependency-free** (stdlib `urllib` + `ThreadPoolExecutor`) — no new pip deps in
   the proxy container.
</content>
