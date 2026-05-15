---
title: "QA Vault-App — 01 — What the substrate provides today"
version: v0.2.6
date: 2026-05-15
audience: Dev / Architect picking up the next slice
---

# 01 — What the substrate provides today

Everything below is **shipped on `claude/architect-qa-service-ijc61`** (and
merged to `dev` for the bits that landed earlier in the branch). The QA
vault-app proposed in `02__qa-app-design.md` consumes this surface without
adding to it.

---

## 1. The stack — one command, four containers + cert sidecar

```bash
sp vault-app create --with-playwright --wait
```

produces a fresh `t3.medium` EC2 host running:

```
                    public internet
                            │
              ┌─────────────┼──────────────────┐
              ▼             ▼                  ▼
           :443        :11024              :80 (boot-only)
       sg-send-vault  sg-playwright       cert-init
       (HTTPS, LE      (HTTP, browser     (ACME http-01,
        IP cert)        automation API)     exits 0)
              │             │
              │     vault-net (docker bridge)
              ▼             ▼
       /data volume   agent-mitmproxy ←┐
       (vault store)  (HTTP CONNECT     │
                       :8080,           │
                       mitmweb :8081)   │
                                        │
                                  host-plane
                            (admin API, docker socket,
                             :19009 localhost-only on host)
```

**External surface** (world-open in the SG, X-API-Key gated):

| Port | Host-published | Container target | What |
|------|---|---|---|
| `:443`  | `0.0.0.0:443:443`        | sg-send-vault uvicorn TLS | The vault — UI + Send API |
| `:11024`| `0.0.0.0:11024:8000`     | sg-playwright uvicorn HTTP | The browser-automation REST API |
| `:80`   | `0.0.0.0:80:80`          | cert-init http-01 listener | **boot-only**; cert-init exits and nothing listens after |

**Internal surface** (SSM port-forward only — bound to `127.0.0.1` on the EC2 host):

| Local port | Container target | What |
|---|---|---|
| `:19009` | host-plane `:8000`       | host admin: `/containers/list`, `/host/shell/page`, `/auth/set-cookie-form`, … |
| `:19081` | agent-mitmproxy `:8000`  | mitmproxy admin: `/web/*` forwards to mitmweb |

Reach the internal surfaces via `sp vault-app open host-plane` and
`sp vault-app open mitmweb`.

---

## 2. Auth — one secret, two headers

Single access token per stack, auto-generated at create or supplied via
`--access-token`. The same value is exported as **both**
`FAST_API__AUTH__API_KEY__VALUE` (the X-API-Key gate) and
`SGRAPH_SEND__ACCESS_TOKEN` (the vault session token). Most callers send
it as `X-API-Key`; the vault UI uses `x-sgraph-access-token` for its own
session cookie. Same value.

The token is tagged on the EC2 instance (`AccessToken` tag) and surfaced by
`sp vault-app info`'s `access-token` row — so the QA vault-app can read it
at boot via the IMDS metadata path the cert sidecar already uses, without
needing it baked into the image.

---

## 3. The CLI surface

Every verb the QA vault-app's deploy/maintenance scripts can call:

| Command | Use |
|---|---|
| `sp vault-app create [--with-playwright] [--no-with-tls-check] [--wait]` | Launch a stack. TLS-prod-LE by default. |
| `sp vault-app list`            | Enumerate stacks. |
| `sp vault-app info [name]`     | Resolved URL set, access token, cookie-form links, ssm-forward commands. |
| `sp vault-app wait [name]`     | Block on health; transitions-only output + stage timings. |
| `sp vault-app health [name]`   | Instant health probe. |
| `sp vault-app diag [name]`     | Full boot checklist + suggested log sources. |
| `sp vault-app logs -s {boot,cloud-init,journal,cert-init,vault,mitmproxy} [-f] [name]` | Stream logs. `--follow` for live tail. |
| `sp vault-app exec [name] <cmd>` | Arbitrary shell via SSM. |
| `sp vault-app connect [name]`  | Interactive SSM session. |
| `sp vault-app open {host-plane,mitmweb} [name]` | SSM port-forward wrapped; prints URL + cookie-form + ready message; Ctrl-C closes. |
| `sp vault-app cert {generate,inspect,show,check}` | Local cert utilities + live `:443` probes. |
| `sp vault-app extend [name] --add-hours N` | Push out auto-terminate. |
| `sp vault-app recreate [name]` | Delete + same-shape create + wait + info. |
| `sp vault-app delete [name]`   | Terminate + clean up SG. |
| `sp vault-app ami {list,bake,delete,wait}` | Bake an AMI from a warm stack for faster cold-starts. |

Every command auto-resolves the stack name when only one exists.

---

## 4. The Playwright REST API — externally reachable

After this branch, `sg-playwright`'s uvicorn `:8000` is host-published as
`:11024` and world-open in the SG. The QA vault-app calls it the same way
any external client would.

**Base:** `http://<public-ip>:11024`
**Auth:** `X-API-Key: <access_token>`
**Endpoint inventory** (full reference in `library/guides/v0.2.6__playwright-api-for-agents.md`):

- `GET  /health/{info,status,capabilities}`
- `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}` — one-shot helpers
- `POST /screenshot/{screenshot,batch}` — JSON-wrapped screenshot
- `POST /sequence/execute` — multi-step orchestration (the right endpoint for QA runs)
- `GET  /metrics` — Prometheus text

The 16-verb step language (`navigate`, `click`, `fill`, `wait_for`,
`screenshot`, `evaluate`, `get_content`, `get_url`, etc.) is documented in
the agent guide and grounded in `sg_compute_specs/playwright/core/schemas/enums/Enum__Step__Action.py`.

