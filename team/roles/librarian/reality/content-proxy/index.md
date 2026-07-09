# content-proxy — Reality Index

**Domain:** `content-proxy/` | **Last updated:** 2026-07-03 | **Maintained by:** Dev (landing) → Librarian (verify)
**Code-source basis:** `sg_compute_specs/content_proxy/` at package version `0.1.0` — **merged to `dev`** (repo line `v0.2.65`).

The content-transformation proxy stack: a browser routes through **mitmproxy**, which forwards every HTML request/response to a **FastAPI MITM service** that injects a client-side transformation `<script>`; **sg-playwright** drives/QAs it; the **vault app** terminates `:443` + `/pw`. Two mitmproxy instances (ext basic-auth for humans, int no-auth for Playwright) into one workflow. Spec: [`library/docs/specs/v0.2.63__content-transformation-proxy-stack.md`](../../../../library/docs/specs/v0.2.63__content-transformation-proxy-stack.md). Brief pack: `team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/`.

---

## EXISTS (code-verified, 215 unit tests passing — no mocks)

### Spec skeleton (`sg_compute_specs/content_proxy/`)
- `manifest.py` — `MANIFEST` (`spec_id='content_proxy'`, caps `MITM_PROXY` + `BROWSER_AUTOMATION` + `REMOTE_SHELL`, `EXPERIMENTAL`). Conformance test green.
- `version` — `0.1.0`.
- **Enums (8):** `Mode` (DIRECT_PROXY/VAULT_WEB), `Tls` (NONE/**SELF_SIGNED**/LETSENCRYPT/ACM), `Vault__Kind` (ZIP/SGIT), `Flow__Action` (INJECTED/BLOCKED/CACHED/SKIPPED/FALLBACK/PASSED), `Proxy` (EXT/INT), `Stack__State`, `Edge` (NONE/CADDY), `Proxy__Tool` (MITMWEB/MITMDUMP).
- **Primitives (4):** `Safe_Str__Content_Proxy__Stack__Name`, `Safe_Str__Content_Proxy__Ref` (paths/URIs/sgit), `Safe_Str__IP__Address`, `Safe_Str__Content_Proxy__Env__File` (backs `env_inline` / full `.env` bodies).
- **Schemas:** `Create__Request` (images default to Docker Hub refs incl. `diniscruz/mgraph-ai-service-mitmproxy`; `mitmproxy/mitmproxy:12.2.3`; tls; proxyauth; proxy CA; `vaults_to_load` empty in MVP), `Vault__Source`, `Flow__Summary`, `Stack__Info` (5-component health). Collections for both.

### Interceptor (`interceptors/`)
- `Content_Proxy__Interceptor__Logic.py` — **stdlib-only** pure logic: `should_process_request/response`, `build_request/response_payload`, `classify_action` (returns strings 1:1 with `Enum__Content_Proxy__Flow__Action`). Fully unit-tested without mitmproxy.
- `active.py` — thin mitmproxy `--scripts` adapter: forwards to FastAPI `POST /proxy/process-request` + `/proxy/process-response`, applies returned modifications, stamps `x-proxy-*` (incl. `x-proxy-action`). Cookie-driven, env-guarded. Always processes `/mitm-proxy` (the injected-UI smoke check).

### Compose + deploy render (`service/`, `docker/compose/`)
- `Content_Proxy__Compose__Template` — renders the 5-service stack: `mitmproxy-ext` (basic auth), `mitmproxy-int` (no auth, net-local), `mitm-service` (:10011, net-local), `sg-playwright` (proxied to int, IGNORE_HTTPS_ERRORS), `vault-app` (:443, `/pw`). Secrets are `${...}` `.env` refs — never baked. Image refs are the only `.format` fields.
- **Committed** `docker/compose/docker-compose.yml` (for local `docker compose up`) + drift-guard test + `.env.example`.
- `Content_Proxy__User_Data__Builder` — pure EC2 cloud-init render: install docker+compose, write `.env` + compose + embedded interceptor → `/opt/content-proxy`, `docker compose up`, `shutdown +Nh`. MVP writes **no vaults**.
- `Content_Proxy__Flow__Mapper` — mitmweb `/flows` entry → `Flow__Summary` (action/fastapi from `x-proxy-*`).

### TUI renders (`tui/renders/`)
- `Content_Proxy__TUI__Status__Render` + `…__Traffic__Render` — pure `*_markup` + `*_plain` (no-TTY) functions (Sentinel pattern). Status shows the 5 components + the `/mitm-proxy` smoke result.

