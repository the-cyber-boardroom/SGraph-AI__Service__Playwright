# content-proxy — Reality Index

**Domain:** `content-proxy/` | **Last updated:** 2026-06-18 | **Maintained by:** Dev (landing) → Librarian (verify)
**Code-source basis:** `sg_compute_specs/content_proxy/` at package version `0.1.0` (branch `claude/clever-wozniak-r0dxkh`, not yet merged to `dev`).

The content-transformation proxy stack: a browser routes through **mitmproxy**, which forwards every HTML request/response to a **FastAPI MITM service** that injects a client-side transformation `<script>`; **sg-playwright** drives/QAs it; the **vault app** terminates `:443` + `/pw`. Two mitmproxy instances (ext basic-auth for humans, int no-auth for Playwright) into one workflow. Spec: [`library/docs/specs/v0.2.63__content-transformation-proxy-stack.md`](../../../../library/docs/specs/v0.2.63__content-transformation-proxy-stack.md). Brief pack: `team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/`.

---

## EXISTS (code-verified, 52 unit tests passing — no mocks)

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
- `Cli__Content_Proxy` (`Spec__CLI__Builder`): 8 standard verbs (`list/info/create/delete/wait/health/connect/exec`) + `ami`/`cert` groups + a **`local up|down|status`** group wrapping `docker compose` on the committed local stack. Registered in `sg_compute/cli/Cli__SG.py` as **`sg content-proxy`** (alias `cp`).

### Configurable proxy tool
- `Enum__Content_Proxy__Proxy__Tool` (MITMWEB | MITMDUMP). Create request defaults to **MITMDUMP** (prod-safe, no in-memory flow accumulation); the committed local compose + template default to **MITMWEB** (dev — TUI `/flows`).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md). The EC2 launch Service + CLI now EXIST (above). Remaining: **Textual screens + live `__TUI__Source`** (the render fns exist), **api/routes**, **deploy-via-pytest + real-Chromium integration**, **vault loading** (post-MVP), and **LE/ACM TLS wiring**. None unit-testable without docker/AWS.

---

## See also
- Spec + brief pack (above) · Sibling mitmproxy stacks: [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md)
