# MVP Brief: Provisioning UI for `Fast_API__SP__CLI`

**Status:** PROPOSED — ready for Sonnet pickup
**Target version:** v0.1.102
**Date drafted:** 2026-04-28
**Author:** Architect (Opus session, with read access to `dev` HEAD `7e72431`)
**Audience:** Sonnet (implementation), Architect, DevOps
**Demo deadline:** to be confirmed by operator

---

## What this is

A minimal web UI for the existing `Fast_API__SP__CLI` control plane. Two static apps under `sgraph_ai_service_playwright__api_site/` — **admin** (cross-stack dashboard) and **user** (per-type "Start" cards) — that let humans provision and tear down ephemeral EC2 stacks (linux, docker, elastic) without touching the CLI. Live progress during boot. X-API-Key auth. No new build toolchain.

This brief is a deliberate MVP slice of the larger commercial-platform vision in `team/humans/dinis_cruz/briefs/04/28/v0.22.19__dev-brief__serverless-provisioning-system.md`. **Its sole purpose is to prove the workflow on a demo.** The heavy machinery (per-user vault, OAuth, billing, IP-pinning, Lambda orchestrator, iframe embedding, SSM browser terminal, VNC bastion) is explicitly deferred to follow-up briefs.

## Status of the underlying surface

| Section | Service | CLI | HTTP routes class | Mounted on `Fast_API__SP__CLI` | MVP role |
|---|---|---|---|---|---|
| `ec2/playwright` | ✅ | ✅ `sp ec2` | ✅ `Routes__Ec2__Playwright` | ✅ | Reference — not a tile in this MVP |
| `linux` | ✅ | ✅ `sp linux` | ✅ `Routes__Linux__Stack` | ❌ **gap closed in PR-1** | **Live tile in MVP** |
| `docker` | ✅ | ✅ `sp docker` | ✅ `Routes__Docker__Stack` | ❌ **gap closed in PR-1** | **Live tile in MVP** |
| `elastic` | ✅ | ✅ `sp el` | ❌ **built in PR-3** | ❌ **mounted in PR-3** | **Live tile in MVP** |
| `opensearch` | ✅ | ✅ `sp os` | (mounted) | ✅ | "Coming soon" tile in MVP |
| `vnc` | ❌ planned | ❌ planned | ❌ planned | ❌ | "Coming soon" tile in MVP |

The MVP ships three live tiles (linux, docker, elastic) and two "coming soon" tiles (opensearch, vnc) so the UI contract leaves room for both without rework.

## How to read this series

| # | Doc | Read when | Approx size |
|---|---|---|---|
| `00` | [`README.md`](README.md) *(this file)* | First — orientation | ~100 lines |
| `01` | [`mvp-scope-and-flows.md`](01__mvp-scope-and-flows.md) | Before designing or building anything | ~300 lines |
| `02` | [`backend-changes.md`](02__backend-changes.md) | When working on the Python side | ~350 lines |
| `03` | [`ui-design-and-components.md`](03__ui-design-and-components.md) | When working on the JS/HTML side | ~450 lines |

Total ~1,200 lines. Sonnet should read 00 + 01 once, then 02 *or* 03 depending on which PR is in flight. Backend and UI PRs are independent — same brief, two parallel implementation tracks.

## Key decisions (already made — do not relitigate)

| # | Decision | Rationale |
|---|---|---|
| 1 | **No new top-level package.** The UI extends `sgraph_ai_service_playwright__api_site/` rather than creating `__ui/`. | `__api_site/` is 405 lines today and serves no production traffic. Replacing it in place keeps the tree clean. The existing `cookie.js` / `storage.js` / X-API-Key flow is reused. |
| 2 | **Vanilla JS + Web Components, no Shadow DOM.** Native ES modules. No build step. | Same dependency profile as today's `__api_site/`. Shadow DOM is deferred — the MVP is small enough that CSS leakage is not a real risk and dropping it removes a class of debugging pain. |
| 3 | **Two separate static apps**: `/admin/index.html` and `/user/index.html`. | Different consumers, different lenses. Sharing a single SPA toggled by nav adds router complexity for no MVP gain. |
| 4 | **Live progress during boot is essential.** Both UIs poll `/{section}/stack/{name}/health` from the moment `create` returns until `healthy=true`. | The 60-600s boot window is the demo's most visible UX surface. A spinner that moves against real health checkpoints is the difference between "it works" and "it feels right". |
| 5 | **Phased scope: linux + docker + elastic in this MVP.** OpenSearch and VNC are "coming soon" tiles. | Each is one config-line in the catalog to flip live when its backend is ready. Designing for five from day one removes UI rework later. |
| 6 | **One new backend endpoint family: `/catalog/types` + `/catalog/stacks`.** Cross-section read-only. | The UI needs one place to ask "what types exist?" and "what's running across all types?". Forcing the UI to hit five endpoints and stitch them is wrong; the section list also can't live in the UI (rule: no hard-coded section list). |
| 7 | **Existing X-API-Key middleware is the only auth.** No OAuth, no per-user identity. | "Admin" = "anyone with the key" for the MVP. Per-user identity is its own follow-up brief. |
| 8 | **No iframe embedding of the running service in the MVP.** Once a stack is `READY`, the UI shows access details (public IP, SSM command, port) and copy buttons. | iframe embedding has same-origin / mixed-content / per-service auth issues that each need designing. Out of scope for the demo. |

## Layering rules (non-negotiable)

These come from `.claude/CLAUDE.md` and the existing brief series. Sonnet must hold these in every PR.

