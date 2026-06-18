---
title: "Content-transformation proxy — Deliverables & acceptance"
file: 06__deliverables-and-acceptance.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — acceptance criteria + demo script + open decisions.
---

# Deliverables & acceptance

## The two key deliverables

| # | Deliverable | What it is |
|---|-------------|------------|
| **a** | Authed external mitmproxy | `mitmproxy-ext` (`:8080`, basic auth), reachable by a browser with its proxy configured; pages come back transformed by the FastAPI workflow |
| **b** | Scriptable sg-playwright via a second proxy | sg-playwright drives a browser through `mitmproxy-int` (`:8081`, **no auth**) into the **same** FastAPI workflow — automation/QA without proxy-auth pain |

Plus the enabling work: the `content_proxy` SG/Compute spec (compose + CLI + user-data), vault
loading (zip/sgit), the TUI (dev/QA/ops), and the test suite (per-piece + integration +
traffic corpus).

---

## MVP scope

The **first MVP deploys NO vaults** — its only job is to prove every piece wires up. MVP = AC-0
through AC-6. Vault loading + roles 1–2 are **post-MVP** (AC-7).

## Acceptance criteria

### AC-0 — the `/mitm-proxy` smoke (MVP chain proof)
- [ ] Requesting `/mitm-proxy` through **each** proxy renders the FastAPI MITM service's
      built-in injected UI — with no vault, no origin, no script. Proves mitmproxy → FastAPI →
      browser end-to-end. Surfaced in TUI `status`.

### AC-1 — deliverable (a)
- [ ] A browser configured with proxy `http://USER:PASS@<host>:8080` loads a target page and
      the page is **transformed** (the injected `<script>` ran; matched content blurred/removed).
- [ ] No / wrong proxy creds → **407** (auth enforced).
- [ ] CA-trust step documented (install mitmproxy CA or accept warning).

### AC-2 — deliverable (b)
- [ ] sg-playwright drives a browser through `mitmproxy-int` (no auth) into the same workflow;
      browser/vault callers reach Playwright via the vault **`/pw` on `:443`** (not `:8000`).
- [ ] `sp content-proxy transform <url> --via int --json` returns DOM/text/screenshot showing
      the **same** transform as AC-1.
- [ ] **Parity:** the same corpus URL via `ext` and `int` yields the same transform.

### AC-3 — the stack runs on BOTH targets
- [ ] `sg-compute spec list` shows `content_proxy` (convention discovery, no registry edit).
- [ ] **Local:** `docker compose -f sg_compute_specs/content_proxy/docker/compose/docker-compose.yml up`
      (or `sp content-proxy create --local`) brings up all 5 services; `status` healthy; TLS `NONE`.
- [ ] **EC2 without cert:** `sp content-proxy create --tls none --wait` — runs; both deliverable
      paths work.
- [ ] **EC2 with cert:** `sp content-proxy create --tls letsencrypt|acm --wait` — `:443` serves
      a trusted cert; both deliverable paths work over HTTPS.
- [ ] The committed local compose == `template.render(local-defaults)` (drift-guard test).

### AC-4 — the TUI
- [ ] `sp content-proxy tui` renders status / traffic / scripts / transform / logs.
- [ ] Every command has `--json` and a no-TTY plain fallback.
- [ ] `transform` shows before→after + the injected `<script>` + rules fired.

### AC-5 — testing
- [ ] Per-piece units green with no docker/AWS (addon, FastAPI contract, compose render, vault
      loader, probe, TUI renders).
- [ ] Traffic corpus accuracy report green (should-blur/remove/block/pass/skip all correct,
      0 false-positives on should-pass).
- [ ] Integration AC-1 + AC-2 pass with real chromium + compose (gated).
- [ ] deploy-via-pytest lifecycle passes (gated on creds).

### AC-6 — hygiene
- [ ] CLAUDE.md conventions (Type_Safe, one-class-per-file, Safe_*/Enum, no mocks, empty
      `__init__.py`, headers).
