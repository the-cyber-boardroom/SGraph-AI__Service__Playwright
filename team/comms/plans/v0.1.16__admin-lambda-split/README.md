---
title: Admin Lambda split — separate CF distribution, own ACM cert, own Lambda
date: 2026-05-19
authors: [vault-publish team]
status: draft / awaiting review
target_version: v0.1.16
companion:
  - team/comms/plans/v0.1.15__vault-admin-ui/README.md  (Phase 1-4 admin UI work — superseded by this plan's structural change)
  - library/docs/research/v0.1.14__http2-connection-coalescing.md  (the underlying constraint)
---

# Goal

Move the admin / control-plane surface to **its own Lambda + its own CloudFront
distribution + its own ACM cert**, served from `admin.aws.sg-labs.app`. This:

1. **Definitively defeats H2 connection coalescing** for the warming-page status
   poll path — the admin host's cert and IPs no longer overlap with the slug
   FQDN's. The polling traffic on `admin.aws.sg-labs.app/api/v1/status` cannot
   coalesce onto the slug's pinned socket regardless of browser behaviour.
2. **Cleans up dead code in the waker Lambda** — the existing `Fast_API__Waker`
   class, the CORSMiddleware on it, and the admin mount become unnecessary once
   admin moves out. `lambda_entry.py` shrinks back to a pure plain-handler.
3. **Lets admin grow independently** — different IAM scope, different memory /
   timeout, different deploy cadence.

# Decisions (already made)

| Decision | Value |
|----------|-------|
| Admin host | `admin.aws.sg-labs.app` |
| Lambda split | Yes — separate Lambda from waker |
| Public read endpoint | `GET /api/v1/status?slug=X` — no auth, CORS allow `*.aws.sg-labs.app` |
| Naming | `admin` (not `config` / `setup` / `info` / `ops` / `console`) |
| Security tradeoff for public read | Accepted — slug names + EC2 IPs + states already discoverable via DNS / CF logs |

# Architecture

```
                         ┌────────────────────────────────────────────────┐
                         │ ACM cert: admin.aws.sg-labs.app (single-host)  │
                         │ ⚠ MUST NOT include *.aws.sg-labs.app in SAN —  │
                         │ otherwise H2 coalescing returns                │
                         └────────────────────────────────────────────────┘
                                              │
                                              ▼
  admin.aws.sg-labs.app  →  CF distribution (sg-compute-admin)  →  Lambda Function URL
                                                                          │
                                                                          ▼
                                                                Lambda: sg-compute-admin
                                                                          │
                                                                          ├─ FastAPI app
                                                                          │   ├─ /                (HTML inventory — auth-gated)
                                                                          │   ├─ /slug/<slug>/    (per-slug HTML — auth-gated)
                                                                          │   ├─ /setup/         (setup pieces — auth-gated)
                                                                          │   ├─ /login          (form + POST)
                                                                          │   ├─ /logout
                                                                          │   ├─ /api/v1/list    (JSON — auth-gated)
                                                                          │   ├─ /api/v1/status  (JSON — PUBLIC + CORS)
                                                                          │   ├─ /api/v1/eval    (JSON — auth-gated)
                                                                          │   └─ /api/v1/register, /unpublish (JSON POST — auth-gated)
                                                                          │
                                                                          └─ IAM: ec2:Run/Describe/Terminate,
                                                                                 route53:Change*, lambda:GetFunction*,
                                                                                 ec2:Describe* (cross-region scan)


  *.aws.sg-labs.app  →  CF distribution (sg-compute-vault-publish, existing)  →  Lambda: sg-compute-vault-publish-waker
                                                                                            │
                                                                                            └─ ONLY slug routing + warming pages
                                                                                               (FastAPI / admin mount removed)
```

Both Lambdas live in the same monorepo. Shared types (`Schema__*`, services
like `Vault_App__Service`, `Vault_App__Auto_DNS`) are imported by both — no
code duplication.

# Cert constraint — the critical detail

`admin.aws.sg-labs.app` is in the **same parent zone** as `<slug>.aws.sg-labs.app`.
The CloudFront wildcard cert (`*.aws.sg-labs.app`) covers it. **If we use that
wildcard cert on the admin CF distribution, H2 coalescing returns** — the
browser would see "existing connection's cert covers admin.aws.sg-labs.app"
even if the IPs differed via a separate CF distribution.

Therefore the admin CF distribution **must** use a different cert. Two options:

- **Single-host ACM cert** for just `admin.aws.sg-labs.app` (recommended — simplest)
- **Separate wildcard** — out of scope, would also work but more management overhead

The `Setup__Admin__CF` provisioner will issue + attach the single-host cert
automatically. Operators don't have to think about it.

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

The warming page in `vault_publish` switches its `probe_target` from the
Lambda Function URL to `https://admin.aws.sg-labs.app/api/v1/status` once the
admin CF distribution is live.

# Repo layout

```
sg_compute_specs/
├── vault_admin/                                  ← NEW
│   ├── __init__.py
│   ├── version
│   ├── lambda_entry.py                           ← admin's own handler
│   ├── Lambda_To_ASGI.py                         ← moved from vault_publish/waker/
│   ├── Fast_API__Admin.py                        ← moved from vault_publish/admin/
│   ├── Admin__Auth.py                            ← moved
│   ├── Admin__Pages.py                           ← moved
│   ├── cli/
│   │   └── Cli__Vault_Admin.py                   ← new top-level `sg vad`
│   ├── setup/
│   │   ├── service/
│   │   │   ├── Setup__Admin__Lambda.py           ← new
│   │   │   ├── Setup__Admin__CF.py               ← new
│   │   │   └── Setup__Admin__DNS.py              ← new
│   │   └── cli/Cli__Setup.py                     ← `sg vad setup *`
│   └── tests/
│       └── ...
│
├── vault_publish/
│   ├── admin/                                    ← REMOVED in Phase 1 (moved to vault_admin)
│   │   ├── Admin__Auth.py
│   │   ├── Admin__Pages.py
│   │   └── Fast_API__Admin.py
│   ├── waker/
│   │   ├── Lambda_To_ASGI.py                     ← REMOVED in Phase 6 (no longer needed)
│   │   ├── Fast_API__Waker.py                    ← REMOVED in Phase 6 (dead code)
│   │   └── lambda_entry.py                       ← TRIMMED in Phase 6 (admin dispatch removed)
│   └── ...
```

# CLI surface

New top-level command group `sg vad` (vault-admin), parallel to `sg vp` and
`sg va`:

```
sg vad setup overview               # what exists, what's missing
sg vad setup lambda  {check,create,update,delete}
sg vad setup cf      {check,create,update,delete}     # includes ACM cert provisioning
sg vad setup dns     {check,create,update,delete}     # admin.aws.sg-labs.app → CF
sg vad status                       # health summary of the admin stack
sg vad logs                         # tail recent CloudWatch
sg vad open                         # `open https://admin.aws.sg-labs.app/__admin__/login`
```

# Phases

| Phase | Deliverable | Effort | Reversible? |
|-------|-------------|:------:|:-----------:|
| **1** | Move admin code into `sg_compute_specs/vault_admin/`. Update `Fast_API__Admin` imports. Standalone — not yet deployed; no behaviour change for prod. | small | Yes (revert moves) |
| **2** | `vault_admin/lambda_entry.py` — plain handler that imports the FastAPI app and dispatches all paths via `Lambda_To_ASGI`. Unit test that login + inventory render in-process. | small | Yes |
| **3** | `Setup__Admin__Lambda` — provision the second Lambda + Function URL + scoped IAM role. `sg vad setup lambda check/create/update`. | medium | Yes (`sg vad setup lambda delete`) |
| **4** | `Setup__Admin__CF` — provision single-host ACM cert + new CF distribution + viewer-host CF Function (similar to existing one). `sg vad setup cf check/create/update`. Includes the cert constraint check (must not be the wildcard). | medium | Yes |
| **5** | `Setup__Admin__DNS` — Route 53 A/Alias for `admin.aws.sg-labs.app` → admin CF distribution. `sg vad setup dns check/create/update`. | small | Yes |
| **6** | Warming page switches `probe_target` to `https://admin.aws.sg-labs.app/api/v1/status`. Run an empirical test confirming no coalescing (different Connection ID in DevTools). | small | Yes |
| **7** | Clean up dead code in `vault_publish/waker/`: remove `Lambda_To_ASGI.py`, `Fast_API__Waker.py`, the `/__admin__/*` dispatch in `lambda_entry.py`, the cached FastAPI app instance, the warming page's fallback paths that pointed at the lambda Function URL. | small | Yes |
| **8** | Decommission the admin sub-app from `vault_publish` entirely (vault_publish only does slug routing + warming pages after this). | small | Yes |

Phases 1-2 land code with no deployment changes — purely a refactor with the
old path still working. Phases 3-5 are AWS resource creation, each gated by
the existing `SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1` mutation flag.
Phase 6 is the cutover (one-line change in `Warming__Page`). Phase 7-8 are
cleanup.

# Cleanup list — dead code to remove in Phase 7-8

After the cutover, these are confirmed-unused in production and should be
deleted (not just left as dead code):

- `sg_compute_specs/vault_publish/waker/Fast_API__Waker.py` (entire file)
- `sg_compute_specs/vault_publish/waker/Lambda_To_ASGI.py` (entire file — moves to vault_admin in Phase 1, deleted from here in Phase 7)
- `sg_compute_specs/vault_publish/admin/` (entire directory — moved in Phase 1)
- In `lambda_entry.py`:
  - The `_FAST_API_APP` / `_LAMBDA_TO_ASGI` module-level cache (~5 lines)
  - The `_get_asgi_dispatcher()` helper
  - The `if path == '/__admin__' or path.startswith('/__admin__/'):` short-circuit
- In `Warming__Page.py`:
  - The `lambda_url` fallback chain — `probe_target` becomes a single value (admin URL)
  - The `WAKER_LAMBDA_FUNCTION_URL` env var read (no longer needed)
  - `Setup__Lambda` similarly stops baking that var

Net effect: the waker Lambda's deployment package shrinks (no FastAPI, no
starlette, no anyio dependency); cold-start time drops further (~50-100ms).

