---
title: vp-admin Lambda split — separate CF distribution, own ACM cert, own Lambda
date: 2026-05-19
authors: [vault-publish team]
status: approved / ready to implement
target_version: v0.1.16
companion:
  - team/comms/plans/v0.1.15__vault-admin-ui/README.md  (Phase 1-4 admin UI work — superseded by this plan's structural change)
  - library/docs/research/v0.1.14__http2-connection-coalescing.md  (the underlying constraint)
---

# Goal

Move the admin / control-plane surface to **its own Lambda + its own CloudFront
distribution + its own ACM cert**, served from `vp-admin.aws.sg-labs.app`. This:

1. **Definitively defeats H2 connection coalescing** for the warming-page status
   poll path — the admin host's cert and IPs no longer overlap with the slug
   FQDN's. The polling traffic on `vp-admin.aws.sg-labs.app/api/v1/status` cannot
   coalesce onto the slug's pinned socket regardless of browser behaviour.
2. **Cleans up dead code in the waker Lambda** — the existing `Fast_API__Waker`
   class, the CORSMiddleware on it, and the admin mount become unnecessary once
   admin moves out. `lambda_entry.py` shrinks back to a pure plain-handler.
3. **Lets admin grow independently** — different IAM scope, different memory /
   timeout, different deploy cadence.
4. **Reflects that this is vault-publish admin, not a top-level vault admin** —
   the name `admin.aws.sg-labs.app` is intentionally reserved for a future
   top-level admin that could span vault-app, vault-publish, future
   vault-something. The current scope is publish-specific (slugs, waker, DNS,
   CF) so the name is too.

# Decisions (made)

| Decision | Value |
|----------|-------|
| Admin host | `vp-admin.aws.sg-labs.app` (NOT the generic `admin.*` — reserved for future top-level admin) |
| Lambda split | Yes — separate Lambda from waker |
| Public read endpoint | `GET /api/v1/status?slug=X` — no auth, CORS allow `*.aws.sg-labs.app` |
| Naming | `admin` under vault-publish (not `config` / `setup` / `info` / `ops` / `console`) |
| Code location | `sg_compute_specs/vault_publish/lambdas/{waker,admin}/` — grouped Lambda deployment units |
| CLI namespace | Flat siblings under `sg vp setup admin-*` (preserves existing `sg vp setup lambda/cf/dns/iam` names) |
| Security tradeoff for public read | Accepted — slug names + EC2 IPs + states already discoverable via DNS / CF logs |

# Architecture

```
                         ┌──────────────────────────────────────────────────────┐
                         │ ACM cert: vp-admin.aws.sg-labs.app (single-host)     │
                         │ ⚠ MUST NOT include *.aws.sg-labs.app in SAN —        │
                         │ otherwise H2 coalescing returns                      │
                         └──────────────────────────────────────────────────────┘
                                              │
                                              ▼
  vp-admin.aws.sg-labs.app  →  CF distribution (sg-compute-vault-publish-admin-cf)
                                                     │
                                                     ▼
                                                Lambda Function URL
                                                     │
                                                     ▼
                                  Lambda: sg-compute-vault-publish-admin
                                          (lambdas/admin/lambda_entry.py)
                                                     │
                                                     ├─ FastAPI app via Lambda_To_ASGI
                                                     │   ├─ /                (HTML inventory — auth-gated)
                                                     │   ├─ /slug/<slug>/    (per-slug HTML — auth-gated)
                                                     │   ├─ /setup/          (setup pieces — auth-gated)
                                                     │   ├─ /login           (form + POST)
                                                     │   ├─ /logout
                                                     │   ├─ /api/v1/list     (JSON — auth-gated)
                                                     │   ├─ /api/v1/status   (JSON — PUBLIC + CORS)
                                                     │   ├─ /api/v1/eval     (JSON — auth-gated)
                                                     │   └─ /api/v1/register, /unpublish (JSON POST — auth-gated)
                                                     │
                                                     └─ IAM: ec2:Run/Describe/Terminate,
                                                            route53:Change*, lambda:GetFunction*,
                                                            ec2:Describe* (cross-region scan)


  *.aws.sg-labs.app  →  CF distribution (sg-compute-vault-publish-cf, existing)
                                          │
                                          ▼
                                Lambda: sg-compute-vault-publish-waker
                                        (lambdas/waker/lambda_entry.py)
                                                     │
                                                     └─ ONLY slug routing + warming pages
                                                        (FastAPI / admin mount removed)
```

Both Lambdas live in the same monorepo under `sg_compute_specs/vault_publish/lambdas/`.
Shared types (`Schema__*`) and services (`Vault_App__Service`, `Vault_App__Auto_DNS`,
`Slug__Registry`) are imported by both — no code duplication.

# Cert constraint — the critical detail

`vp-admin.aws.sg-labs.app` is in the **same parent zone** as `<slug>.aws.sg-labs.app`.
The existing CloudFront wildcard cert (`*.aws.sg-labs.app`) covers it. **If we use that
wildcard cert on the admin CF distribution, H2 coalescing returns** — the browser would
see "existing connection's cert covers vp-admin.aws.sg-labs.app" even if the IPs
differed via a separate CF distribution.

Therefore the admin CF distribution **must** use a different cert. The chosen approach:

- **Single-host ACM cert** for just `vp-admin.aws.sg-labs.app`
- `Setup__Admin__CF` provisions this cert as part of `sg vp setup admin-cf create`
- An idempotent guard in the same setup piece will refuse to attach the wildcard cert if
  someone ever rewires it manually — preserves the coalescing-free property

# Public probe endpoint (the one that doesn't auth)

`GET /api/v1/status?slug=<slug>` returns the same JSON the existing
`/__waker__/probe` returns today:

```json
{
  "slug"        : "tls-test-1",
  "waker_state" : "proxied",
  "ec2_state"   : "running",
  "instance_id" : "i-002239d051e876b2a",
  "public_ip"   : "35.178.202.0",
  "region"      : "eu-west-2"
}
```

Response headers:
- `Access-Control-Allow-Origin: <echoed request Origin if it matches /https?://([a-z0-9-]+\.)*aws\.sg-labs\.app/, else null>`
- `Access-Control-Allow-Credentials: true`
- `Cache-Control: no-store`

The warming page in `lambdas/waker/` switches its `probe_target` from the
Lambda Function URL to `https://vp-admin.aws.sg-labs.app/api/v1/status` once
the admin CF distribution is live.

# Repo layout

```
sg_compute_specs/vault_publish/
├── lambdas/                                       ← NEW: deployment-unit grouping
│   ├── waker/                                     ← MOVED from vault_publish/waker/
│   │   ├── lambda_entry.py
│   │   ├── Waker__Handler.py
│   │   ├── Warming__Page.py
│   │   ├── Endpoint__Proxy.py
│   │   ├── Endpoint__Resolver.py
│   │   ├── Endpoint__Resolver__EC2.py
│   │   ├── Slug__From_Host.py
│   │   ├── Waker__Commands.py
│   │   ├── Waker__Console.py
│   │   ├── schemas/
│   │   └── tests/
│   └── admin/                                     ← MOVED from vault_publish/admin/
│       ├── lambda_entry.py                        ← NEW (own Lambda handler)
│       ├── Lambda_To_ASGI.py                      ← MOVED from waker/ (deleted from waker)
│       ├── Fast_API__Admin.py
│       ├── Admin__Auth.py
│       ├── Admin__Pages.py
│       └── tests/
├── service/                                       ← unchanged (Vault_Publish__Service, Slug__Registry, etc.)
├── schemas/                                       ← unchanged
├── cli/                                           ← unchanged (sg vp register/unpublish/etc.)
├── setup/
│   ├── service/
│   │   ├── Setup__Lambda.py                       ← existing (waker — kept name, no rename)
│   │   ├── Setup__CF.py                           ← existing (waker CF)
│   │   ├── Setup__CF__Function.py                 ← existing
│   │   ├── Setup__DNS.py                          ← existing (slug zone records)
│   │   ├── Setup__IAM.py                          ← existing (waker role)
│   │   ├── Setup__Admin__Lambda.py                ← NEW
│   │   ├── Setup__Admin__CF.py                    ← NEW (includes single-host ACM cert)
│   │   ├── Setup__Admin__DNS.py                   ← NEW (vp-admin.aws.sg-labs.app → admin CF)
│   │   └── Setup__Admin__IAM.py                   ← NEW (separate role with broader perms)
│   ├── schemas/                                   ← extended with Schema__Setup__Admin__*__Report
│   └── cli/Cli__Setup.py                          ← adds admin-* subcommands
├── waker/                                         ← REMOVED after Phase 1 (moved to lambdas/waker/)
└── admin/                                         ← REMOVED after Phase 1 (moved to lambdas/admin/)
```

# CLI surface

Flat siblings under `sg vp setup`, preserving the existing waker-Lambda command names
(no breaking change for any script that calls them today):

```
sg vp setup                          # overview — shows BOTH Lambdas + all their pieces
sg vp setup lambda           *       # waker Lambda  (existing)
sg vp setup cf               *       # waker CF      (existing)
sg vp setup cf-function      *       # CF Function   (existing)
sg vp setup dns              *       # slug zone records (existing)
sg vp setup iam              *       # waker role    (existing)
sg vp setup admin-lambda     *       # NEW — admin Lambda
sg vp setup admin-cf         *       # NEW — admin CF + single-host ACM cert
sg vp setup admin-dns        *       # NEW — vp-admin.aws.sg-labs.app record
sg vp setup admin-iam        *       # NEW — admin role (broader perms than waker)
```

# Phases

| Phase | Deliverable | Effort | Reversible? |
|-------|-------------|:------:|:-----------:|
| **1a** | Create `lambdas/waker/` and `lambdas/admin/` directories. Move existing files into them (`vault_publish/waker/` → `lambdas/waker/`, `vault_publish/admin/` → `lambdas/admin/`). Update all import paths across the repo (CLI, services, setup, tests). Pure refactor — no behaviour change, no deployment change. | small-medium | Yes (revert moves) |
| **1b** | `lambdas/admin/lambda_entry.py` — plain handler that imports the FastAPI app and dispatches all paths via `Lambda_To_ASGI`. Unit test that login + inventory render in-process. `Lambda_To_ASGI.py` moves from `lambdas/waker/` to `lambdas/admin/`. | small | Yes |
| **2** | `Setup__Admin__IAM` — provision the admin Lambda's role with scoped permissions (ec2:Run/Describe/Terminate, route53:Change*, lambda:GetFunction* for cross-region scan). `sg vp setup admin-iam check/create/update`. | small | Yes |
| **3** | `Setup__Admin__Lambda` — provision the admin Lambda + Function URL. Handler points at `lambdas.admin.lambda_entry.handler`. Env vars include the shared API key + zone config. `sg vp setup admin-lambda check/create/update`. | medium | Yes (`delete` reverses) |
| **4** | `Setup__Admin__CF` — provision single-host ACM cert + new CF distribution. Idempotent guard refuses the wildcard cert. `sg vp setup admin-cf check/create/update`. | medium | Yes |
| **5** | `Setup__Admin__DNS` — Route 53 A/Alias for `vp-admin.aws.sg-labs.app` → admin CF distribution. `sg vp setup admin-dns check/create/update`. | small | Yes |
| **6** | Warming page switches `probe_target` to `https://vp-admin.aws.sg-labs.app/api/v1/status`. Run the empirical Connection-ID test in DevTools (no coalescing). | small | Yes |
| **7** | Clean up dead code in `lambdas/waker/`: remove `Fast_API__Waker.py`, the `/__admin__/*` dispatch in `lambda_entry.py`, the `_FAST_API_APP` cache, the `WAKER_LAMBDA_FUNCTION_URL` env-var bake, the warming page's fallback paths that pointed at the waker Function URL. Waker package shrinks ~50-100ms cold-start. | small | Yes |
| **8** | `sg vp setup` overview now reports drift on BOTH Lambdas. CI / deploy pipelines updated to deploy both. | small | Yes |

# Cleanup list — dead code to remove in Phase 7

After the cutover, these are confirmed-unused in production:

- `sg_compute_specs/vault_publish/lambdas/waker/Fast_API__Waker.py` (entire file)
- `sg_compute_specs/vault_publish/lambdas/waker/Lambda_To_ASGI.py` (moved to admin in Phase 1b; remove the waker copy)
- In `lambdas/waker/lambda_entry.py`:
  - `_FAST_API_APP` / `_LAMBDA_TO_ASGI` module-level cache (~5 lines)
  - `_get_asgi_dispatcher()` helper
  - `if path == '/__admin__' or path.startswith('/__admin__/'):` short-circuit
- In `lambdas/waker/Warming__Page.py`:
  - The `lambda_url` fallback chain — `probe_target` becomes the admin URL only
  - The `WAKER_LAMBDA_FUNCTION_URL` env var read (no longer needed)
- In `setup/service/Setup__Lambda.py`:
  - The `WAKER_LAMBDA_FUNCTION_URL` env var bake (was used by Warming__Page; no longer needed)

Net effect: the waker Lambda's deployment package no longer pulls FastAPI / starlette /
anyio. Cold-start drops ~50-100ms. Code path simpler — `lambda_entry` is back to being
a pure plain-handler, ~150 lines.

# Tests to update / add

| File | Change |
|------|--------|
| `tests/.../test_Lambda_To_ASGI.py` (new) | Move from waker/tests to admin/tests; same body |
| `tests/.../test_Fast_API__Admin.py` | Update import path; verify login/inventory routes against the new `lambdas.admin.lambda_entry` |
| New: `tests/.../test_vault_admin__cors.py` | Verify `/api/v1/status` returns proper Allow-Origin echoing for same-zone subdomains, `null` otherwise |
| `tests/.../test_warming_page.py` | Update probe target expectation (now `vp-admin.aws.sg-labs.app`) |
| `tests/.../test_Setup__Admin__*.py` (new) | One per setup-piece, mirroring the existing waker setup tests |

# Acceptance criteria

After Phase 6 (cutover) lands:

- [ ] `dig vp-admin.aws.sg-labs.app` returns IPs distinct from `<slug>.aws.sg-labs.app`'s
      EC2-IP result (different CF distribution edges, not EC2 IP)
- [ ] Cert presented at `vp-admin.aws.sg-labs.app:443` has SAN containing ONLY
      `vp-admin.aws.sg-labs.app`, NOT the wildcard `*.aws.sg-labs.app`
- [ ] `curl -v https://vp-admin.aws.sg-labs.app/api/v1/status?slug=<live-slug>` returns
      JSON with the expected fields + CORS headers, in <200ms
- [ ] `curl -v https://vp-admin.aws.sg-labs.app/__admin__/login` returns the login HTML
- [ ] DevTools Network panel on `https://<slug>.aws.sg-labs.app/` during warming-page
      rendering shows probes going to `https://vp-admin.aws.sg-labs.app/api/v1/status`,
      with a **Connection ID different** from the document request (no coalescing)
- [ ] The warming-page redirect lands on the EC2 directly (no X-Waker-State on the
      response) **without** any settle-countdown wait — the pinning workaround becomes
      unnecessary
- [ ] `sg vp setup overview` reports both Lambdas; no admin-related drift on either

# Open questions (deferred to v0.1.17)

- HMAC signature on `/api/v1/status` to prevent slug enumeration — security tradeoff
  accepted in v0.1.16 (slugs + IPs aren't secrets)
- Cognito / WebAuthn / per-user auth (still single shared API key)
- Audit logging
- Mutation endpoints (register / unpublish via POST) — currently exists in
  `Fast_API__Admin` as read-only; will gain POST handlers

# Non-goals for this slice

- Renaming the existing `sg vp setup lambda` / `cf` / `dns` / `iam` to add a `waker-`
  prefix (breaking CLI change; not worth the churn — the admin pieces use `admin-*`
  prefix for symmetry and the absence of a prefix on the waker pieces is fine)
- Multi-region admin Lambda (single region for now)
- Shared `Lambda_To_ASGI` location at `sg_compute/core/` — keep one copy in
  `lambdas/admin/` until a third Lambda needs it