- [ ] Reality doc `content-proxy/index.md` + changelog updated in the landing commit.
- [ ] No vault keys / AWS creds in git.

### AC-7 — vaults (POST-MVP, not required for the MVP)
- [ ] `load-vaults` populates script + log + UX vaults via **zip** and via **sgit** (live
      server / s3).
- [ ] Active transformation script sourced from the **script vault**; updating the vault changes
      behaviour with no redeploy (role 1).
- [ ] Logs **append** to the S3-backed log vault; the vault **reopens from another environment**
      with the same files (role 2).

---

## Demo script (what to show the owner)

```
# 1. it's a spec
sg-compute spec list                                  # content_proxy appears

# 2a. bring it up LOCALLY (no AWS, no vaults)
docker compose -f sg_compute_specs/content_proxy/docker/compose/docker-compose.yml up -d
#    ...or:  sp content-proxy create --local --proxyauth demo:demo
sp content-proxy status --json                        # 5 services healthy, TLS none

# 3. MVP chain proof — the /mitm-proxy injected UI
#    open http://demo:demo@localhost:8080/mitm-proxy  (or via the int proxy)
#    -> the FastAPI MITM UI renders  => whole chain works, no vault needed

# 4. deliverable (a) — human proxy
#    configure a browser proxy to http://demo:demo@localhost:8080, open a target page
#    -> content is transformed

# 5. deliverable (b) — scripted playwright through the no-auth proxy (reached via /pw:443)
sp content-proxy transform https://news.site/9 --via int --json
#    -> before/after, injected <script>, rules fired

# 6. accuracy + the operator TUI
sp content-proxy traffic --run-corpus --json          # accuracy + latency report
sp content-proxy tui                                  # watch flows live, drill into a flow

# 7. EC2 — with or without a cert
sp content-proxy create --region eu-west-2 --tls none        --wait   # no cert
sp content-proxy create --region eu-west-2 --tls letsencrypt --wait   # LE cert on :443

# 8. POST-MVP — vaults as the backbone
sp content-proxy load-vaults --vault zip:./scripts.zip --vault sgit:s3://bkt/logs
sp content-proxy scripts                              # versions; set-active -> behaviour changes
sp content-proxy logs --follow                        # append->S3; reopen elsewhere
```

---

## Open decisions (carry to the owner before / during build)

Resolved already (2026-06-18): code lives **here**; stock-image + interceptor-addon calling
`:10011` (not upstream); **cookie** activation (FastAPI-owned); **two** mitmproxies (ext-auth /
int-noauth); vaults via **zip or sgit**; **VNC out of scope**.

All resolved (2026-06-18):

1. **mitmproxy version** → **latest `12.2.3`** (run `mitmdump`). The VNC `10.4.2` pin was a
   Caddy-reverse-proxy-of-mitmweb constraint; not relevant to a forward proxy.
2. **MITM-service image** → **pull the Docker Hub image** being published now (wire as
   `mitm_service_image`; ref pending — the only external dependency left).
3. **QA cookies** → `mitm-show`, `mitm-inject`, `mitm-debug` (confirmed); set on the Playwright
   context in the QA sequence.
4. **Basic-auth secret** → from the **`.env`** file (`CONTENT_PROXY__PROXYAUTH_{USER,PASS}`).
5. **Proxy CA (Mode 1)** → **user supplies** the CA cert/key via setup params
   (`--proxy-ca` / `--proxy-ca-key`), mounted into both mitmproxy containers.
6. **NLB/ALB/ASG** → **reuse the existing aws-deployment foundation** (v0.33.2); no new infra
   modules here.

Nothing blocking. Only pending external input: the MITM-service Docker Hub image ref.

---

## Where everything lives (recap)

| Artefact | Path |
|----------|------|
| The contract (spec) | `library/docs/specs/v0.2.63__content-transformation-proxy-stack.md` |
| This brief pack | `team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/` |
| The code (to build) | `sg_compute_specs/content_proxy/` |
| Reality doc (to add) | `team/roles/librarian/reality/content-proxy/index.md` |
</content>
