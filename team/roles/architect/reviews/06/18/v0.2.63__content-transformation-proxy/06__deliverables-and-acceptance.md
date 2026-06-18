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

## Acceptance criteria

### AC-1 — deliverable (a)
- [ ] A browser configured with proxy `http://USER:PASS@<host>:8080` loads a target page and
      the page is **transformed** (the injected `<script>` ran; matched content blurred/removed).
- [ ] No / wrong proxy creds → **407** (auth enforced).
- [ ] CA-trust step documented (install mitmproxy CA or accept warning).

### AC-2 — deliverable (b)
- [ ] `sp content-proxy transform <url> --via int --json` (or a `/sequence/execute` call with
      the browser proxied to `mitmproxy-int` + `mitm-*` cookies set) returns DOM/text/screenshot
      showing the **same** transform as AC-1.
- [ ] No proxy-auth friction (the int proxy has none).
- [ ] **Parity:** the same corpus URL via `ext` and `int` yields the same transform.

### AC-3 — the stack
- [ ] `sg-compute spec list` shows `content_proxy` (convention discovery, no registry edit).
- [ ] `sp content-proxy create --wait` brings up all 5 services; `status` shows them healthy.
- [ ] `load-vaults` populates the script + log + UX vaults via **zip** and via **sgit**.
- [ ] The active transformation script is sourced from the **script vault**; updating the vault
      changes behaviour with no redeploy.
- [ ] Logs **append** to the S3-backed log vault and the vault **reopens from another
      environment** with the same files (role 2).

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

---

## Demo script (what to show the owner)

```
# 1. it's a spec
sg-compute spec list                                  # content_proxy appears

# 2. bring it up locally
sp content-proxy create cp-local --mode direct \
      --vault zip:./scripts.zip --proxyauth demo:demo --wait
sp content-proxy status --json                        # 5 services healthy

# 3. deliverable (a) — human proxy
#    configure a browser proxy to http://demo:demo@localhost:8080, open a target page
#    -> content is blurred/removed

# 4. deliverable (b) — scripted playwright through the no-auth proxy
sp content-proxy transform https://news.site/9 --via int --json
#    -> before/after, injected <script>, rules fired

# 5. parity + accuracy
sp content-proxy traffic --run-corpus --json          # accuracy + latency report

# 6. the operator TUI
sp content-proxy tui                                   # watch flows live, drill into a flow

# 7. vaults are the backbone
sp content-proxy scripts                              # versions; set-active a new script -> behaviour changes
sp content-proxy logs --follow                        # append->S3; reopen elsewhere
```

---

## Open decisions (carry to the owner before / during build)

Resolved already (2026-06-18): code lives **here**; stock-image + interceptor-addon calling
`:10011` (not upstream); **cookie** activation (FastAPI-owned); **two** mitmproxies (ext-auth /
int-noauth); vaults via **zip or sgit**; **VNC out of scope**.

Still open:

1. **mitmproxy version pin** — reuse VNC `10.4.2`, or clear a newer line? *(Recommend 10.4.2.)*
2. **MITM-service image** — pull a pinned `MGraph-AI__Service__Mitmproxy` image, or build in
   this repo's compose? *(Recommend pull pinned.)*
3. **QA cookie names/values** — exact `mitm-*` cookies the FastAPI service keys on, so the
   sg-playwright sequence can set them.
4. **Basic-auth secret source** for `mitmproxy-ext` — env / vault / generated-at-launch (like
   the VNC operator password)?
5. **CA trust for Mode 1** — document install, or ship a helper to fetch/install the proxy CA?
6. **NLB/ALB/ASG** — confirm these reuse the existing aws-deployment foundation (v0.33.2) rather
   than new modules in this spec.

---

## Where everything lives (recap)

| Artefact | Path |
|----------|------|
| The contract (spec) | `library/docs/specs/v0.2.63__content-transformation-proxy-stack.md` |
| This brief pack | `team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/` |
| The code (to build) | `sg_compute_specs/content_proxy/` |
| Reality doc (to add) | `team/roles/librarian/reality/content-proxy/index.md` |
</content>