# Tests to update / add

| File | Change |
|------|--------|
| `tests/.../test_Lambda_To_ASGI.py` (new) | Move from `vault_publish/waker/tests/` to `vault_admin/tests/` |
| `tests/.../test_Fast_API__Admin.py` | Update import path; verify login/inventory routes against the new lambda_entry |
| New: `tests/.../test_vault_admin__cors.py` | Verify `/api/v1/status` returns proper Allow-Origin echoing for same-zone subdomains, `null` otherwise |
| `tests/.../test_warming_page.py` | Update probe target expectation (now admin.aws.sg-labs.app) |

# Acceptance criteria (Phase 6 — the cutover)

After the cutover, the following must hold:

- [ ] `dig admin.aws.sg-labs.app` returns IPs distinct from `dig <slug>.aws.sg-labs.app`'s
      EC2-IP result (different CF distribution edges, not EC2 IP)
- [ ] `curl -v https://admin.aws.sg-labs.app/api/v1/status?slug=<live-slug>` returns JSON
      with the expected fields + CORS headers, in <200ms
- [ ] `curl -v https://admin.aws.sg-labs.app/__admin__/login` returns the login HTML
- [ ] DevTools Network panel on `https://<slug>.aws.sg-labs.app/` (during warming-page
      rendering) shows probes going to `https://admin.aws.sg-labs.app/api/v1/status`,
      with a **Connection ID different** from the document request (no coalescing)
