---
title: Vault Admin UI — browser-side equivalent of `sg vp`
date: 2026-05-19
authors: [vault-publish team]
status: draft / pre-implementation
target_version: v0.1.15
companion_briefs:
  - team/comms/briefs/v0.1.14__vault-publish-end-to-end-flow/README.md
  - team/comms/briefs/v0.1.14__browser-dns-pinning/README.md
---

# Why

Today every interaction with the vault-publish system requires a developer terminal:

- Operators run `sg vp register / unpublish / list / status / eval / dns` from a shell.
- The browser-facing surface is just the warming page + the vault UI itself.
- The waker exposes diagnostic surfaces (`/__waker__/status`, `/__waker__/console`) but
  these are read-only single-page dumps, not an operational UI.

We want a **browser UI** that:

1. Lets an operator (and eventually an authenticated end user) **inspect** the full state
   of the vault-publish system without touching a terminal.
2. Mirrors the existing `sg vp` verbs so behaviour stays consistent across CLI / UI.
3. Can run mutations (register, unpublish, adopt) when the user is authorised.
4. Is independent of any specific slug — it's the **control plane**, served at a stable
   well-known location.

The trigger for writing this down now: while building the JS-driven warming page we hit
browser DNS pinning hard. The right answer is to **poll the Lambda directly from a
cross-origin context** instead of polling the slug URL (which pins DNS). That requires
the Lambda to expose a CORS-enabled JSON status endpoint, which then becomes the
foundation that the full admin UI can build on. So this doc is also the "where we're
heading" view for the polling-architecture refactor.

---

# UX shape

## URL layout

```
https://waker.aws.sg-labs.app/                       — admin home (inventory)
https://waker.aws.sg-labs.app/slug/<slug>/           — per-slug page (status, diag, actions)
https://waker.aws.sg-labs.app/setup/                 — setup pieces (CF function, Lambda, R53 zone)
https://waker.aws.sg-labs.app/api/v1/list             — JSON: equivalent of `sg vp list`
https://waker.aws.sg-labs.app/api/v1/status?slug=X    — JSON: equivalent of `sg vp status`
https://waker.aws.sg-labs.app/api/v1/eval?slug=X      — JSON: equivalent of `sg vp eval` (per-step)
https://waker.aws.sg-labs.app/api/v1/dns?slug=X       — JSON: equivalent of `sg vp dns`
https://waker.aws.sg-labs.app/api/v1/register         — POST: mutation, gated
https://waker.aws.sg-labs.app/api/v1/unpublish        — POST: mutation, gated
https://waker.aws.sg-labs.app/api/v1/setup/<piece>    — GET: each setup-piece check
```

`waker.aws.sg-labs.app` is covered by the existing `*.aws.sg-labs.app` CF wildcard. We
reserve the slug `waker` in `Reserved__Slugs` — when `Slug__From_Host` extracts `waker`,
the waker routes the request to the admin app instead of looking up an EC2. `admin` is
left registerable by users (per 2026-05-19 decision — operators may want their own
vault at `admin.<their-zone>`, and the control plane already lives under its own name).

## Inventory page (`/`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SG/Vault — admin                                  region: eu-west-2 ▾  ⟳  │
├─────────────────────────────────────────────────────────────────────────────┤
│  slug         state    ec2-state  ip               fqdn                 ⚙   │
│  tls-test-2   ●  ok    running    18.132.206.81    tls-test-2.aws…     ⋯   │
│  tls-test-5   ●  ok    running     3.10.119.106    tls-test-5.aws…     ⋯   │
│  notls-test   ●  ok    running    13.40.112.237    notls-test.aws…     ⋯   │
│  brave-curie  ●  warn  pending    (waiting)        brave-curie.aws…    ⋯   │
│  hopper       ●  err   not_found  -                hopper.aws…         ⋯   │
└─────────────────────────────────────────────────────────────────────────────┘

  [ + Register new vault ]    [ Show setup pieces ]    [ Refresh ]
