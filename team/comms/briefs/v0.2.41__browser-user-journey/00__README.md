---
title: "Browser User-Journey Platform — briefing pack (v0.2.41)"
version: v0.2.41
date: 2026-05-26
status: PROPOSED — substrate + frameworks are delivered; this pack is the conductor/worker/TUI layer to build on top.
audience: Architect, Dev, QA, DevOps, Librarian (cross-role)
builds_on:
  - team/comms/briefs/v0.2.19__qa-vault-app/
  - team/roles/architect/reviews/05/26/v0.2.41__browser-user-journey-platform__plan.md
---

# Browser User-Journey Platform — Briefing Pack (v0.2.41)

A self-contained pack for building **`sg browser user-journey`** — a
container-driven browser-automation **execution platform**. It provisions an
ephemeral EC2, then a **conductor** container fans out **worker** containers —
each worker is one browser *user-journey* (visit a site and browse N pages, open
a vault and do N actions, …) routed through a shared mitmproxy — and aggregates
pass/fail + captured flows. **Load = how many workers you run. The journey =
which worker image + params.** The operator drives it through **TUIs** (a live
cockpit + an LLM chat cockpit that *talks to the tools*); the CLI only
starts/stops/monitors.

Four files, read in order:

| # | File | What it covers |
|---|------|---|
| 00 | this file | Pack overview, **status table**, the reframe, what we reuse, reading order |
| 01 | `01__substrate-contract.md` | The stable contract we build against — the vault-app substrate **and** the TUI tool-API framework |
| 02 | `02__platform-design.md` | The platform design — conductor, worker image, suites, schemas, tool-API provider, slice plan, open questions |
| 03 | `03__architecture-flows-ux.md` | **ASCII-art** architecture, flow diagrams, and TUI/CLI UX mockups |

---

## The reframe in one sentence

> This is the **load-oriented, fan-out evolution of the QA vault-app** that
> `v0.2.19__qa-vault-app` designed but never built. That pack assumed **one
> runner per stack** driving a shared Playwright service (fine for a nightly
> smoke). For real concurrency we make the **journey a container** and run **N of
> them**, coordinated by a **conductor** — and we add the two missing
> experiences: a **live cockpit TUI** and a **chat cockpit** where an LLM drives
> the platform through the existing tool-API. The execution substrate
> (vault + Playwright + mitmproxy + TLS), the assertion model, and the agentic
> tool framework already exist — **we are not reinventing any of them.**

---

## What we reuse (and therefore do NOT build)

Three things already shipped, in three different parts of the repo. 01 is the contract for all of them.

1. **The execution substrate** — `sg vault-app create --with-playwright` already
   stands up vault + Playwright API + mitmproxy + host-plane + TLS + single-token
   auth on one EC2 (`sg_compute_specs/vault_app/`, 63 passing tests). We deploy
   *that* and add a conductor.
2. **The QA app design** — `v0.2.19__qa-vault-app/02` fully designed the
   journey/result/assertion schemas, the stateless evaluator, the
   vault-resident `journeys/` + `runs/` layout, and the **one outstanding
   substrate slice** (per-run mitmproxy capture). We **adopt those schemas**
   (aligning names) and **build that slice** — it is now a hard prerequisite,
   because flow aggregation across N workers needs per-run addressability.