### Traffic harness (`traffic/`)
- Labelled corpus (`should-blur/remove/pass/skip`) + fixtures, `Content_Proxy__Traffic__Runner` (pure `build_results` grading), `Content_Proxy__Traffic__Report__Builder` (accuracy + p50/p95 latency).

### EC2 launch + CLI (`service/`, `cli/`) — reuses the shared `sg va` foundation
- `Content_Proxy__AWS__Client` composes the shared EC2 helpers (`EC2__SG/AMI/Instance/Launch/Tags__*` + `Stack__Naming(section_prefix='cp')`, `stack_type='content-proxy'`) — no new AWS logic.
- `Content_Proxy__Service` (`Spec__Service__Base`): `create_stack` / `list_stacks` / `get_stack_info` / `delete_stack` + `cli_spec`; `health`/`exec`/`connect` inherited. Tags carry `cp:mode` / `cp:tls`. `Content_Proxy__Stack__Mapper` (pure, tested). Create/List/Delete response schemas.
- `Cli__Content_Proxy` (`Spec__CLI__Builder`): standard verbs `list/info/create/delete/health/connect/exec` (the builder's default `wait` is **replaced** — see below) + `ami` (bake/delete/list/wait) / `cert` (check/generate/inspect/show) groups + top-level **`smoke`** (the `/mitm-proxy` chain check on the EC2 box via SSM, no SSH), **`logs`** (stream any of 12 host/container log sources over SSM — incl. `cert-init`, `caddy`, `browser-1/2` + a dynamic `browser-N` pattern), and the diagnose-driven **`check`** / **`wait`** (see "Boot diagnostics" below) + create extras (`--env-file` ships a working `.env` verbatim, `--scripts-bucket`, `--forward-aws-creds`, `--proxy-tool`, `--tls`, `--proxyauth-*`, `--proxy-ca-*`, `--edge-auth`, `--browsers N --browser-engine chromium|firefox`) + a **`local up|down|status|logs|smoke|pull|ca`** group wrapping `docker compose` on the committed local stack (`up --browsers N` renders gitignored `docker-compose.generated.yml` + `Caddyfile.generated` variants) (`smoke` = curl the `/mitm-proxy` chain check through mitmproxy-ext; `pull` = refresh `:latest`; `ca` = show the mitmproxy CA cert for browser import; `up --pull`). Registered in `sg_compute/cli/Cli__SG.py` as **`sg content-proxy`** (alias `cp`).

### Vault TLS on :443 (mirrors `sg va`)
- `Enum__Content_Proxy__Tls` = NONE / SELF_SIGNED / LETSENCRYPT (→ cert-init `letsencrypt-ip`) / ACM (ALB — not wired). When `tls != NONE` the compose adds a one-shot **`cert-init`** sidecar (`diniscruz/sg-host-control`, auto-detects the public IP via IMDS) that writes `/certs` to a shared `vault_certs` volume; the vault terminates TLS on :443 via `FAST_API__TLS__*`. LETSENCRYPT also opens/publishes `:80` (ACME http-01). `create` opens SG `:80` only for LETSENCRYPT. Health probe scheme follows the stack's tls (http for NONE, https for TLS).
- **Secrets:** one shared `SGRAPH_SEND__ACCESS_TOKEN` (vault auth + the sg-playwright `X-API-Key` the `/pw` proxy forwards — they must match) + `FASTAPI_API_KEY_VALUE` (interceptor↔mitm-service). `create` reuses both from a supplied `--env-file`, generating only when absent (surfaced once, labelled from-env vs generated).
- **Health via SSM:** `wait`/`health` probe the vault on the box (`localhost`) over SSM (`localhost_probe_command` + `parse_http_code`/`is_healthy_code`), not the external IP — robust against SG/caller-IP drift and self-signed TLS.
- **Interceptor** leaves `mitm.it` (mitmproxy onboarding/cert page) untouched.

### Front-door edge — Caddy (local + EC2)
- `Enum__Content_Proxy__Edge` (NONE | CADDY). `Content_Proxy__Edge__Template` renders a `Caddyfile`; `Compose__Template.render(edge=CADDY)` adds a `caddy` service that owns `:443` (TLS) and routes `/`→vault, `/pw/*`→sg-playwright (auth injected) — vault becomes a **plain origin** (no `serve_with_proxy` patch, no vault TLS, no cert-init). Committed `docker/compose/docker-compose.caddy.yml` + `Caddyfile` (drift-guarded); `sg cp local up --edge caddy`. Default path (NONE, vault-as-edge) unchanged. Rationale + options: `team/roles/architect/reviews/06/19/content_proxy__edge-front-door-options.md`.
- **Two site-address modes.** Local: the Caddyfile binds a **named** site `localhost, 127.0.0.1` + `tls internal` (a bare `:443` has no subject → Caddy aborts the handshake with `tlsv1 alert internal error`; the named site provisions the internal cert at startup). Hostname: `Edge__Template.render(hostname=<fqdn>, acme_email=…)` emits an `<fqdn> { … }` block and Caddy does **public auto-ACME** (http-01 on :80, tls-alpn on :443) — the cert external callers (Claude) trust. `edge_block(edge, hostname)` publishes `:80` (+ `:443`) on the caddy service only in hostname mode.
- **EC2 wiring (`--edge` / `--hostname` / `--with-aws-dns`).** Create request carries `edge` / `hostname` / `with_aws_dns`. `derive_fqdn(stack, request)` = explicit `--hostname` ⊳ `<stack>.sg-compute.sgraph.ai` (when `--with-aws-dns`, zone via `SG_AWS__DNS__DEFAULT_ZONE`) ⊳ blank; any FQDN forces `edge=CADDY`. `User_Data__Builder` writes the `Caddyfile` (hostname variant) to `/opt/content-proxy/` and drops the `/pw` override (edge routes it). `sg_rules(tls, edge, hostname)` opens `:443`+`:80` to the world for a public hostname (Claude reach + Caddy ACME); else caller-scoped. Tags `cp:edge` / `cp:hostname`; `Stack__Info` + mapper + renderer surface them (`https://<fqdn>/`). `--with-aws-dns` reuses the **sg va** Route 53 flow (`Vault_App__Auto_DNS`) via the CLI `post_launch_fn` (background thread, joined after `_wait_healthy`). Health probe uses `https` when the edge fronts TLS even if vault `tls=NONE`.
- **`.env` is the single source for every container var.** All compose env entries use `=${VAR}` interpolation (the mitm-service AWS_*/`CACHE__SERVICE__BUCKET_NAME` were converted from bare passthrough to `=${VAR:-}`), so `--env-file` feeds every container. `local up` (a) back-fills keys missing from a stale `.env` from `.env.example`, and (b) `realize_secrets` replaces `change-me`/blank secret values with real GUIDs — `FASTAPI_API_KEY_VALUE` (the mitm-service rejects non-GUID keys), `CONTENT_PROXY__PROXYAUTH_PASS`, and one shared GUID into both `FAST_API__AUTH__API_KEY__VALUE` + `SGRAPH_SEND__ACCESS_TOKEN` (the access-token pair stays identical). EC2 `create` generates `fastapi_key`/`access_token` as `uuid4` too.

### Configurable proxy tool
- `Enum__Content_Proxy__Proxy__Tool` (MITMWEB | MITMDUMP). Create request defaults to **MITMDUMP** (prod-safe, no in-memory flow accumulation); the committed local compose + template default to **MITMWEB** (dev — TUI `/flows`).

### Interactive browser fleet — sg-playwright-vnc (2026-07)
- `--browsers N` (`create` or `local up`) adds `cp-browser-{i}` containers on **`diniscruz/sg-playwright-vnc`** (the sg-playwright image + Xvfb/openbox/x11vnc/noVNC under supervisord — `sg_compute_specs/playwright/vnc/`), reached at **`/browser/{i}/`** through the Caddy edge (forced). Wiring is **env-only**: `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` (→ mitmproxy-int), `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` (mitmproxy CA — no certutil/profile prep on the host), `SG_PLAYWRIGHT__AUTOSTART_BROWSER` (`--browser-engine chromium|firefox`, an env choice on the same image), and the stack access token as the in-container API key. Ephemeral (no volumes); `:6080` never published (edge-only). Tags `cp:browser-count`/`cp:browser-engine` → per-browser URLs in `info`/`create`. Each browser is ALSO a full sg-playwright API (`POST /desktop/browser` opens the headed session; `/session/{id}/*` drives the same browser the human sees). Replaced the jlesage/firefox fleet (v0.2.66 line — TLS 307, noVNC sub-path breakage, certutil NSS boot hang); plan: `team/comms/plans/v0.2.67__sg-playwright-vnc__interactive-browser-image.md`.
- **`--edge-auth`** (opt-in, default off) — Caddy 401-gates `/pw/*` + `/browser/{i}/*` unless the access token arrives as `X-API-Key` or the `cp_access` cookie (`/edge/auth?token=…` bootstrap route sets it). Off → byte-identical open render (drift-guarded).

### Boot diagnostics — `diagnose()` + `check` / `wait` (2026-07)
- `Content_Proxy__Service.diagnose(region, name)` — a **9-stage generator** yielding `(check, status, detail)` over SSM: `ec2-state → ssm-reachable → boot-failed → container-engine → containers-up → cert-init → vault-http → browser-http → boot-ok` (+ the CLI appends an `external-http` `svc.health()` probe). `browser-http` docker-execs `curl :6080/vnc.html` inside every `cp-browser-{i}` (skip when no fleet) — proves the noVNC desktop SERVES, not merely that the container is Up. Pure parsers back it: `expected_containers`/`has_cert_init` (shape-aware: base 5 + `cp-cert-init` for non-caddy TLS + `cp-caddy` for edge), `parse_ps_names_status`/`containers_up_status`, `engine_active`, `boot_log_failed/complete/last_stage`, `cert_init_status`.
- `sg cp check` (one-shot) and `sg cp wait` (loops until all-OK/timeout) render a live Rich check-table via the **shared** `sg_compute/cli/base/Spec__Diagnose__Renderer`; **`create --wait` uses the same table** (the builder's silent `_wait_healthy` now delegates to the diagnose renderer when the service exposes `diagnose()`). Per-failure rows suggest the matching `sg cp logs --source <x>`.

### Credential / env plumbing (2026-07)
- **`SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS`** (prefixed) is the name sg-playwright reads — the compose emits the prefixed form (an earlier bare `IGNORE_HTTPS_ERRORS` was silently ignored → `ERR_CERT_AUTHORITY_INVALID` through mitmproxy).
- **`realize_secrets`** re-couples `FAST_API__AUTH__API_KEY__VALUE` ↔ `SGRAPH_SEND__ACCESS_TOKEN` whenever they **differ** (not only when blank/`change-me`) — a drifted local `.env` otherwise yielded "Invalid API key value" on `/pw`.
- **`AWS_ACCOUNT_ID`** is always written to the box `.env` (derived via `derive_account_id` → osbot-aws `AWS_Config().aws_session_account_id()`), not only on the `--forward-aws-creds` path.
- **`CACHE__SERVICE__BUCKET_NAME`** — `create` inherits it from the operator's local `.env` when `--scripts-bucket` is blank (`resolve_scripts_bucket`).
- **`block_global=false`** — `proxy_command(allow_global=…)` sets it on the **ext** (internet-facing) proxy only; without it mitmproxy kills remote browsers from public IPs ("killed by block_global option"). The int proxy (docker-network, private IPs) is unaffected.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md). The EC2 launch Service + CLI now EXIST (above). Remaining: **Textual screens + live `__TUI__Source`** (the render fns exist; `tui/screens/` is empty), **api/routes** (empty package — `manifest.create_endpoint_path='/api/specs/content_proxy/stack'` is still a claim with no route behind it), **deploy-via-pytest + real-Chromium integration** (all 179 tests are pure unit — no docker-compose bring-up), **vault loading** (post-MVP), and **ACM (ALB) TLS**. Note: **SELF_SIGNED + LETSENCRYPT are now wired** via the `cert-init` sidecar (see the TLS section above) — only ACM remains proposed.

### Known gaps / open bugs (2026-07 review)
- **EC2 `create` ships the ext (internet-facing) proxy with empty basic-auth** unless `--proxyauth-*` is passed — `realize_secrets` (which fills a GUID pass locally) does not run on the EC2 path, so the box gets `proxyauth=:`.
- **`--env-file` bypasses the access-token coupling guard** — a shipped `.env` with divergent `FAST_API__AUTH__API_KEY__VALUE` / `SGRAPH_SEND__ACCESS_TOKEN` deploys as-is (the `/pw` "Invalid API key value" failure, unguarded server-side).
- **`--proxy-ca-cert` / `--proxy-ca-key` are no-ops** — only `--ca-from-local` (→ `proxy_ca_pem`) actually ships a CA; a supplied cert path just emits a comment.
- **`cp:access-token` tag** holds the live bearer token in plaintext EC2 metadata (by-design parity with `sg va`, but readable via `ec2:DescribeTags` / CloudTrail).

---

## See also
- Spec + brief pack (above) · Sibling mitmproxy stacks: [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md)