```

Each row maps to one entry from `Slug__Registry.list_all()`. Color-coded state:
- `ok` (green) = `proxied` waker-state on probe + per-slug DNS converged
- `warn` (yellow) = `warming` or DNS partially propagated
- `err` (red) = `not_found` / `error` / EC2 terminated

Clicking a slug opens the per-slug page.

## Per-slug page (`/slug/<slug>/`)

Mirrors `sg vp eval` 1:1 — same 7 steps, same colour coding, but interactive:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← tls-test-5     status: ●  ok          actions: [ Open ] [ Unpublish ]   │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. ✓  slug registered           instance tagged sg:slug=tls-test-5         │
│  2. ✓  ec2 instance present      i-0db5… state=running ip=3.10.119.106     │
│  3. ✓  direct IP reachable       https://3.10.119.106/ → 401 (147ms)        │
│  4. ✓  per-slug DNS record       A tls-test-5.aws.sg-labs.app → 3.10.…      │
│  5. ✓  public DNS resolves       tls-test-5.aws.sg-labs.app → 3.10.…        │
│  6. ✓  HTTPS via CloudFront      https://tls-test-5.aws…/ → 401 (170ms)     │
│  7. ✓  waker headers correct     state=proxied host=tls-test-5.aws…         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Recent waker activity (last 50 requests, polled every 30s)                 │
│  ...                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

Each step is independently re-runnable (click the ✓/✗ to re-test that step). All steps
shown stale ages if the last poll was > 30s ago.

## Setup pieces page (`/setup/`)

Mirrors `sg vp setup` (CF function, hosted zone, lambda, etc.). Per-piece check status
+ "redeploy" button (gated behind the mutation flag).

---

# API surface

## Read-side endpoints

All read endpoints are JSON, CORS-enabled (Access-Control-Allow-Origin: `*.aws.sg-labs.app`
or `*`), no auth. They map onto the existing service methods:

| Endpoint                                  | Implementation                                         | sg vp equivalent |
|-------------------------------------------|--------------------------------------------------------|------------------|
| `GET /api/v1/list`                        | `Vault_Publish__Service.list_slugs()`                  | `sg vp list`     |
| `GET /api/v1/status?slug=X`               | `Vault_Publish__Service.status(slug)`                  | `sg vp status`   |
| `GET /api/v1/eval?slug=X`                 | per-step assembly (same logic as `eval` CLI command)   | `sg vp eval`     |
| `GET /api/v1/dns?slug=X`                  | Route 53 / public resolver lookup                       | `sg vp dns`      |
| `GET /api/v1/setup/<piece>`               | dispatch to setup-piece's `.check()` method            | `sg vp setup * check` |
| `GET /api/v1/waker/health`                | already exists                                          | n/a              |
| `GET /api/v1/waker/deploy`                | already exists                                          | n/a              |

## Mutation endpoints

All POST, JSON body, behind an auth gate:

| Endpoint                                  | sg vp equivalent  | Mutation gate                                       |
|-------------------------------------------|-------------------|-----------------------------------------------------|
| `POST /api/v1/register`                   | `sg vp register`  | `SG_AWS__VAULT_PUBLISH__ADMIN_UI__ALLOW_MUTATIONS=1` + bearer token |
| `POST /api/v1/unpublish`                  | `sg vp unpublish` | same + bearer token                                 |
| `POST /api/v1/adopt`                      | `sg vp adopt`     | same                                                |
| `POST /api/v1/setup/<piece>/update`       | setup-piece update | same                                                |

Auth model for v0.1.15:

- **Read endpoints**: no auth. Public read is acceptable — no secrets exposed (vault keys
  are already redacted in `list_slugs` response).
- **Mutation endpoints**: bearer token in `Authorization: Bearer <token>` header. The
  token is set as the env var `WAKER_ADMIN_TOKEN` on the Lambda. The same token is
  printed once during `sg vp setup admin-token rotate`. There is no "user accounts" yet
  — single shared operator token for v0.1.15.

For v0.1.16 (later): switch to **AWS Cognito** + per-user IAM-mapped scopes, or **WebAuthn**
keys. Out of scope here.

---

# Cross-origin status endpoint — also fixes warming-page polling

The warming page's JS today polls `https://<slug>.aws.sg-labs.app/?_probe=…`. This is
exactly the URL whose DNS we're trying to let the browser un-pin. Every probe resets the
HTTP/1.1 keep-alive idle timer on the kept-alive socket to CloudFront, so the socket
never closes and the in-tab navigation always lands via Lambda.

We fix this by polling a **different origin** from the warming page. CORS headers on
the probe endpoint allow the slug-FQDN origin to read the response.

## Why we use the Lambda Function URL, not `waker.aws.sg-labs.app`

The intuitive choice would be to point the warming page at `waker.aws.sg-labs.app/probe`
— same parent zone, served by the same Lambda via the CF wildcard. **But this doesn't
defeat connection pinning.** Browsers (Chromium, Firefox, Safari) implement HTTP/2
**connection coalescing**: when two hostnames share a wildcard cert and resolve to
overlapping IPs, they reuse the same H2 connection. CloudFront serves both
`<slug>.aws.sg-labs.app` and `waker.aws.sg-labs.app` from the same edges with the same
`*.aws.sg-labs.app` cert — so Chrome would route the "cross-origin" probe down the
existing slug-FQDN H2 connection. We'd be polling the very connection we're trying to
let idle out.

