---
title: "QA Vault-App — 01 — The substrate contract"
version: v0.2.19
date: 2026-05-15
audience: Dev / Architect picking up the next slice
---

# 01 — The substrate contract

This file is the **contract** the QA vault-app builds against. Everything
here is shipped and stable as of v0.2.19. The QA app should treat this
document as the interface — additions need updates here; removals are
breaking changes.

> v1 of this pack listed the same surface but framed it as "what exists
> today." v2 reframes the same surface as the substrate's *contract* —
> stable, depended-on, with one named follow-up (§5).

---

## 1. The one-command deploy

```bash
sp vault-app create --with-playwright --wait
```

Produces a fresh `t3.medium` EC2 host running:

```
                  public internet
                          │
            ┌─────────────┴──────────────┐
            ▼                            ▼
         :443                          :80
    sg-send-vault                  sg-playwright
   (HTTPS, real LE                (HTTP, browser
    IP cert — browser-trusted)     automation API)
            │                            │
            │                            │
            │       vault-net (bridge)
            │                            │
       /data volume    agent-mitmproxy ←┐
       (vault store)   (CONNECT :8080,  │
                        mitmweb :8081)  │
                                        │
                                  host-plane
                            (admin API, docker socket,
                             :19009 localhost-only on host)
```

**Defaults:** TLS-on for the vault with a real Let's Encrypt **IP**
certificate (the bleeding-edge `shortlived` profile, ~6-day validity);
recreate-on-expiry by design (no renewal). Opt out via
`--no-with-tls-check` (plain HTTP on `:8080`, no cert sidecar). The
Playwright API is always plain HTTP on port 80 — chosen specifically so
Claude sandboxes and other egress-restricted environments (which only
allow standard ports) can reach it.

---

## 2. External surface

What the QA app's clients (and external agents) see:

| Port | Bound to | Protocol | What | When |
|------|----------|----------|------|------|
| `:443`  | `0.0.0.0` | HTTPS | Vault UI + Send API. TLS terminated in the vault container itself via the §8.2 contract. | `--with-tls-check` (default) |
| `:80`   | `0.0.0.0` | HTTP  | Playwright REST API. **Standard port — sandbox-friendly.** | `--with-playwright` (after cert-init exits if TLS) |
| `:80`   | `0.0.0.0` | HTTP  | ACME http-01 challenge (cert-init only). Transient; the container exits and Playwright takes the port. | `--with-tls-check`, boot only |
| `:8080` | `0.0.0.0` | HTTP  | Vault UI plain HTTP fallback. | `--no-with-tls-check` only |

All of `:443`, `:80`, `:8080` are world-open in the SG. The actual gate
is the access token (§4) — same shape as exposing a token-gated API.

---

## 3. Internal surface (SSM port-forward only)

Bound to `127.0.0.1` on the EC2 host — not reachable from the internet,
only from a laptop after running `sp vault-app open <target>`:

| Local port | Container target | What |
|---|---|---|
| `:19009` | host-plane `:8000`       | `/containers/list`, `/host/shell/page`, `/auth/set-cookie-form`, … |
| `:19081` | agent-mitmproxy `:8000`  | Admin FastAPI; `/web/*` forwards to mitmweb on `:8081` |

`sp vault-app open host-plane` and `sp vault-app open mitmweb` are the
two intended entry points. Both wrap `aws ssm start-session
AWS-StartPortForwardingSession` and exec into the AWS CLI — Ctrl-C closes.

---

## 4. Auth — one secret, two headers

A single access token per stack, auto-generated at create. Same value is
exported as **both** `FAST_API__AUTH__API_KEY__VALUE` (the FastAPI gate)
and `SGRAPH_SEND__ACCESS_TOKEN` (the vault session token).

| Header | Required by | Notes |
|---|---|---|
| `X-API-Key`              | Every Playwright API call; every host-plane / mitmweb-admin call | The FastAPI middleware gate. |
| `x-sgraph-access-token`  | Every vault UI / Send API call | The vault's own session cookie or header. |

For most callers (and the QA runner), `X-API-Key` is the only header
that matters. The vault UI is the main consumer of the second header (via
its cookie-form flow).

The token is **tagged on the EC2 instance** as `AccessToken`, and shown
on `sp vault-app info`. Programmatic consumers can read it via
`describe-instances` without SSM-ing the box. **Caveat:** anyone with
`ec2:DescribeInstances` on the account can read it; the
ec2-tag-as-secret-distribution trade was a deliberate ops-vs-secrecy call.

---

## 5. The Playwright REST API — externally reachable

| What | Value |
|---|---|
| Base URL (external)  | `http://<public-ip>`  (port 80 — default, suffix omitted) |
| Base URL (internal)  | `http://sg-playwright:8000`  (over the docker bridge) |
| Auth                 | `X-API-Key: <access_token>` |
| Schema reference     | `library/guides/v0.2.6__playwright-api-for-agents.md` (self-contained agent guide) |

Key endpoints (full reference in the agent guide):

- `GET  /health/{info,status,capabilities}`
- `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}` — one-shot helpers
- `POST /screenshot/{screenshot,batch}` — JSON-wrapped screenshot
- `POST /sequence/execute` — **the orchestration endpoint** (multi-step). The QA app's main interaction point.
- `GET  /metrics` — Prometheus

