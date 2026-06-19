# content-proxy — Reality Index

**Domain:** `content-proxy/` | **Last updated:** 2026-06-18 | **Maintained by:** Dev (landing) → Librarian (verify)
**Code-source basis:** `sg_compute_specs/content_proxy/` at package version `0.1.0` (branch `claude/clever-wozniak-r0dxkh`, not yet merged to `dev`).

The content-transformation proxy stack: a browser routes through **mitmproxy**, which forwards every HTML request/response to a **FastAPI MITM service** that injects a client-side transformation `<script>`; **sg-playwright** drives/QAs it; the **vault app** terminates `:443` + `/pw`. Two mitmproxy instances (ext basic-auth for humans, int no-auth for Playwright) into one workflow. Spec: [`library/docs/specs/v0.2.63__content-transformation-proxy-stack.md`](../../../../library/docs/specs/v0.2.63__content-transformation-proxy-stack.md). Brief pack: `team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/`.

---

## EXISTS (code-verified, 118 unit tests passing — no mocks)

### Spec skeleton (`sg_compute_specs/content_proxy/`)
- `manifest.py` — `MANIFEST` (`spec_id='content_proxy'`, caps `MITM_PROXY` + `BROWSER_AUTOMATION` + `REMOTE_SHELL`, `EXPERIMENTAL`). Conformance test green.
- `version` — `0.1.0`.
- **Enums:** `Mode` (DIRECT_PROXY/VAULT_WEB), `Tls` (NONE/LETSENCRYPT/ACM), `Vault__Kind` (ZIP/SGIT), `Flow__Action` (INJECTED/BLOCKED/CACHED/SKIPPED/FALLBACK/PASSED), `Proxy` (EXT/INT), `Stack__State`.
- **Primitives:** `Safe_Str__Content_Proxy__Stack__Name`, `Safe_Str__Content_Proxy__Ref` (paths/URIs/sgit), `Safe_Str__IP__Address`.
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
- `Cli__Content_Proxy` (`Spec__CLI__Builder`): 8 standard verbs (`list/info/create/delete/wait/health/connect/exec`) + `ami`/`cert` groups + a top-level **`smoke`** (runs the `/mitm-proxy` chain check on the EC2 box via SSM, no SSH) + create extras (`--env-file` ships a working `.env` verbatim, `--scripts-bucket`, `--forward-aws-creds`, `--proxy-tool`, `--tls`, `--proxyauth-*`, `--proxy-ca-*`) + a **`local up|down|status|logs|smoke|pull|ca`** group wrapping `docker compose` on the committed local stack (`smoke` = curl the `/mitm-proxy` chain check through mitmproxy-ext; `pull` = refresh `:latest`; `ca` = show the mitmproxy CA cert for browser import; `up --pull`). Registered in `sg_compute/cli/Cli__SG.py` as **`sg content-proxy`** (alias `cp`).

### Vault TLS on :443 (mirrors `sg va`)
- `Enum__Content_Proxy__Tls` = NONE / SELF_SIGNED / LETSENCRYPT (→ cert-init `letsencrypt-ip`) / ACM (ALB — not wired). When `tls != NONE` the compose adds a one-shot **`cert-init`** sidecar (`diniscruz/sg-host-control`, auto-detects the public IP via IMDS) that writes `/certs` to a shared `vault_certs` volume; the vault terminates TLS on :443 via `FAST_API__TLS__*`. LETSENCRYPT also opens/publishes `:80` (ACME http-01). `create` opens SG `:80` only for LETSENCRYPT. Health probe scheme follows the stack's tls (http for NONE, https for TLS).
- **Secrets:** one shared `SGRAPH_SEND__ACCESS_TOKEN` (vault auth + the sg-playwright `X-API-Key` the `/pw` proxy forwards — they must match) + `FASTAPI_API_KEY_VALUE` (interceptor↔mitm-service). `create` reuses both from a supplied `--env-file`, generating only when absent (surfaced once, labelled from-env vs generated).
- **Health via SSM:** `wait`/`health` probe the vault on the box (`localhost`) over SSM (`localhost_probe_command` + `parse_http_code`/`is_healthy_code`), not the external IP — robust against SG/caller-IP drift and self-signed TLS.
- **Interceptor** leaves `mitm.it` (mitmproxy onboarding/cert page) untouched.

### Front-door edge — Caddy (local + EC2)
- `Enum__Content_Proxy__Edge` (NONE | CADDY). `Content_Proxy__Edge__Template` renders a `Caddyfile`; `Compose__Template.render(edge=CADDY)` adds a `caddy` service that owns `:443` (TLS) and routes `/`→vault, `/pw/*`→sg-playwright (auth injected) — vault becomes a **plain origin** (no `serve_with_proxy` patch, no vault TLS, no cert-init). Committed `docker/compose/docker-compose.caddy.yml` + `Caddyfile` (drift-guarded); `sg cp local up --edge caddy`. Default path (NONE, vault-as-edge) unchanged. Rationale + options: `team/roles/architect/reviews/06/19/content_proxy__edge-front-door-options.md`.
- **Two site-address modes.** Local: the Caddyfile binds a **named** site `localhost, 127.0.0.1` + `tls internal` (a bare `:443` has no subject → Caddy aborts the handshake with `tlsv1 alert internal error`; the named site provisions the internal cert at startup). Hostname: `Edge__Template.render(hostname=<fqdn>, acme_email=…)` emits an `<fqdn> { … }` block and Caddy does **public auto-ACME** (http-01 on :80, tls-alpn on :443) — the cert external callers (Claude) trust. `edge_block(edge, hostname)` publishes `:80` (+ `:443`) on the caddy service only in hostname mode.
- **EC2 wiring (`--edge` / `--hostname` / `--with-aws-dns`).** Create request carries `edge` / `hostname` / `with_aws_dns`. `derive_fqdn(stack, request)` = explicit `--hostname` ⊳ `<stack>.sg-compute.sgraph.ai` (when `--with-aws-dns`, zone via `SG_AWS__DNS__DEFAULT_ZONE`) ⊳ blank; any FQDN forces `edge=CADDY`. `User_Data__Builder` writes the `Caddyfile` (hostname variant) to `/opt/content-proxy/` and drops the `/pw` override (edge routes it). `sg_rules(tls, edge, hostname)` opens `:443`+`:80` to the world for a public hostname (Claude reach + Caddy ACME); else caller-scoped. Tags `cp:edge` / `cp:hostname`; `Stack__Info` + mapper + renderer surface them (`https://<fqdn>/`). `--with-aws-dns` reuses the **sg va** Route 53 flow (`Vault_App__Auto_DNS`) via the CLI `post_launch_fn` (background thread, joined after `_wait_healthy`). Health probe uses `https` when the edge fronts TLS even if vault `tls=NONE`. `local up` now also back-fills missing keys into a stale `.env` from `.env.example`.

### Configurable proxy tool
- `Enum__Content_Proxy__Proxy__Tool` (MITMWEB | MITMDUMP). Create request defaults to **MITMDUMP** (prod-safe, no in-memory flow accumulation); the committed local compose + template default to **MITMWEB** (dev — TUI `/flows`).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md). The EC2 launch Service + CLI now EXIST (above). Remaining: **Textual screens + live `__TUI__Source`** (the render fns exist), **api/routes**, **deploy-via-pytest + real-Chromium integration**, **vault loading** (post-MVP), and **LE/ACM TLS wiring**. None unit-testable without docker/AWS.

---

## See also
- Spec + brief pack (above) · Sibling mitmproxy stacks: [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md)
