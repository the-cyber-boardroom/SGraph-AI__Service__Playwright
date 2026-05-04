# 03 — Sidecar Contract

The sidecar — the `Fast_API__Host__Control` running on every Node — is now a first-class sub-architecture. This brief documents its contract: ports, auth, CORS, API surface, and the partition between sidecar concerns vs control-plane concerns.

**Read this in full.** Both teams touch the sidecar. Backend builds it; frontend talks to it directly from the dashboard (iframe pattern for browser, fetch with `X-API-Key` for machine-to-machine).

---

## 1. Identity

| Property | Value |
|----------|-------|
| Package | `sg_compute/host_plane/` |
| Image | `docker/host-control/Dockerfile` (Alpine + Python 3.12 + uvicorn) |
| Port | **`:19009`** on the Node's public IP |
| Entry point | `uvicorn sg_compute.host_plane.fast_api.lambda_handler:_app` |
| Lifecycle | Auto-installed on every Node by `Section__Sidecar` (built in BV2.1) |
| Boot signal | `GET /health` returns 200 once the application is ready |

The sidecar runs **inside the Node**, alongside the spec's pods. It has access to the Node's Docker socket; it does NOT have AWS IAM credentials.

**Port history** (for the Librarian's port-stabilisation sweep):
- Original v0.1.140 brief: `:9000`.
- v0.1.154 sidecar briefs: `:19009`.
- v0.2.0 (this brief): **`:19009` is canonical**. Any reference to `:9000` is legacy and must be swept.

---

## 2. Auth model — three modes coexist

The sidecar accepts authenticated calls in three ways. **All three are needed** because the sidecar is consumed by both machine clients (the SP CLI control plane) and browsers (the dashboard's iframe pattern).

### 2.1 X-API-Key header (machine-to-machine)

Standard. Used by the SP CLI control plane when proxying calls and by any backend code calling the sidecar via `requests.get(..., headers={'X-API-Key': key})`.

### 2.2 Auth cookie (browser default)

Used by the iframe pattern. Cookie is set by `POST /auth/set-auth-cookie` (called from `GET /auth/set-cookie-form`). Cookie attributes:

| Attribute | Current value | v0.2 hardening (BV2.7) |
|-----------|---------------|------------------------|
| Name | `sg_api_key` | unchanged |
| `HttpOnly` | `false` | **flip to `true`** (R2 from code review) |
| `SameSite` | `Lax` | unchanged |
| `Secure` | depends on origin | force `true` once dashboard ships behind TLS |
| `Path` | `/` | unchanged |
| `Max-Age` | (session) | (session) |

Once the cookie is set, every request from the iframe automatically includes it. Subsequent fetches do not need to pass `X-API-Key` explicitly.

### 2.3 WS handshake via cookie (terminal stream)

The `WS /shell/stream` endpoint authenticates via the cookie sent during the WebSocket upgrade. This is why the iframe pattern matters — it ensures the cookie is in the same origin as the WS endpoint, so the browser sends it automatically.

**Pattern C (cookie auth)** is the v0.2 default. The original v0.1.154 brief proposed Option A (`?api_key=` query) and Option B (per-handler validation). Option A leaks the key in URL logs; Option B is fragile. Pattern C is what shipped and what stays.

### 2.4 Auth-free paths

Routes that bypass auth entirely (their security boundary is something else):

| Path | Reason |
|------|--------|
| `GET /health` | Liveness probe — no key needed |
| `GET /health/ready` | Readiness — same |
| `GET /docs` | Swagger UI — auth happens via `/docs-auth` |
| `GET /docs-auth?apikey=...` | Sets the cookie + redirects to `/docs` — the auth establishment endpoint |
| `GET /auth/set-cookie-form` | The HTML form — must load before auth is set |
| `POST /auth/set-auth-cookie` | The form's submit target — establishes auth |
| `GET /host/shell/page` | xterm.js terminal page — auth is provided via cookie set by the iframe parent |

Implemented as the `_AUTH_FREE_PATHS` set in `_Middleware`. Any new route MUST default to authenticated; carve-outs are explicit.

---

## 3. CORS contract

The sidecar's `Fast_API__Host__Control` mounts `CORSMiddleware` as the OUTERMOST layer. `_Middleware.dispatch()` also stamps CORS headers on every response it produces, so 401 responses don't lose CORS headers (which would otherwise look like a CORS error in the browser).

### 3.1 Current configuration

```python
CORSMiddleware(
    allow_origin_regex = r".*",
    allow_credentials  = True,
    allow_methods      = ["*"],
    allow_headers      = ["*"],
)
```

### 3.2 Risk flagged by code review

`allow_origin_regex=r".*"` + `allow_credentials=True` is a **credential-theft surface**: any malicious origin that the user visits can reflect their cookie back. With `samesite=lax` cookies, this is mitigated for cross-site nav but **not** for same-tab fetches from a malicious script. **R1 + R3 in code review.**

### 3.3 v0.2 hardening (BV2.7)

Three options, in order of preference:

1. **Lock the origin allowlist** to the dashboard's known origins (e.g. `https://admin.sgraph.ai`, `http://localhost:8000`).
2. **Cookie attribute hardening** (`HttpOnly=true`, `SameSite=Strict`) reduces theft surface even with reflective CORS.
3. **Document the threat model** — accept the risk explicitly with a security review entry — only if (1) is operationally infeasible.

**Architect call needed before BV2.7.** Default recommendation: option 1 + option 2 together.

---

## 4. API surface

All endpoints listed below are mounted on `Fast_API__Host__Control`. **`*` marks endpoints that require auth.**

### 4.1 Health

| Method | Path | Returns |
|--------|------|---------|
| GET | `/health` | `{ status: "ok" }` |
| GET | `/health/ready` | `{ status, ready_since, runtime: "docker"\|"podman" }` |

### 4.2 Auth

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/set-cookie-form` | HTML form — operator pastes API key |
| POST | `/auth/set-auth-cookie` | Sets the cookie + redirects |
| GET | `/docs-auth?apikey=...` | Convenience — sets cookie via query, redirects to `/docs` (used by the dashboard's iframe SwaggerUI pattern) |

### 4.3 Host status (*)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/host/status` | CPU%, mem MB, disk GB, uptime, pod_count |
| GET | `/host/runtime` | runtime name + version |
| GET | `/host/logs/boot` | tail of `/var/log/cloud-init-output.log` |

### 4.4 Pods (*)

| Method | Path | Action |
|--------|------|--------|
| GET | `/pods/list` | list all pods on this Node |
| POST | `/pods` | start a pod |
| GET | `/pods/{name}` | info |
| GET | `/pods/{name}/logs?tail=100` | log tail |
| GET | `/pods/{name}/stats` | live CPU/mem snapshot |
| POST | `/pods/{name}/stop` | stop |
| DELETE | `/pods/{name}` | remove |

**Compatibility aliases** (v0.2 deletes them):
- `GET /containers/list`, `GET /containers/{name}`, `GET /containers/{name}/logs`, `GET /containers/{name}/stats` — kept as aliases for the legacy UI panel; BV2.8 deletes after FV2.8 lands.

### 4.5 Shell (*)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/shell/execute` | One-shot command. Allowlist-gated by `Safe_Str__Shell__Command`. |
| WS | `/shell/stream` | Interactive PTY via `/bin/rbash`. **Cookie-authenticated only** — no `X-API-Key` (browser WebSocket can't send custom headers during upgrade). |
| GET | `/host/shell/page` | xterm.js terminal HTML — served unauthenticated; auth is via the cookie that the iframe parent already established. |

---

## 5. Sidecar vs control-plane boundary

The single most-asked architectural question: **which API does this route belong on?**

| Concern | Where it lives | Why |
|---------|----------------|-----|
| Provision a Node (EC2 RunInstances) | Control plane (`Fast_API__Compute`) | Needs IAM |
| List EC2 instances by tag | Control plane | Needs IAM |
| Get EC2 instance metadata (volumes, SGs) | Control plane | Needs IAM |
| Look up an AMI ID | Control plane | Needs IAM |
| Spin up / down a pod inside a Node | Sidecar | Needs Docker socket on the Node |
| Show the boot log of a Node | Sidecar | Reads `/var/log/cloud-init-output.log` on the Node |
| Run an allowlisted shell command on a Node | Sidecar | Same |
| Stream a terminal to the Node | Sidecar | Same |
| List the pods running on a Node | Sidecar | Reads from Docker socket |
| Show CPU / mem / disk stats of a Node | Sidecar | `psutil` on the Node |
| Show currently-installed runtime (docker / podman) | Sidecar | Local `shutil.which` |

**The rule:** If it needs IAM, it's the control plane. If it needs the Docker socket or local Node state, it's the sidecar. **BV2.7 enforces this in code** (the `Routes__Compute__Nodes` audit found business logic mixed in — clean refactor due there).

The error mode that motivated this rule: commit `1c96fbe` had to move `/ec2-info` from the sidecar to the SP CLI catalog because the sidecar tried to call `describe_instances` and failed (no IAM). **Don't repeat that.** When in doubt, the route lives on the control plane.

---

## 6. The iframe pattern

Why the dashboard talks to the sidecar via iframe instead of direct fetch:

### 6.1 The problem

The dashboard origin (e.g. `http://localhost:8000`) is different from each Node's sidecar origin (e.g. `http://1.2.3.4:19009`). Cross-origin WebSocket calls cannot send custom headers (no `X-API-Key`). Cross-origin fetch with credentials needs CORS + cookie permission, which works but every fetch must include the cookie explicitly.

### 6.2 The solution

The dashboard renders an `<iframe src="http://1.2.3.4:19009/host/shell/page">`. The iframe is **same-origin to the sidecar**. Once the iframe sets the auth cookie via the form, every subsequent request (including the WebSocket upgrade) sends the cookie automatically.

This pattern works for:
- **Terminal tab** — iframe to `/host/shell/page`.
- **Host API tab** — iframe to `/docs-auth?apikey=...` which redirects to `/docs` (Swagger UI).
- **Future tabs** — anything served by the sidecar that needs WebSocket or rapid-fire fetch with auth.

### 6.3 Authentication flow inside the iframe

1. Iframe loads (e.g. terminal page) — page is auth-free, renders the "🔑 Authenticate" button.
2. Operator clicks the button → iframe navigates to `/auth/set-cookie-form`.
3. Operator pastes API key (or it's pre-filled by URL parameter from the parent).
4. Form POSTs to `/auth/set-auth-cookie` → cookie is set on the sidecar origin → iframe redirects back to the original page.
5. Original page now has the cookie; WebSocket connects; everything works.

### 6.4 Hardening notes

- **Don't store the API key in the parent dashboard's localStorage** if the iframe can read it via postMessage — the API key has to live somewhere that's not exfiltratable by other dashboard origins. Currently it's read from the user's vault on demand (good).
- The cookie's `HttpOnly=true` flip in BV2.7 prevents JavaScript inside the iframe from reading the cookie back — defence in depth.
- `SameSite=Strict` would also help but breaks the iframe pattern (the cookie wouldn't be sent in iframe-context fetches). `SameSite=Lax` stays.

---

## 7. Test surface (BV2.7 fills gaps)

Code review found:

- ✅ `mitmproxy` spec has 12 tests including Routes coverage — model.
- ⚠ Sidecar itself has 31 host-plane tests but coverage of the new auth flow (`Routes__Host__Auth`, `Routes__Host__Docs`) is unverified.
- ❌ Compute control-plane tests use `unittest.mock.patch` (8 sites) — violates "no mocks" rule.

BV2.7 deliverables:

- In-memory test composition for `Fast_API__Host__Control` (drop the mocks).
- Unit tests for `Routes__Host__Auth` covering the cookie set/clear flow.
- Integration test: full iframe-cookie-WS flow simulated via httpx + websockets.
- Negative-path tests: 401 with no auth, 401 with wrong key, 401 retains CORS headers.

---

## 8. Frontend consumer surface (FV2 reference)

The dashboard (`sgraph_ai_service_playwright__api_site/`) talks to the sidecar from these components:

| Component | What it consumes |
|-----------|------------------|
| `sp-cli-host-shell` (in `_shared/`) | iframe to `/host/shell/page`; "🔑 Authenticate" loads `/auth/set-cookie-form` inside the iframe |
| `sp-cli-host-api-panel` (in `_shared/`) | iframe to `/docs-auth?apikey=...` |
| `sp-cli-nodes-view` Pods tab | `GET /pods/list` (or legacy `/containers/list`) |
| `sp-cli-nodes-view` Boot Log tab | `GET /host/logs/boot` |
| `sp-cli-nodes-view` Overview tab | `GET /host/status` (polled until READY, then stops — code-review confirmed correct cessation) |

`host_api_url` is **derived on the frontend** from `public_ip`: `http://{public_ip}:19009`. The handover doc's recommended fallback is now the canonical path. `Schema__Node__Info` does not carry `host_api_url` — frontend constructs it.

---

## 9. Summary checklist for v0.2

What ships when v0.2.0 closes (per the BV2.x and FV2.x plans):

- [x] Sidecar exists at `sg_compute/host_plane/` (already shipped)
- [x] Auth-free paths established (already shipped)
- [x] CORS layer outermost (already shipped)
- [x] Cookie pattern with `samesite=lax` (already shipped)
- [ ] **`Section__Sidecar` user-data composable** — installs the sidecar uniformly (BV2.1)
- [ ] **`HttpOnly=true`** on the auth cookie (BV2.7)
- [ ] **Origin allowlist** instead of `r".*"` (BV2.7)
- [ ] **Pod__Manager + Routes__Compute__Pods** on the control plane (BV2.2) — bridges sidecar pod APIs to the unified `/api/nodes/{id}/pods/*` shape
- [ ] **`Routes__Host__Auth` test coverage** + drop the `unittest.mock.patch` violations (BV2.7)
- [ ] **Sidecar vs control-plane boundary** documented in code review checklist (BV2.7)
- [ ] **Port stabilisation sweep** — `:9000` → `:19009` everywhere (Librarian B-014)
- [ ] **`/containers/*` aliases deleted** after FV2.8 lands (BV2.8)