The 16-verb step language (`navigate`, `click`, `fill`, `wait_for`,
`screenshot`, `evaluate`, `get_content`, `get_url`, etc.) is in
`Enum__Step__Action`. The QA app composes sequences from scenario steps
+ synthetic Wait_For/Get_Content for DOM assertions — see
`02__qa-app-design.md` §3.

---

## 6. The mitmproxy capture surface — ✅ with one follow-up

Every Chromium launched by `sg-playwright` is configured at launch time
with:

```yaml
SG_PLAYWRIGHT__DEFAULT_PROXY_URL:   http://agent-mitmproxy:8080
SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS: 'true'
```

So **100% of the browser's outbound HTTP/S traffic** is captured by
mitmproxy without the QA app having to do anything. The intercept script
is baked into the image; the default writes NDJSON to stdout (visible
via `sp vault-app logs -s mitmproxy`).

**Live admin UI**: `sp vault-app open mitmweb` → `http://localhost:19081/web/`
in a browser. The same access token works.

**🟡 The one substrate follow-up:** per-run *addressability*. The capture
exists; today it's not keyed by `run_id`. The QA app will inject
`X-SG-Run-Id: <run_id>` into every browser request, and a new endpoint —
`GET /capture/network-log/{run_id}` on the agent-mitmproxy admin FastAPI
— will return that run's flows as NDJSON. ~80 lines. Detail in
`02__qa-app-design.md` §5.

---

## 7. Vault storage — three modes, ready for any of them

`/data` backing is orthogonal to vault preload (which is `sgit clone` at
boot via `SG_VAULT_APP__SEED_VAULT_KEYS=k1,k2,…`):

| Backing | Configured via | When |
|---|---|---|
| Local disk (ephemeral)  | none — writable layer | dev / CI smoke |
| EBS volume              | `VAULT_DATA_PATH=/opt/vault-app/data` (the create default) | single-EC2 persistent |
| Native S3               | `SEND__STORAGE_MODE=s3` + AWS creds | multi-replica / shared |
| Mountpoint-for-S3       | bucket mount + bind into `/data` | POSIX-view-over-S3 |

Vault preload happens on first boot — clones are idempotent (skip-if-
exists). The QA vault's content (scenarios, environments) lives in the
preloaded vault; runs are written back into the same vault.

---

## 8. EC2 instance tags — readable without SSH

What `describe-instances` returns, ready for the QA app's deploy scripts:

| Tag | Value | Source |
|---|---|---|
| `StackName`           | Auto-generated stack name | create |
| `StackType`           | `vault-app`               | create |
| `StackEngine`         | `docker` or `podman`      | create |
| `StackWithPlaywright` | `true`/`false`            | create |
| `StackTLS`            | `true`/`false`            | create |
| `AccessToken`         | The shared stack secret   | create |
| `TerminateAt`         | ISO-8601 auto-terminate time | create |
| `CallerIP`            | Originator's IP           | create |

**Tag-driven QA-app deploys are practical**: read these tags from boto3,
construct the URL set and auth header, no SSM required.

---

## 9. CLI surface — every verb the QA app's deploy/maintenance scripts can call

| Command | Use |
|---|---|
| `sp vault-app create [--with-playwright] [--no-with-tls-check] [--wait]` | Launch a stack. TLS-prod-LE + playwright on port 80 by default. |
| `sp vault-app list`            | Enumerate stacks. |
| `sp vault-app info [name]`     | URLs, access token, cookie-form links. |
| `sp vault-app wait [name]`     | Block on health. Transitions-only output + stage-timings table. |
| `sp vault-app health [name]`   | Instant health probe (TLS-aware). |
| `sp vault-app diag [name]`     | Full boot checklist + suggested log sources. |
| `sp vault-app logs -s {boot,cloud-init,journal,cert-init,vault,mitmproxy} [-f] [name]` | Stream logs. `-f` to follow. |
| `sp vault-app exec [name] <cmd>` | Arbitrary shell via SSM. |
| `sp vault-app connect [name]`  | Interactive SSM session. |
| `sp vault-app open {host-plane,mitmweb} [name]` | SSM port-forward wrapped. |
| `sp vault-app cert {generate,inspect,show,check}` | Cert utilities + live `:443` probes. |
| `sp vault-app extend [name] --add-hours N` | Push out auto-terminate. |
| `sp vault-app recreate [name]` | Delete + same-shape create + wait + info. |
| `sp vault-app delete [name]`   | Terminate + clean up SG. |
| `sp vault-app ami {list,bake,delete,wait}` | Bake an AMI from a warm stack. |

Every verb auto-resolves the stack name when only one exists.

---

## 10. Test status, as of this branch on `dev`

- `sg_compute_specs/vault_app/tests/`: **63 passing**.
- `sg_compute__tests/platforms/tls/`: 17 on py3.11; 24 on py3.12 (acme-backed CSR builder verified against the real lib).
- `sg_compute__tests/fast_api/`: passing (Fast_API__TLS__Launcher + TestClient suite on 3.12).

The 14 pre-existing failures in `stacks/ollama/*` + `stacks/open_design/*` + `Section__Shutdown` were verified pre-existing via stash-compare; unrelated.

---

*Next: `02__qa-app-design.md` — the QA vault-app's own design, schemas, and slice plan.*