1. **All schemas extend `Type_Safe`.** No Pydantic. No Literals. Fixed-value sets are `Enum__*`. One class per file.
2. **All AWS calls go through `osbot-aws`.** No direct boto3. (UI does not touch AWS at all — this is reiteration for the backend PRs.)
3. **Routes have no logic** — they delegate to a service. Mirror the shape of `Routes__Linux__Stack`.
4. **The UI never imports anything Python.** It is a pure HTTP client of `Fast_API__SP__CLI`.
5. **The UI never knows about AWS.** Its vocabulary is "stack types", "stacks", "health" — all defined by the catalog endpoint.
6. **No `fetch` call outside `<sg-api-client>`.** No `localStorage` access outside `<sg-api-client>` and `<sg-auth-panel>`. `grep` should verify both.
7. **Components are dumb renderers.** They receive data via attributes/properties and emit `CustomEvent`s. Page controllers wire them together. No fetch inside components, no routing inside components.
8. **No third-party JS frameworks.** No React, Vue, Svelte, Lit. Native Web Components only. CDN imports of `xterm.js` / `noVNC` are explicitly OUT of scope for this MVP (those land in follow-up briefs).

## What's NOT in scope for the MVP

Documented here so scope creep has somewhere to push back from. Each of these is a worthwhile follow-up brief — none of them is a hidden assumption.

- ❌ SSM browser terminal (`xterm.js` + `Routes__Ssm`) — **own brief, after the MVP demo**
- ❌ VNC viewer (`noVNC` + `Routes__Vnc`) — **depends on `sp vnc` slice landing**
- ❌ Cost display, uptime tracking, hourly rate — **schema additions + own brief**
- ❌ Section-specific operations beyond create/list/info/delete/health (e.g. elastic seed/wipe, observability backup) — **own brief per section**
- ❌ Iframe embedding of running services — **own design exercise**
- ❌ Per-user identity, quotas, billing — **per the v0.22.19 commercial-platform brief**
- ❌ Real-time WebSocket updates — **polling for now; revisit if it becomes a measured problem**
- ❌ Replacing the CLI — **the UI is additive, the CLI is the source of truth**
- ❌ Mobile-optimised layout — **responsive enough not to break, not mobile-first**
- ❌ Themes (light mode) — **start dark, defer light**
- ❌ Internationalisation — **English only**

## Backend changes summary (full detail in doc 02)

Three PRs, sequenceable in order, each independently shippable:

- **PR-1** — Mount `Routes__Linux__Stack` and `Routes__Docker__Stack` on `Fast_API__SP__CLI`. ~10 lines + 4 tests. Half a day.
- **PR-2** — Build new `catalog/` sub-package with `Routes__Stack__Catalog` (3 endpoints). The cross-section read API the UI needs. 1 day.
- **PR-3** — Build `Routes__Elastic__Stack` mirroring the linux/docker shape. Service exists; only the route class is missing. Half a day plus tests.

Total backend: ~2 days for one developer.

## UI build summary (full detail in doc 03)

Two static apps under `sgraph_ai_service_playwright__api_site/`, sharing a small set of components:

- **6 components**: `<sg-api-client>`, `<sg-auth-panel>`, `<sg-header>`, `<sg-stack-grid>`, `<sg-stack-card>`, `<sg-create-modal>`, `<sg-toast-host>`. (7 if you count the toast host; the doc treats it as one of the 6 user-facing widgets plus the toast host as a passive listener.)
- **2 page controllers**: `admin.js`, `user.js`. Each ~150 lines.
- **3 shared modules**: `api-client.js` (the only fetch boundary), `catalog.js` (caches `/catalog/types`), `poll.js` (health-poll loop with back-off).

Total UI: ~5 days for one developer working alongside the backend dev.

## Acceptance criteria for "the MVP demo is ready"

A reviewer should be able to do all of these in a freshly-deployed environment:

1. Open `/admin/` in a browser, paste the API key, see the connection turn green.
2. Open `/user/`, see four tiles: Linux, Docker, Elastic (live with [Start] buttons) + OpenSearch and VNC (greyed "coming soon").
3. Click "Start Linux". Watch a modal appear with a progress bar that advances against real health-check ticks. ~60s later, see "READY" with public IP and the SSM command to connect.
4. Open `/admin/` in another tab. See the linux stack listed with its state, IP, and uptime. Click "Stop". See it disappear within 10 seconds.
5. Repeat (3) for Docker (~10 min boot — slower but same UX) and Elastic (~90s).
6. Confirm the equivalent `sp linux create` / `sp docker create` / `sp el create` CLI commands still work and produce stacks visible in the admin UI.
7. Confirm `grep -r "fetch(" sgraph_ai_service_playwright__api_site/` returns hits **only** in `shared/api-client.js`.
8. Confirm `grep -r "localStorage" sgraph_ai_service_playwright__api_site/` returns hits **only** in `shared/api-client.js` and `shared/auth-panel.js`.

If any of these fails, the MVP is not done.

## What ships after the demo

The MVP demo is an evidence-gathering exercise. After it lands, the next briefs in the queue should be:

1. **OpenSearch tile flip** — same shape as elastic; add a `Routes__OpenSearch__Stack` if not already mounted, register in catalog. Likely a 1-day brief.
2. **VNC integration brief** — depends on `sp vnc` slice landing per `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`. Adds the `<sg-vnc-viewer>` component.
3. **SSM browser terminal brief** — adds `Routes__Ssm` and `<sg-ssm-terminal>`. The first place the UI gains real interactive depth.
4. **Cost display brief** — schema additions for `launch_time` / `max_hours` surfaced in `Info` responses, plus the `<sg-cost-display>` component.

Each is its own focused brief, same shape as this one. None should bloat into the next.