- [ ] The warming-page redirect lands on the EC2 directly (no X-Waker-State on the
      response) **without** any settle-countdown wait — the whole pinning workaround
      becomes unnecessary
- [ ] `sg vp setup` no longer reports any admin-related drift; `sg vad setup` is the
      sole admin manager

# Open questions for review

1. **CLI command group** — `sg vad` vs `sg admin` vs `sg vp setup admin-*`? Doc currently
   recommends `sg vad`; happy to change.
2. **ACM cert lifecycle** — should `Setup__Admin__CF` own the cert provisioning + renewal
   tracking, or should it be a separate `Setup__Admin__Cert` to mirror how other zones
   handle certs? Currently in-line for simplicity.
3. **Shared `Lambda_To_ASGI`** — move to a shared utils location (`sg_compute/core/lambda_adapter/`)
   or keep one copy in vault_admin? Phase 1 moves it; Phase 7 deletes the vault_publish copy.
   If a third service needs it later, we'll lift it then.
4. **HMAC signature on `/api/v1/status`** — defer to v0.1.17? The doc currently accepts
   the security tradeoff per your decision. Signature is a nice-to-have, not blocker.

# Non-goals for this slice

- Cognito / WebAuthn / per-user auth (still single shared API key, v0.1.15 model)
- Mutations beyond what already exists in `Fast_API__Admin` (register/unpublish stay
  unauthored until v0.1.17)
- Audit logging (defer to v0.1.18)
- Multi-region admin Lambda (single region for now; the warming-page probe goes
  cross-region implicitly via the CF distribution)
