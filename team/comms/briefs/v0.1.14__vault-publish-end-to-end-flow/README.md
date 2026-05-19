# Brief: `sg vp` — end-to-end working state

**Version:** vault-publish package `v0.1.14`  (service `v0.2.31`)
**Date:** 2026-05-19
**Audience:** Architect, Dev, Librarian, future-Claude
**Status:** REALITY — every command listed below has been run end-to-end against
a live AWS account during this session, producing a browser-reachable
`https://<slug>.aws.sg-labs.app/` with a valid Let's Encrypt cert.

A pragmatic snapshot of the vault-publish surface as it exists right now.
Useful as the entry point for anyone touching this code next — diagnostic
verbs, debug RPCs, and three working orchestrations are all listed below.

---

## 1. The three working flows

### 1a. Greenfield: provision a new slug end-to-end

```bash
sg vp register <slug> --vault-key <key> --wait
```

What it does in order:

1. Detects the live waker Lambda's deploy region; **aborts with exit 2** if
   `--region` differs (`--force-region-mismatch` overrides). Prevents the
   "EC2 lands in us-east-1, waker in eu-west-2" silent breakage.
2. Prints the underlying `Vault_App__Service.create_stack(...)` call shape
   so the operator sees exactly what's being invoked.
3. Calls `Vault_App__Service.create_stack` with
   `tls_mode='letsencrypt-hostname'`, `tls_hostname=<fqdn>`,
   `with_aws_dns=True` — the EC2 is provisioned with DNS in place so the
   boot-time `cert-init` container can complete LE HTTP-01 first try.
4. Tags the new instance with `sg:slug` / `sg:fqdn` / `sg:zone` via
   `Slug__Registry.put`.
5. With `--wait`: three-phase poll —
   - Phase 1 — `Endpoint__Resolver__EC2` until state RUNNING + public IP
   - Phase 2 — in-VPC HTTP probe on `:8080/ui/` until status<500
   - Phase 3 — **external HTTPS probe** of `https://<fqdn>/` with strict cert
     validation; on failure, auto-invokes `cert-renew --mode letsencrypt-hostname
     --hostname=<fqdn>` (covers the race where LE rate-limits or DNS hasn't
     propagated by boot time).

### 1b. Adopt an existing EC2 (created via `sg va create`)

```bash
sg vp adopt <slug>
```

Counterpart to `register` for instances that already exist outside the
vault-publish flow (`sg va create --name <slug>` is the common case — it
doesn't add the routing tags or per-slug DNS, and defaults to
`letsencrypt-ip` mode which the `.app` HSTS preload list rejects in
browsers).

The single command does:

1. Scan `WAKER_SCAN_REGIONS` (defaulting to deploy region + eu-west-2 / us-east-1
   / us-west-2 / eu-west-1) for an EC2 with **`tag:sg:slug` OR `tag:StackName`**
   matching the slug, plus `tag:StackType=vault-app`. First hit wins.
2. `ec2.create_tags` to add the missing `sg:slug` / `sg:fqdn` / `sg:zone`.
3. `Vault_App__Auto_DNS.run()` upserts a Route 53 A record for
   `<slug>.<zone> → <public-ip>`.
4. Patches `/opt/vault-app/.env` on the EC2 (via SSM SendCommand) to force
   `SG__CERT_INIT__MODE=letsencrypt-hostname` and
   `SG__CERT_INIT__TLS_HOSTNAME=<fqdn>`.
5. `docker compose up -d --force-recreate --no-deps cert-init` — **not**
   `restart` (see Gotchas §5.2).
6. Polls until cert-init exits 0; dumps cert-init logs once complete so the
   operator can verify the mode + hostname + LE success.
7. `docker compose restart --no-deps sg-send-vault` — vault reads `/certs/cert.pem`
   at process startup only; replacing the file on disk doesn't reload it.
8. Invokes the live Lambda's `/__waker__/cmd?name=cache-clear&slug=<slug>` so
   the next request through the waker re-scans tags.

Flags: `--skip-dns` / `--skip-cert` / `--skip-cache-clear` / `--cert-timeout 180`.

### 1c. Re-issue a cert on an existing slug

```bash
sg va cert-renew <stack> \
  --mode letsencrypt-hostname \
  --hostname <slug>.aws.sg-labs.app
```

For cert expiry / mode-mismatch repair / DNS-change scenarios that don't
need the tag-and-route work that `adopt` does. Same `.env` patch +
force-recreate cert-init + restart vault flow as adopt step 4-7.

---

## 2. Architecture at a glance