**Internal access** (vault → playwright on the docker bridge):
`http://sg-playwright:8000` — same `X-API-Key`, no port collision with the
host-published `:11024`. The QA vault-app should prefer the internal URL
when running on the same EC2.

---

## 5. The mitmproxy capture surface

Every Chromium launched by `sg-playwright` routes through `agent-mitmproxy`
on the docker network — set at launch time via:

```yaml
SG_PLAYWRIGHT__DEFAULT_PROXY_URL:   http://agent-mitmproxy:8080
SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS: 'true'
```

So **100% of the browser's outbound traffic is captured** without the QA
vault-app having to do anything special. mitmproxy's intercept script is
baked into the image; the default writes NDJSON to stdout (visible via
`sp vault-app logs -s mitmproxy`).

**What's NOT there yet** (per the v2 delta §10): a `/capture/network-log/{run_id}`
endpoint that returns the per-run network log keyed by an `X-SG-Run-Id`
header. The capture exists; it's not addressable per run. See §02 slice 4
for the proposed slice.

---

## 6. Vault storage — three modes, none assumed

Per the §02 design of the v2 delta, `/data` backing is orthogonal to vault
*content* preload:

| Backing | Compose config | Use |
|---|---|---|
| Local disk (ephemeral)  | none — writable layer | dev / CI smoke |
| EBS volume              | `VAULT_DATA_PATH=/opt/vault-app/data` (the create default) | single-EC2 persistent |
| Native S3               | `SEND__STORAGE_MODE=s3` + AWS creds | multi-replica / shared |
| Mountpoint-for-S3       | bucket mount + bind into `/data` | if a POSIX view is specifically needed |

Vault preload is via either bind-mount (vaults already on disk) or the
`SG_VAULT_APP__SEED_VAULT_KEYS=k1,k2,k3` env, which clones via `sgit clone`
on first boot. Both compose.

---

## 7. TLS posture — defaults that just work

After this branch:

| Default | Meaning |
|---|---|
| `--with-tls-check=true`   | cert-init sidecar runs; sg-send-vault binds `:443` with FAST_API__TLS__* |
| `--tls-mode=letsencrypt-ip` | Real Let's Encrypt cert for the EC2 public IP (no DNS required) |
| `--acme-prod=true`        | Production LE directory — browser-trusted; the `shortlived` ~6-day profile |

Opt-out: `--no-with-tls-check` for plain HTTP on `:8080` (Web Crypto won't
be available client-side — `window.isSecureContext` is `false`). The QA
vault-app should default to TLS-on for the secure-context features the
vault UI relies on.

§8.2 launch contract (`FAST_API__TLS__{ENABLED,CERT_FILE,KEY_FILE,PORT}`)
is documented in the closing debrief; the launcher is single-file and
ready to land in OSBot__Fast_API upstream.

---

## 8. Agent-facing docs

Three docs the QA vault-app's contributors will hand to a Claude session:

| Doc | What it covers | When to use |
|---|---|---|
| `library/guides/v0.2.6__playwright-api-for-agents.md` | Self-contained Playwright REST API guide — 11 endpoints, 16 step verbs, JS allowlist, full Python example | Hand to an agent driving the API |
| `team/comms/briefs/v0.2.6__vault-to-playwright-api.md` | Vault→Playwright shape — internal vs external URL, header pattern, network topology | Hand to anyone writing the vault-side caller |
| `team/comms/briefs/v0.2.6__sgit-cli-two-auth-headers.md` | The two-header auth requirement | Hand to the sgit CLI maintainers |

The QA vault-app design (`02__qa-app-design.md` in this pack) explicitly
points back at these — no duplication, no drift.

---

## 9. What is and isn't tagged on the EC2 instance

The QA vault-app's deploy scripts can read these tags from
`describe-instances` without SSM-ing the box:

| Tag | What | Source |
|---|---|---|
| `StackName`           | Auto-generated stack name (e.g. `swift-faraday`) | create |
| `StackType`           | `vault-app`                                       | create |
| `StackEngine`         | `docker` or `podman`                              | create |
| `StackWithPlaywright` | `true` if `--with-playwright`                     | create |
| `StackTLS`            | `true` if TLS enabled                             | create (new this branch) |
| `AccessToken`         | The shared stack secret                           | create (new this branch) |
| `TerminateAt`         | ISO-8601 auto-terminate time                      | create |
| `CallerIP`            | Originator's IP                                   | create |

**What's not tagged yet** (would be needed for a fully tag-driven QA-app
deploy without scraping `info`): `tls_mode`, `acme_prod`, `storage_mode`,
`disk_size_gb`, `instance_type`, `max_hours`. Schema today preserves them
in `Schema__Vault_App__Create__Request`; tags don't. If the QA vault-app
wants to recreate-with-exact-shape, this gap will need closing.

---

## 10. Test status as of this branch

Passing on `dev` (after merge):

- All `sg_compute_specs/vault_app/tests/` — 63 passing.
- All `sg_compute__tests/platforms/tls/` — 17 passing on py3.11; 24 on py3.12 (the acme-backed CSR builder verified against the real lib).
- All `sg_compute__tests/fast_api/` — passing (Fast_API__TLS__Launcher + the slim Fast_API__TLS app TestClient suite on 3.12).

Pre-existing failures untouched: 14 in `stacks/ollama/*` + `stacks/open_design/*` + `helpers/user_data/Section__Shutdown.py` (confirmed pre-existing via stash-compare; unrelated to this branch).

---

*Read `02__qa-app-design.md` next for the QA vault-app design itself.*