The Lambda Function URL (`https://<uuid>.lambda-url.<region>.on.aws/`) has:
- A different IP block (AWS-managed Lambda endpoints, not CloudFront edges)
- A different cert (AWS-issued, scoped to `*.lambda-url.<region>.on.aws`)
- Therefore: no H2 coalescing with the slug FQDN connection.

That's the only browser-side mechanism that actually gives us an independent socket
pool slot. So the cross-origin polling target is and stays the Lambda Function URL,
discovered at deploy time and baked into the warming page via env var
`WAKER_LAMBDA_FUNCTION_URL`.

## What `waker.aws.sg-labs.app` IS for, then

It's the **admin/console** surface. Operators and humans visit it to view inventory,
poke at individual slugs, run setup checks. It does NOT carry the warming-page polling
traffic. Its routes are listed in the API surface table above.

When `Slug__From_Host` extracts `waker` from the host, the request bypasses the
slug-resolver state machine and goes to the admin app's routes instead. `waker` is
reserved in `Reserved__Slugs` so no user can register a vault under that name.

---

# Implementation order

## Phase 1 — JSON status endpoint + CORS (this slice)

- Add `GET /__waker__/probe?slug=X` to `Fast_API__Waker`. Returns the same payload the
  warming page needs: `{waker_state, ec2_state, instance_id, public_ip}` plus a
  CORS-allow header.
- Read `WAKER_LAMBDA_FUNCTION_URL` from env in `Warming__Page.render()` (set by
  `Setup__Lambda` at deploy time from the Function URL we already create).
- Update `Warming__Page` JS: poll the Lambda Function URL cross-origin, not the slug URL.
  Slug URL is NEVER hit until the final redirect.

That's the immediate fix. Smallest change, fixes the user-visible symptom.

## Phase 2 — admin subdomain + inventory page

- Reserve slug `waker` in `Reserved__Slugs` (DONE). Then update `Slug__From_Host` so
  that when the extracted slug is `waker`, the resolver short-circuits and the request
  is routed to the admin app routes instead of running the wake state machine.
- Add admin app routes to `Fast_API__Waker`:
  `GET /api/v1/list`, `GET /api/v1/status?slug=X`, `GET /api/v1/eval?slug=X`,
  `GET /` (HTML inventory).
- Plain HTML+vanilla-JS first; no framework. Render the table; refresh every 30s.

## Phase 3 — per-slug page + mutations

- `GET /slug/<slug>/` HTML page
- `POST /api/v1/register`, `POST /api/v1/unpublish` (gated)
- `WAKER_ADMIN_TOKEN` env var + `sg vp setup admin-token rotate`

## Phase 4 — setup pieces page

- `GET /setup/` HTML page
- `GET /api/v1/setup/<piece>` for each setup piece
- `POST /api/v1/setup/<piece>/update` (gated)

## Phase 5 — auth upgrade

Cognito / WebAuthn, out of scope for this plan.

---

# Open questions

- **Auth before public IP?** Read endpoints are exposed at `*.aws.sg-labs.app` which is
  public. The list response redacts vault keys but does expose slug names + EC2 IPs.
  Is that OK for v0.1.15? Decision needed before Phase 2.
- **CORS allowlist policy?** `Access-Control-Allow-Origin: *` is simplest but leaks
  status info to any origin. `https://*.aws.sg-labs.app` is what we actually need (same
  parent zone). FastAPI's CORSMiddleware can enforce.
- **Where does the admin UI live in the repo?** Probably `sg_compute_specs/vault_publish/admin/`
  with `Fast_API__Admin.py`, then mounted into the existing waker FastAPI app at
  `/__admin__/`. Keep one Lambda.
- **Should admin be a separate Lambda?** No, for v0.1.15. One Lambda, two app surfaces
  (waker for slugs, admin for `slug=admin`). If admin grows, split later.

---

# Acceptance for Phase 1 only (the one we want to do next)

- [ ] `GET https://<lambda-fn-url>/__waker__/probe?slug=X` returns JSON
  `{waker_state, ec2_state, instance_id, public_ip}` with `Access-Control-Allow-Origin`
  header allowing the slug FQDN's origin.
- [ ] `Warming__Page.render()` reads `WAKER_LAMBDA_FUNCTION_URL` env var and injects it
  into the JS config block.
- [ ] Warming-page JS uses `CFG.lambda_url + '/__waker__/probe?slug=' + CFG.slug` as the
  poll target — and falls back to the slug URL if `lambda_url` is empty (degraded mode,
  preserves backwards-compat for already-deployed Lambdas without the env var).
- [ ] No probe hits the slug FQDN until the final `window.location.replace()` / new-tab
  navigation, verified in DevTools Network panel.
