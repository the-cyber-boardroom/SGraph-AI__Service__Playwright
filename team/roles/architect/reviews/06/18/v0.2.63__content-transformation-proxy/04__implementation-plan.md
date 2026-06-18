---
title: "Content-transformation proxy — Implementation plan"
file: 04__implementation-plan.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — phased slices + package layout + reuse map.
---

# Implementation plan

Build order is **bottom-up and demoable at each slice**: get one mitmproxy→FastAPI→browser
path green locally before adding the second proxy, the spec, the TUI, and the cloud. Each
slice ships tests and a reality-doc update in the same commit.

---

## Package layout — `sg_compute_specs/content_proxy/`

Conformant to `v0.2.6__authoring-a-new-top-level-spec.md`. `spec_id = content_proxy`, PascalCase
`ContentProxy`. Discovered by convention — **no registry edits**.

```
sg_compute_specs/content_proxy/
├── __init__.py                 # empty
├── version                     # 0.1.0
├── manifest.py                 # exports MANIFEST (Schema__Spec__Manifest__Entry)
├── enums/
│   ├── Enum__Content_Proxy__Mode.py            # DIRECT_PROXY | VAULT_WEB
│   ├── Enum__Content_Proxy__Vault__Kind.py     # ZIP | SGIT
│   └── Enum__Content_Proxy__Flow__Action.py    # INJECTED|BLOCKED|CACHED|SKIPPED|FALLBACK|PASSED
├── schemas/                    # one class per file (see doc 03 §8)
│   ├── Schema__Content_Proxy__Create__Request.py
│   ├── Schema__Content_Proxy__Vault__Source.py
│   ├── Schema__Content_Proxy__Stack__Info.py
│   └── Schema__Content_Proxy__Flow__Summary.py
├── collections/
│   └── List__Schema__Content_Proxy__Flow__Summary.py
├── interceptors/
│   └── active.py               # baked from the supplied fastapi_interceptor.py (+ doc 03 §9 fixes)
├── docker/
│   └── compose/
│       └── docker-compose.yml  # COMMITTED — for local `docker compose up`. Generated from the
│                               # template; a test asserts it == template.render(local-defaults)
├── service/
│   ├── ContentProxy__Service.py            # Tier-1 orchestrator (8-verb contract + extras)
│   ├── ContentProxy__Compose__Template.py  # renders the 5-service docker-compose (2 mitmproxies)
│   ├── ContentProxy__User_Data__Builder.py # compose up + load-vaults; writes .env + interceptor
│   ├── ContentProxy__Vault__Loader.py      # zip copy-in / sgit clone (uses Section__SGit_Venv pattern)
│   └── ContentProxy__HTTP__Probe.py        # component health (5 services)
├── api/routes/
│   ├── Routes__ContentProxy__Stack.py      # 8 standard verbs via Spec__CLI__Builder
│   └── Routes__ContentProxy__Flows.py      # GET /content_proxy/stack/{name}/flows
├── cli/
│   ├── Cli__ContentProxy.py                # typer app (Spec__CLI__Builder + extras)
│   └── Renderers.py                        # Rich renderers (pure functions)
├── tui/
│   ├── ContentProxy__TUI__Source.py        # data only (poll status / tail flows / read vaults)
│   ├── renders/                            # pure *__Render fns (status/traffic/scripts/transform/logs)
│   ├── screens/                            # thin Textual screens
│   └── cli/Cli__ContentProxy__Tui.py       # `sp content-proxy tui`
├── traffic/                    # the QA corpus + harness (mirror sentinel/traffic/)
│   ├── corpus/                 # labelled fixture pages: should-blur / should-block / should-pass
│   ├── ContentProxy__Traffic__Runner.py
│   └── ContentProxy__Traffic__Report__Builder.py   # accuracy + latency
└── tests/
    ├── test_manifest.py
    ├── interceptor/            # pure-function tests over the addon
    ├── service/                # compose render / vault loader / probe (in-memory + _Fake)
    ├── tui/                    # render fns + headless screen smoke
    └── integration/            # the two deliverable paths (real chromium, gated)
```

---

## Slices (each is a commit + tests + reality-doc update)

