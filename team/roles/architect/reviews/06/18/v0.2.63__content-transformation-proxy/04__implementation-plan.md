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

### Slice 0 — skeleton + manifest (½ day)
- Package skeleton, `manifest.py`, `version`, enums, schemas (doc 03 §8). `test_manifest.py`
  passes the conformance contract → `sg-compute spec content_proxy` lists.
- **Demo:** `sg-compute spec list` shows `content_proxy`.

### Slice 1 — the interceptor addon, unit-tested (½ day)
- Bake the supplied `fastapi_interceptor.py` → `interceptors/active.py` with the doc-03-§9
  fixes. Pure-function tests for `should_process_request/response`, `prepare_*_data`,
  `apply_*_modifications` over fixture `http.HTTPFlow`-shaped dicts (no live mitmproxy).
- **Demo:** `pytest tests/interceptor` green; static assets skipped, html processed, block/
  cached/override applied.

### Slice 2 — single-proxy compose, local (1 day)
- `ContentProxy__Compose__Template` renders `mitmproxy-int` + `mitm-service` + `sg-playwright`
  (no vault app yet, no auth). `ContentProxy__HTTP__Probe` checks health.
- **Demo:** `docker-compose up`; drive sg-playwright `/sequence/execute` through
  `mitmproxy-int` against a fixture origin; assert the injected `<script>` is in the DOM.
  **This is deliverable (b) minimal.**

### Slice 3 — second proxy + basic auth (½ day)
- Add `mitmproxy-ext` with `--proxyauth`. Same interceptor, same FastAPI.
- **Demo:** a real browser (or curl with proxy creds) through `:8080` gets the transform;
  no creds → 407. **This is deliverable (a).**

### Slice 4 — the `content_proxy` CLI (8 verbs + extras) (1 day)
- Wire `Cli__ContentProxy` via `Spec__CLI__Builder` (free: list/info/create/delete/wait/
  health/connect/exec). Extras: `traffic`, `scripts`, `transform`, `logs`, `load-vaults`.
  Renderers pure.
- **Demo:** `sp content-proxy create --wait` (local), `… status --json`, `… transform <url>`.

### Slice 5 — vault app + vault loading (1–1.5 days)
- Add `vault-app` to compose; `ContentProxy__Vault__Loader` does zip copy-in + sgit clone
  (from live server / s3). Script vault feeds the MITM service; log vault is the append target.
- **Demo:** `sp content-proxy load-vaults --vault zip:./scripts.zip --vault sgit:s3://…`;
  the active script comes from the vault; logs append (role 2).

### Slice 6 — the TUI (1.5 days)
- `ContentProxy__TUI__Source` + pure `*__Render` fns + thin screens (doc 02). Every command
  `--json` + no-TTY fallback. Tests: render fns + headless screen smoke (sentinel pattern).
- **Demo:** `sp content-proxy tui` → status/traffic/transform screens live.

### Slice 7 — the traffic corpus + accuracy report (1 day)
- `traffic/corpus/` labelled pages; `ContentProxy__Traffic__Runner` replays through the
  workflow; `…__Report__Builder` reports accuracy (blurred/removed/blocked as labelled) +
  latency. Driveable from the TUI `transform`/`traffic` screens.
- **Demo:** `sp content-proxy traffic --run-corpus --json` → accuracy table.

### Slice 8 — EC2 via SG/Compute + deploy-via-pytest (1.5 days)
- `ContentProxy__User_Data__Builder` (compose up + load-vaults on the box); `create` launches
  EC2; deploy-via-pytest numbered lifecycle. NLB/ALB + ASG noted as infra (cross-ref v0.33.2).
- **Demo:** `sp content-proxy create --region … --wait`; the two deliverable paths hit live.

### Slice 9 — docs + reality (½ day)
- New reality domain `team/roles/librarian/reality/content-proxy/index.md`; changelog; onboarding
  pointer; update the spec status table.

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