```
                       │  https://<slug>.<zone>/
                       ▼
                ┌─────────────┐
                │ Browser     │
                └──┬──────────┘
                   │  DNS resolves <slug>.<zone>:
                   │    A alias  → CloudFront wildcard (*.zone)
                   │    A record → EC2 IP (per-slug, set by register/adopt)
                   ▼
              ┌─────────────────┐
              │ CloudFront      │
              │  ALL viewer req │
              └──┬──────────────┘
                 │  CF Function (viewer-request, edge):
                 │   • copy Host  → X-Vault-Viewer-Host  (owned signal)
                 │   • copy Host  → X-Forwarded-Host     (interop)
                 │   • stamp X-Waker-Flow-Id (= event.context.requestId)
                 │   • stamp X-Waker-CF-Version (v0.0.3)
                 │   • stamp X-Waker-CF-Timestamp (millis since epoch)
                 ▼
        ┌─────────────────────┐
        │ Lambda Function URL │  (sg-compute-vault-publish-waker, eu-west-2)
        │ plain handler       │  lambda_entry.handler(event, context)
        │ no FastAPI/LWA      │  Schema__Waker__Request_Context
        └──┬──────────────────┘
           │  routes (in order):
           │  ┌─ /__waker__/health    JSON liveness
           │  ├─ /__waker__/deploy    JSON deploy metadata + schema check
           │  ├─ /__waker__/cmd?name= JSON debug RPC dispatcher
           │  ├─ /__waker__/console   HTML browser UI for /cmd
           │  ├─ /__waker__/status    HTML diag for a given slug
           │  └─ /*                   slug routing → resolve → wake/proxy/warm
           │
           │  Slug__From_Host extracts slug from X-Vault-Viewer-Host
           ▼
   ┌────────────────────────────┐
   │ Endpoint__Resolver__EC2    │
   │ multi-region scan          │  tag:sg:slug → fallback tag:StackName
   │ 60s in-process cache       │  StackType=vault-app filter
   └──┬─────────────────────────┘
      │  resolve() returns EC2 + region; resolver computes vault_url:
      │    https://<ip>/    when StackTLS=true
      │    http://<ip>:8080 otherwise
      ▼
 ┌──────────────────────────────┐
 │ Waker__Handler state machine │
 │  state-table (slug + EC2):   │
 │    UNKNOWN              → 200 status page  ("Slug not registered")
 │    STOPPED + iid        → start_instances, 202 warming page
 │    PENDING / STOPPING   → 202 warming page
 │    RUNNING + healthy    → Endpoint__Proxy.proxy → upstream response
 │    RUNNING + 5xx        → upstream response (passthrough)
 │    RUNNING + unhealthy  → 200 warming page
 │  X-Waker-* headers stamped on every response
 │  JSON log line emitted to CloudWatch
 └──┬───────────────────────────┘
    │  when proxying:
    ▼
 ┌────────────────────────────────────┐
 │ EC2 vault-app stack                │  eu-west-2 (matches waker)
 │  cert-init container (one-shot)    │  → /certs/cert.pem (LE-issued, FQDN-CN)
 │  sg-send-vault container :443      │  → reads /certs at startup
 │  host-control sidecar :19009       │  → admin HTTP API (not yet used by waker)
 │  tags: sg:slug, sg:fqdn, sg:zone,  │
 │        StackName, StackType=vault-app
 └────────────────────────────────────┘
```

---

## 3. Key components

### Deployed Lambda (`sg-compute-vault-publish-waker`)

| File | Role |
|---|---|
| `sg_compute_specs/vault_publish/waker/lambda_entry.py` | **Canonical handler.** No FastAPI / no LWA. Parses Function URL v2.0 events, routes, dispatches. Reads env into `DEPLOY_INFO` at cold-start. |
| `sg_compute_specs/vault_publish/waker/Fast_API__Waker.py` | **Local-only.** Kept for `uvicorn` testing; NOT what runs in AWS. |
| `sg_compute_specs/vault_publish/waker/Waker__Handler.py` | State machine + diagnostic 200 page render. |
| `sg_compute_specs/vault_publish/waker/Warming__Page.py` | "Vault is warming up" HTML — cancel button + diag link + console link + 30-attempt cap with sessionStorage counter. |
| `sg_compute_specs/vault_publish/waker/Waker__Console.py` | Self-contained HTML+JS browser UI for `/__waker__/cmd`. |
| `sg_compute_specs/vault_publish/waker/Waker__Commands.py` | RPC dispatcher — 16 commands today. Decorator-registered, gate-controlled. |
| `sg_compute_specs/vault_publish/waker/Endpoint__Resolver__EC2.py` | Multi-region tag-scan resolver. StackName fallback. 60s cache. |
| `sg_compute_specs/vault_publish/service/Slug__Registry.py` | EC2-tag-backed slug registry (NO SSM Parameter Store). |
| `sg_compute_specs/vault_publish/version` | `v0.1.14` — bumped on every Lambda runtime code change (rule documented in `Setup__Lambda` header). |

