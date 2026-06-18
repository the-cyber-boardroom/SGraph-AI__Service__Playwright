---
title: "Brief Pack — content-transformation proxy stack (for the implementing agent)"
file: 00__README.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — implementation brief pack. Read top to bottom before writing code.
spec: library/docs/specs/v0.2.63__content-transformation-proxy-stack.md
---

# Brief Pack — content-transformation proxy stack

> **You are the implementing agent.** This pack is everything you need to build the
> `content_proxy` stack in **this** repo. The contract is the spec
> ([`library/docs/specs/v0.2.63__content-transformation-proxy-stack.md`](../../../../../library/docs/specs/v0.2.63__content-transformation-proxy-stack.md));
> this pack is the *how*. Read in order.

---

## What you are building (one paragraph)

A docker-compose stack (runnable locally and on EC2 via a new `content_proxy` SG/Compute spec)
that puts a browser behind **mitmproxy**, which forwards every HTML request/response to a
**FastAPI MITM service** that injects a client-side transformation `<script>`. There are **two
mitmproxy instances** — one externally exposed **with basic auth** (for a human browser), one
internal **without auth** (for the **sg-playwright** browser, because Playwright + an authed
proxy is messy). The **vault app** ships the scripts in and the logs out (append → S3). You
also build a **Textual TUI** for dev/QA/ops and a **layered test suite** (each piece alone,
then the integration). The two key deliverables are the two reachable proxy paths into one
transformation workflow.

**MVP & targets (read this):**
- **The first MVP deploys NO vaults** — its job is to prove the pieces wire up. The
  `/mitm-proxy` injected UI (always processed by the interceptor) is the chain-proof smoke
  check. Vault loading (zip/sgit) is **post-MVP**.
- **Both targets ship from one compose template:** **local** (`docker compose up` the committed
  `sg_compute_specs/content_proxy/docker/compose/docker-compose.yml`) and **EC2** (**with or
  without** an SSL cert — `--tls none|letsencrypt|acm`).
- Images pulled from **Docker Hub**: `diniscruz/sg-playwright`, `diniscruz/sg-send-vault`,
  stock `mitmproxy/mitmproxy`, + the MGraph-AI MITM service image. sg-playwright is reached by
  browsers only via the vault **`/pw` on `:443`** (its `:8000` is net-local).

---

## The two key deliverables (what "done" means)

| # | Deliverable | Proven by |
|---|-------------|-----------|
| **a** | An **authed** external mitmproxy a browser can use (proxy configured) → transformed page | doc `06` AC-1 |
| **b** | A **scriptable** sg-playwright path through a **second, no-auth** mitmproxy → the **same** transform | doc `06` AC-2 |

Everything else (TUI, vault loading, ASG/LB) serves these two.

---

## Reading order

| Doc | Title | Why |
|-----|-------|-----|
| `00` | This README | Orientation, deliverables, conventions |
| `01` | [Architecture & flow diagrams](01__architecture-and-flow-diagrams.md) | Every topology + flow in ASCII. The mental model. |
| `02` | [UX / TUI mockups](02__ux-tui-mockups.md) | Every screen the TUI must render |
| `03` | [Components & contracts](03__components-and-contracts.md) | The interceptor addon ↔ FastAPI contract (exact payloads + verbs), cookie control, env, vault loading |
| `04` | [Implementation plan](04__implementation-plan.md) | Phased slices, package layout, the reuse map (Sentinel / sg_edge / vault_app) |
| `05` | [Testing strategy](05__testing-strategy.md) | Per-piece → integration, TUI test support, the traffic corpus |
| `06` | [Deliverables & acceptance](06__deliverables-and-acceptance.md) | Acceptance criteria, demo script, open decisions |

---

## Non-negotiable conventions (CLAUDE.md — read first if unfamiliar)

- `Type_Safe` only; **no Pydantic, no Literals**; zero raw primitives in schema attrs
  (`Safe_*` / `Enum__*`). One class per file. Empty `__init__.py`. 80-char `═══` headers in
  **Python** (frontmatter in Markdown). Inline comments only.
- **No mocks, no patches.** In-memory composition + `_Fake_*` subclasses. Real Chromium gated
  on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`.
- **No boto3** (use `osbot-aws`). **No vault keys / AWS creds in git.**
- New spec discovered by convention — no registry edits (see `04`).
- Branch `claude/{desc}-{session}`; never push to `dev`; PR from the feature branch.
- Update the reality doc (`team/roles/librarian/reality/`) in the same commit as code.

---

## Hard precedents to copy (do not invent)

| Need | Copy from |
|------|-----------|
| A new SG/Compute spec (manifest, schemas, service, routes, CLI) | `sg_compute_specs/docker/` (full) ; `sg_compute_specs/vnc/` *(in `…__cli/vnc/`)* for the mitmproxy+compose+interceptor shape |
| 8-verb CLI for free | `sg_compute/cli/base/Spec__CLI__Builder.py` + `v0.2.6__spec-cli-contract.md` |
| Compose + user-data + interceptor baking + vault tag model | `sgraph_ai_service_playwright__cli/vnc/service/` (N5 interceptor resolver, compose template, caddy) |
| TUI (Textual screens, render fns, `--json`, no-TTY, `__TUI__Source`) | `sgraph_ai_service_playwright__cli/sentinel/tui/` |
| Traffic corpus + echo origin + accuracy/latency report | `sgraph_ai_service_playwright__cli/sentinel/traffic/` |
| Multi-target harness (local-direct / docker / AWS) + parity matrix | `…/sentinel/` (`Sentinel__Local__Harness`, `…__Docker__Runtime`, parity tests) |
| Vault load via sgit in user-data | `sg_compute/platforms/ec2/user_data/Section__SGit_Venv.py` |
| `/pw` reverse proxy for browser→playwright | `sg_compute/fast_api/reverse_proxy/Fast_API__Reverse_Proxy.py` + v0.2.41 spec |
| The interceptor addon itself | the operator-supplied `fastapi_interceptor.py` (quoted verbatim in `03`) |

---

## Status snapshot

| Element | Status |
|---------|--------|
| The four/five components (mitmproxy, MITM service, sg-playwright, vault app) | as-built (sg-send v0.33.21) |
| `content_proxy` spec (compose + CLI + user-data) | **to build (this repo)** |
| Two-mitmproxy topology (ext-auth / int-noauth) | **to build (MVP)** |
| Local docker-compose (committed) + EC2 deploy (TLS none/LE/ACM) | **to build (MVP)** |
| `/mitm-proxy` injected-UI smoke check | **to build (MVP)** |
| TUI (status/traffic/scripts/transform/logs) | **to build (MVP)** |
| Test suite (per-piece + integration + traffic corpus) | **to build (MVP)** |
| Vault loading (zip / sgit) + roles 1–2 | **to build (POST-MVP)** |
| VNC remote browser | **out of scope** |
</content>