> **MVP = slices 0–8 with NO vaults deployed.** The goal of the MVP is to prove every piece
> wires up. Vault loading + roles 1–2 are post-MVP (slice 9). The MVP's primary gate is the
> **`/mitm-proxy` injected-UI smoke check** (doc 01 §12).

### Slice 0 — skeleton + manifest (½ day)
- Package skeleton, `manifest.py`, `version`, enums (incl. `Enum__Content_Proxy__Tls`),
  schemas (doc 03 §8). `test_manifest.py` passes the conformance contract.
- **Demo:** `sg-compute spec list` shows `content_proxy`.

### Slice 1 — the interceptor addon, unit-tested (½ day)
- Bake the supplied `fastapi_interceptor.py` → `interceptors/active.py` with the doc-03-§9
  fixes. Pure-function tests for `should_process_request/response`, `prepare_*_data`,
  `apply_*_modifications` over fixture flow dicts (no live mitmproxy). Assert `/mitm-proxy` is
  always processed.
- **Demo:** `pytest tests/interceptor` green.

### Slice 2 — single-proxy compose + the `/mitm-proxy` smoke (1 day) ← THE CHAIN PROOF
- `ContentProxy__Compose__Template` renders `mitmproxy-int` + `mitm-service` (stock image +
  addon; no vault, no auth, no origin). `ContentProxy__HTTP__Probe` checks health.
- **Demo:** `docker-compose up`; request `/mitm-proxy` through `mitmproxy-int` → the FastAPI
  UI is injected and renders. **Proves mitmproxy → FastAPI → browser end-to-end.**

### Slice 3 — vault app on `:443` + `/pw` → sg-playwright (1 day)
- Add `vault-app` (`diniscruz/sg-send-vault`) terminating `:443` with `/pw`→sg-playwright, and
  `sg-playwright` (`diniscruz/sg-playwright`) net-local on `:8000` proxied to `mitmproxy-int`.
  TLS `NONE` (self-signed) locally.
- **Demo:** `https://localhost/pw/health/status` works; drive `/pw/sequence/execute` →
  transformed DOM via `mitmproxy-int`. **This is deliverable (b)** (browser path on `:443`).

### Slice 4 — second proxy + basic auth + proxy CA (½ day)
- Add `mitmproxy-ext` (`mitmdump … --proxyauth`). Creds from **`.env`**
  (`CONTENT_PROXY__PROXYAUTH_{USER,PASS}`; commit `.env.example` only). Mount the
  **user-supplied proxy CA** (`--proxy-ca`/`--proxy-ca-key`) into both proxies.
- **Demo:** a browser / curl with proxy creds through `:8080` gets the transform; no creds →
  407; the browser trusts the supplied CA. **This is deliverable (a).**

### Slice 5 — the `content_proxy` CLI (8 verbs + extras) (1 day)
- Wire `Cli__ContentProxy` via `Spec__CLI__Builder` (free: list/info/create/delete/wait/
  health/connect/exec). Extras: `traffic`, `scripts`, `transform`, `logs`. **No `load-vaults`
  in the MVP CLI.** Renderers pure.
- **Demo:** `sp content-proxy create --wait` (local), `… status --json`, `… transform <url>`.

### Slice 6 — the TUI (1.5 days)
- `ContentProxy__TUI__Source` + pure `*__Render` fns + thin screens (doc 02). Every command
  `--json` + no-TTY fallback. Tests: render fns + headless screen smoke (sentinel pattern).
  `status` surfaces the `/mitm-proxy` smoke result.
- **Demo:** `sp content-proxy tui` → status/traffic/transform live.

### Slice 7 — the traffic corpus + accuracy report (1 day)
- `traffic/corpus/` labelled pages; `ContentProxy__Traffic__Runner` replays through the
  workflow; `…__Report__Builder` reports accuracy + latency. Driveable from the TUI.
- **Demo:** `sp content-proxy traffic --run-corpus --json` → accuracy table.

### Slice 8 — EC2 + TLS + deploy-via-pytest (1.5 days) ← MVP COMPLETE
- `ContentProxy__User_Data__Builder` (writes `.env` + compose to `/opt/content-proxy/`, compose
  up; **no vaults**). `create` launches EC2; **TLS via `LETSENCRYPT` or `ACM`** (§3.3).
  **Reuse the existing aws-deployment foundation (v0.33.2) for NLB/ALB/ASG — no new infra
  modules.** deploy-via-pytest numbered lifecycle.