### CloudFront Function

| Name | Stage | Version | Purpose |
|---|---|---|---|
| `vault-publish-viewer-host` | LIVE | `v0.0.3` (in `Setup__CF__Function.FUNCTION_VERSION`) | Set X-Vault-Viewer-Host + X-Forwarded-Host + 3 tracing headers on viewer-request. |

### Setup areas (`sg vp setup ...`)

| Area | Verbs | Status |
|---|---|---|
| `ec2` | check/status | read-only prereq check (`playwright-ec2` profile + AL2023 AMI) |
| `iam` | check/status/create/update/delete | waker execution role |
| `lambda` | check/status/create/update/delete/invoke/cmd | runtime |
| `cf` | check/status/create | wildcard distribution |
| `cf-function` | check/status/create/update/delete/show | viewer-host shim |
| `acm` | check/status/request | wildcard certificate |
| `dns` | check/status/create/delete | wildcard A-alias |

Global verbs run all areas in dependency order: `check`, `create`, `update`, `delete`.

---

## 4. Debugging surfaces

### CLI

| Command | When to use |
|---|---|
| `sg vp setup check` | Top-level "is everything wired" — rich.live table with per-area progress |
| `sg vp setup lambda update --invoke` | Redeploy + auto-`/__waker__/deploy` to confirm version |
| `sg vp setup lambda cmd <name> [k=v ...]` | Invoke any of the 16 RPC commands |
| `sg vp setup lambda cmd help` | Table of all available commands with mutates marker |
| `sg vp wake <slug>` | Mirror the Lambda's wake flow from the CLI |
| `sg vp dns <slug>` | Route 53 record + dig-equivalent inspection |
| `sg vp eval <slug>` | 7-step end-to-end smoke test |
| `sg vp adopt <slug>` | Onboard an instance created outside vault-publish |
| `sg va cert-renew <stack> --mode --hostname` | Re-issue LE cert (mode+hostname overrides) |

### Lambda routes — accessible via browser OR `sg vp setup lambda invoke --path`

| Path | Returns | Notes |
|---|---|---|
| `/__waker__/health` | JSON `{status, service, version, service_version}` | No AWS call |
| `/__waker__/deploy` | JSON `{deploy_info, has_field}` | Schema-field smoke check confirms which deploy is live |
| `/__waker__/cmd?name=<cmd>` | JSON `{cmd, args, result}` | Gated by `WAKER_CMD_ENABLED=1` |
| `/__waker__/console` | HTML | Browser UI for cmd RPC |
| `/__waker__/status?slug=<slug>` | HTML diag | Like the 200 page but for an arbitrary slug, no resolve side-effects |
| `/__waker__/docs` | n/a today | (`Fast_API__Waker` only — not on the plain handler) |

### Browser RPC commands (Console + CLI `cmd`)

Read-only: `help`, `health`, `env [pattern]`, `python-info`, `list-files`,
`read-file`, `regions`, `cache`, `find-slug`, `check-slug`,
`describe-instance`, `dns-query`, `http-get`.

Mutating (`WAKER_CMD_MUTATIONS_ENABLED=1`): `cache-clear [slug=]`, `tag-slug`,
`start-instance`.

---

## 5. Gotchas (real bugs we hit; documented so next-time-Claude doesn't repeat them)

### 5.1 — `.app` TLD is HSTS-preloaded
Browsers refuse plain HTTP and reject any cert mismatch with NO bypass.
Forced us to make the cert flow correct end-to-end before anything else
worked. `register` defaults to `letsencrypt-hostname` mode; `adopt` forces it.

### 5.2 — `docker compose restart` does NOT re-read `.env`
`${VAR:-default}` substitution in the compose template is resolved at compose-
parse time (`up`). `restart` re-uses the existing container's baked env.
Always use `up -d --force-recreate --no-deps <service>` when env values change.

### 5.3 — vault container holds the cert in memory
`sg-send-vault` reads `/certs/cert.pem` only at process startup. After
cert-init writes a fresh cert, the vault needs a `compose restart --no-deps
sg-send-vault` to load it.

### 5.4 — SSM SendCommand `TimeoutSeconds >= 30`
Minimum is 30. Caused a poll loop to fail with `ParamValidationError`.