3. **The TUI tool-API framework** — `sgraph_ai_service_playwright__cli/tui/` has a
   backend-neutral agentic chat loop (`Chat__Engine.send_turn_agentic`), a
   provider/registry model, and an **execution center** with preconditions,
   param validation, grants, **dry-run preview, a mutation gate, and an audit
   log** (`Tui_Api__Execution_Center`). Plus **workflows = curated grant bundles**
   (`Schema__Tui_Api__Workflow` — "the model never picks tools; a workflow curates
   grants"). We expose our operations as one provider and reuse all of it.

---

## Status table — acceptance criteria, as of v0.2.41

| # | Capability | Status | Why |
|---|-----------|--------|-----|
| 1 | One-command stack deploy (vault + Playwright + mitmproxy + TLS + auth) | **✅ substrate** | `sg vault-app create --with-playwright --wait`. |
| 2 | 16-verb browser step language + `/sequence/execute` + per-run Chromium isolation | **✅ substrate** | `Enum__Step__Action`; each call spawns/tears down its own browser. |
| 3 | 100% browser traffic captured by mitmproxy + custom interceptors | **✅ substrate** | `SG_PLAYWRIGHT__DEFAULT_PROXY_URL`; `--interceptor-script` (vnc/firefox resolver). |
| 4 | Per-run network-log addressability (`GET /capture/network-log/{run_id}`) | **🟡 designed, NOT built** | The qa-vault-app slice 4 (~80 lines). **Hard prerequisite** for N-worker flow aggregation. |
| 5 | Journey / result / assertion schemas + stateless evaluator | **❌ designed, NOT built** | Fully specced in `v0.2.19__qa-vault-app/02`. We build + converge names. |
| 6 | Container fan-out primitive | **✅ primitive** | host-plane `/pods` (limited schema) + Docker socket pattern. Conductor uses the socket for full control. |
| 7 | Conductor (suites, fan-out, aggregation, suite API) | **❌ new** | The platform's brain. Dedicated container. |
| 8 | Worker journey-runner image | **❌ new** | Dedicated image FROM the Playwright base; runs the browser in-process via the reused core. |
| 9 | Agentic, backend-neutral tool framework (chat loop, providers, exec center, workflows, audit) | **✅ framework** | `tui/chat/` + `tui/tool_api/`. |
| 10 | `user-journey` tool-API provider + workflows (monitor / operate / load) | **❌ new (thin)** | Maps conductor ops to grant-gated tools. |
| 11 | Cockpit TUI (live worker grid + flow feed) + chat cockpit | **❌ new (thin)** | Reuse Textual widgets + the agentic loop. |
| 12 | `sg browser` CLI group + `user-journey` spec (manifest, CLI, routes, service) | **❌ new** | Nested under a new `sg browser` group; `nav_group=BROWSERS` (already exists). |
| 13 | Load fan-out (count × concurrency) + aggregate latency percentiles | **❌ new** | The reason this is a *platform*, not a single runner. |

**Reused: 1, 2, 3, 6, 9 (✅). One designed-but-unbuilt prerequisite: 4 (🟡).
Net-new (mostly thin layers over existing frameworks): 5, 7, 8, 10, 11, 12, 13.**

---

## So what's actually left to build?

In dependency order:

1. **The per-run capture slice (#4)** — `GET /capture/network-log/{run_id}` on
   `agent_mitmproxy`, keyed by `X-SG-Run-Id`. Shared with the qa effort; do it first.
2. **The journey/assertion schemas + evaluator (#5)** — adopt the qa-vault-app
   design, renamed to `Schema__Journey__*`. Pure data + pure logic.
3. **The worker journey-runner image (#8)** — runs one journey in-process and
   writes its result + artefacts into the vault.
4. **The conductor (#7) + fan-out (#13)** — owns suites, fans workers out over the
   Docker socket, aggregates.
5. **The `user-journey` spec + `sg browser` group (#12)** — manifest, service,
   routes, thin CLI.
6. **The tool-API provider (#10) + the two TUIs (#11)** — the operator experience.

Full detail in `02__platform-design.md` §6 (slice plan). The architecture, flows,
and UX are drawn in `03__architecture-flows-ux.md`.

---

## Cross-references

| What | Where |
|---|---|
| Architect plan (decisions + boundaries) | `team/roles/architect/reviews/05/26/v0.2.41__browser-user-journey-platform__plan.md` |
| QA vault-app pack (the design we extend) | `team/comms/briefs/v0.2.19__qa-vault-app/` |
| Vault-app substrate spec | `sg_compute_specs/vault_app/` · compose `…/service/Vault_App__Compose__Template.py` |
| Playwright core (step engine) | `sg_compute_specs/playwright/core/service/Playwright__Service.py` · `…/Step__Executor.py` |
| mitmproxy spec | `sg_compute_specs/mitmproxy/` |
| TUI tool-API framework | `sgraph_ai_service_playwright__cli/tui/tool_api/` |
| Agentic chat engine + backends | `sgraph_ai_service_playwright__cli/tui/chat/` · chat TUI `…/aws/bedrock/tui/screens/Bedrock__Chat__Screen.py` |
| Host-plane fan-out | `sg_compute/host_plane/pods/` · client `sg_compute/core/pod/Sidecar__Client.py` |
| Playwright API agent guide | `library/guides/v0.2.6__playwright-api-for-agents.md` |

---

*Filed as the strategy for the user-journey platform. Open `01__substrate-contract.md` next.*