- **Demo:** `sp content-proxy create --region … --tls letsencrypt --wait`; both deliverable
  paths hit live over HTTPS; `/mitm-proxy` UI renders. **MVP done.**

### Slice 9 (POST-MVP) — vault loading + roles 1–2 (1.5 days)
- Add `load-vaults` (`ContentProxy__Vault__Loader`: zip copy-in + sgit clone from live
  server / s3). Script vault feeds the MITM service (role 1); log vault is the append→S3 target
  (role 2). `Schema__…__Vault__Source` populated.
- **Demo:** `sp content-proxy load-vaults --vault zip:… --vault sgit:s3://…`; active script
  comes from the vault; logs append + reopen elsewhere.

### Slice 10 — docs + reality (½ day)
- New reality domain `team/roles/librarian/reality/content-proxy/index.md`; changelog; onboarding
  pointer; update the spec status table.

---

## Deployment targets & where the docker-compose lives

**Both targets ship. Same compose, one source of truth (`ContentProxy__Compose__Template`).**

| Target | How it starts | TLS | Compose file location |
|--------|---------------|-----|------------------------|
| **Local (dev/CI)** | `docker compose -f sg_compute_specs/content_proxy/docker/compose/docker-compose.yml up` (or `sp content-proxy create --local`) | `NONE` / self-signed | **committed** at `sg_compute_specs/content_proxy/docker/compose/docker-compose.yml` |
| **EC2 — no cert** | `sp content-proxy create --tls none` | `NONE` (HTTP / self-signed `:443`) | rendered → written by user-data to `/opt/content-proxy/docker-compose.yml` |
| **EC2 — with cert** | `sp content-proxy create --tls letsencrypt|acm` | Let's Encrypt (self-terminate) or ACM (on the ALB) | same `/opt/content-proxy/docker-compose.yml` |

Precedent (verified): `sg_compute_specs/vault_app/docker/compose/docker-compose.yml` is a
committed local compose; `Vault_App__User_Data__Builder` / `Vnc__User_Data__Builder` write the
rendered compose to `/opt/<stack>/docker-compose.yml` via a heredoc on the EC2 box. We mirror
both.

- **Single source of truth:** `ContentProxy__Compose__Template.render(...)`. The committed
  local file is produced from it (drift-guarded by a unit test — slice 2). Local and EC2 differ
  only in image tags, the `--proxyauth` secret, the TLS mode, and (post-MVP) the vault sources.
- **Anyone can `docker compose up` the committed file** to get the full stack locally with zero
  AWS — that is the primary dev/QA loop.

---

## Reuse map (copy, do not invent)

| Slice | Copy from |
|-------|-----------|
| 0 | `sg_compute_specs/docker/` (manifest, schemas, routes, cli) |
| 1 | the supplied `fastapi_interceptor.py` (doc 03) |
| 2–3 | `…__cli/vnc/service/Vnc__Compose__Template.py` (mitmproxy + `--scripts` + compose) |
| 4 | `sg_compute/cli/base/Spec__CLI__Builder.py` + `v0.2.6__spec-cli-contract.md` |
| 5 | `…__cli/vnc/service/Vnc__Interceptor__Resolver.py` (resolve→write source); `Section__SGit_Venv.py` (sgit) |
| 6 | `…/sentinel/tui/{source,renders,screens}` + `…/tui/screens/test_renders.py` |
| 7 | `…/sentinel/traffic/` (corpus, runner, report builder, echo origin) |
| 8 | `…__cli/vnc/service/Vnc__User_Data__Builder.py`; any spec's deploy-via-pytest |

Estimated total: ~9–10 working days for a single agent, demoable from slice 2.

---

## What this plan deliberately defers

- VNC remote browser (out of scope — needs a container per user).
- Real-time WebSocket flow streaming (REST/poll only).
- The TUI `tui_api` chat wiring (ship the screens; chat-ready shape, no chat).
- Live NLB/ALB/ASG provisioning code (use the existing aws-deployment foundation; this spec
  declares the per-mode LB choice but the LB/ASG modules are the infra layer's job).
</content>