### 5.5 — `sg va create` defaults to `letsencrypt-ip`
Issues a cert with `CN=<ip>` — useless for a `.app` HSTS hostname. `adopt`
forces the mode to `letsencrypt-hostname` and re-issues.

### 5.6 — Region mismatch is silent without the guard
`sg vp register` aborts (exit 2) if `--region` differs from the waker's
`WAKER_DEPLOY_REGION`. Override with `--force-region-mismatch`.

### 5.7 — CloudFront Function `restart`-vs-`create` is async
CF Function attach is fire-and-forget; edge propagation takes ~5 min.
`Setup__CF__Function.create` doesn't wait; check after a few minutes.

### 5.8 — botocore returns `FunctionCode` as a StreamingBody, not bytes
`CloudFront__Function__AWS__Client.get_code` must `.read()` it. Falling
through to `str(raw)` produced `<botocore.response.StreamingBody object at …>`
and silently broke every CF Function drift check.

### 5.9 — Lambda handler architecture is `lambda_entry.py`, NOT `Fast_API__Waker.py`
Both files exist. The plain handler runs in AWS. `Fast_API__Waker.py` is for
local uvicorn testing only. Any runtime behaviour change must go in
`lambda_entry.py` AND its dependencies.

### 5.10 — SSM Parameter Store is fully removed for slug routing
Slug→EC2 lookup is via EC2 tags only. The only remaining `ssm:GetParameter`
calls are for the AWS-public AL2023 AMI parameter, which can't be moved
(read-only convention). `ssm:SendCommand` (Run Command) is still used for
container ops on EC2 — distinct service, different concerns.

---

## 6. Versioning policy (recap)

| File | Bumped by | Today | Trigger |
|---|---|---|---|
| `/version` | CI on merge to `dev` | `v0.2.31` | Every PR |
| `sg_compute_specs/vault_publish/version` | **Manually by agent** | `v0.1.14` | Every change to Lambda runtime code (anything in `vault_publish/waker/` or schemas referenced by `lambda_entry`/`Waker__Handler`). Documented in `Setup__Lambda.py` header. |
| `Setup__CF__Function.FUNCTION_VERSION` | Manually | `v0.0.3` | Every JS change in the CF Function code embedded as a Python string |

---

## 7. What's not yet done (carry-forward)

| Item | Notes |
|---|---|
| **Decoupling** (per-slug `port` / `health_path` / `warming_label` in the EC2 tags) | Brief 02 of `v0.2.29__brief__decoupling-and-eval-cli` proposed this. Today `vault_url` is hard-coded `https://<ip>/` (TLS) or `http://<ip>:8080` (no-TLS). |
| **Reverse-proxy mode** (always-proxy `/.well-known/acme-challenge/*`) | Brief 04 of same. Not needed today because LE issuance happens at EC2 boot (when DNS is in place), but blocks the "issue cert lazily on first request" pattern. |
| **`sg vp eval` checklist on the diagnostic page** | We have `check-slug` RPC + the diagnostic 200 page. They should merge into a server-rendered checklist on the slug's status page. |
| **Removal of `Fast_API__Waker.py`** | Dead code in prod path, kept for local uvicorn. Could split into its own dev-only package. |
| **host-control HTTP API for cert ops** | When Fargate lands, SSM SendCommand isn't available. host-control could expose `/vault/cert-renew` (POST). |
| **CloudFront edge propagation waiter** | `setup cf-function update` returns immediately; ~5 min before changes are global. No CLI flag to wait. |
| **Removal of `bootstrap` command's service-level method** | CLI verb was removed in `0ea8659` but `Vault_Publish__Service.bootstrap()` still exists for backward compat. |

---

## 8. References

- `team/humans/dinis_cruz/claude-code-web/05/18/11/v0.2.29__brief__setup-architecture/` — initial setup architecture brief
- `team/humans/dinis_cruz/claude-code-web/05/18/11/v0.2.29__brief__decoupling-and-eval-cli/` — decoupling proposal + status update (file `07__status-update.md`)
- `team/humans/dinis_cruz/claude-code-web/05/18/11/v0.2.29__brief__ssm-usage-audit/README.md` — SSM Parameter Store removal rationale
- `team/humans/dinis_cruz/claude-code-web/05/18/10/v0.2.29__brief__waker-internals-ux-debug/` — debug-headers / structured-logs brief
- `team/comms/briefs/v0.1.140__host-control-plane/` — host-control HTTP API (future cert-ops home)
- Branch: `claude/waker-debug-clean-bRIbm` (this session's work; rebased on `dev` multiple times)
