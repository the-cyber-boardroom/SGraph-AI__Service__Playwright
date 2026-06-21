---
title: "05 — JS API (agentic window.__tool — aligned to sgraph.ai precedent)"
file: 05__js-api.md
author: Architect (Claude)
date: 2026-06-21 (rev 3 — Q1b RESOLVED → real sg-tool-api on sg-layout)
repo: "SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)"
status: PROPOSED — design proposal aligned to the agentic-js-api precedent. No runtime code.
parent: README.md
covers: "User point (f) — JS API support"
precedent:
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/how-it-works.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/claude-playwright.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/building-agent-native.md
  - team/humans/dinis_cruz/claude-code-web/06/21/15/agentic-js-api-research.md   # captured grounding
---

# 05 — JS API (agentic `window.__tool`)

Covers **point (f)**: JavaScript-API support. **Rev 2** replaced the rev-1 "shape
proposal blocked on precedent" with a design aligned to the supplied house pattern:
the **agentic JS API** (`window.__tool`) used across the sgraph.ai tools. **Rev 3**
resolves the last packaging sub-decision: `window.__tool` is registered via the
**real `sg-tool-api` web component**, wired on `sg-layout`, not an inline shim.

> ✅ **Q1 RESOLVED.** The operator supplied the precedent on 2026-06-21:
> `https://sgraph.ai/en-gb/library/use-cases/agentic-js-api` (read any page's
> markdown by appending `.md`). The grounding is captured at
> `team/humans/dinis_cruz/claude-code-web/06/21/15/agentic-js-api-research.md`.
> The rev-1 `SgPlaywrightClient` HTTP-wrapper guess (modeled on the admin-site
> `api-client.js`) is **superseded** — it was the wrong house style. The correct
> pattern is the dual-surface, self-describing `window.__tool` below.
>
> ✅ **Q1b RESOLVED (rev 3) → option (A).** The operator decided to **reuse the
> shared `sg-tool-api` web component and build the console on `sg-layout`** (its other
> tools use it; "it brings a lot of powerful features"). This **reverses the pack's
> old Decision #1** (single self-contained no-deps file) — see README Decision #1/#8
> rev 3. The "inline shim" recommendation from rev 2 is superseded. §1-§5 below (the
> method surface, the `getSkills()` trio, the Playwright runtime-discovery workflow)
> are unchanged — only the **packaging** conclusion changes (real component, not shim).
> The console's component/asset URLs are now root_path-aware (Decision #11, brief 08).

---

## 1. The pattern (what we are aligning to)

The agentic JS API is a **dual-surface** design: a tool ships BOTH a human UI and a
JavaScript API for agents, over **one shared tool state** — "neither is a wrapper
around the other." Agents drive the typed JS surface instead of reverse-engineering
HTML, which removes Playwright's two classic failure modes (UI changes break
automations silently; timing/shadow-DOM non-determinism).

Three mandatory properties (`building-agent-native.md`):
1. **`window.__tool` registered on page load** (via the `sg-tool-api` component).
2. **Core operations exposed as typed methods** — not DOM pokes.
3. **Tool ships its own skill files** via `getSkills()`.

Three defining characteristics (`how-it-works.md`):
- **Self-describing** — `__tool.meta.getSkills()` returns human + browser + API docs.
- **Deterministic** — typed signatures, explicit params, consistent return shapes.
- **Dual-surface** — one page serves human and agent equally.

Global surface to mirror:
- `window.__tool` — the live instance.
- `window.__tool.meta` — `getMethods()`, `getVersion()`, `getManifest()`,
  `getSkills()`, `health()`, `getLog()`.
- `window.SGA_TOOL` — frozen event-name constants.
- `window.__tool_registry` — `find()/findAll()/findById()` (multi-instance).
- Window events for async ops (e.g. `tool:run:started`, `tool:run:complete`).

---

## 2. Why this fits sg-playwright unusually well

The sg-playwright "Try it out" page becomes an **agent-native `window.__tool`** whose
typed methods wrap the endpoints the page already calls. This is recursive and clean:
an agent uses Playwright **(the service)** to open a page whose `window.__tool` then
drives the Playwright **service** — every layer self-describing.

Two payoffs unique to this repo:
1. **The API skill is generated from code-derived truth.** `getSkills().api` is built
   from the capability map + `library/skills/sg-playwright-capabilities/SKILL.md`, so
   "the documentation never drifts from the implementation because it is served by the
   implementation" (`how-it-works.md`). This is the **root fix for D2/D4** (the
   `capabilities.json` version drift and the stale `skill__agent.md`): the page's own
   live skill, sourced from `/health/capabilities` + the code surface, supersedes the
   pinned artefacts.
2. **The workflow file (brief 03) is the native payload** for `__tool.sequence(...)` —
   import/export, gallery, and the JS API all speak the one `/sequence/execute` shape
   (Decision #3).

---

## 3. Proposed `window.__tool` method surface

All async methods return typed result objects (consistent shapes); all sync getters
read the shared console state. Every body sent matches an existing `Schema__*`
(briefs 02/03) — the API invents no field names (Decision #9).

```js
// PROPOSAL — names mirror the agentic-js-api house style; bodies match existing schemas.
window.__tool = {
  // ── async actions (wrap the HTTP surface) ──
  async screenshot({ url, format, full_page, javascript, click }),     // POST /screenshot
  async batch({ items }),                                              // POST /screenshot/batch (independent sessions)
  async sequence({ steps, screenshot_per_step }),                     // POST /sequence/execute (24-verb language)
  async inspect(body),                                                // POST /inspect (snapshot-once / probe-many)
  async browser(verb, body),                                          // POST /browser/{navigate|click|fill|get-content|get-url|screenshot}
  session: {
    async open(body),                                                 // POST /session/open
    async act(id, body),                                              // POST /session/{id}/act
    async probe(id, body),                                            // POST /session/{id}/probe
    async close(id),                                                  // POST /session/{id}/close
  },

  // ── console actions (drive the human UI from script) ──
  async run(workflowOrBody),    // execute a workflow file or raw body, render in the result pane
  loadExample(id),              // load gallery workflow W1..W9 into the active builder (brief 02)
  exportWorkflow(),             // current builder state → workflow file (brief 03)
  importWorkflow(obj),          // workflow file → builder
  setAuth({ token, authMode }), // 'apiKey' (X-API-Key) | 'proxy' (x-sgraph-access-token)

  // ── sync state getters ──
  getState(), getRuns(n), getActiveTab(),

  // ── meta (the self-describing contract) ──
  meta: {
    getMethods(),     // method list + typed signatures
    getVersion(),     // { api: '<brief-05 contract>', service: '<from /health/info>' }
    getManifest(),    // capability manifest = the /health/capabilities response, cached on load
    async getSkills(),// { human, browser, api } — see §4
    async health(),   // GET /health/status (auth-aware)
    getLog(),         // recent __tool call log (no token values)
  },
};
```

Mirrors the precedent's split exactly: discovery under `meta.*`, typed actions on the
root, shared state via getters. `connect(...)`/`generate(...)` in the infographic tool
map here to `setAuth(...)` + the action verbs.

---

## 4. `getSkills()` — the three self-describing docs

Returns the same trio the house pattern mandates (`building-agent-native.md`):

| Skill | Content | Source of truth |
|-------|---------|-----------------|
| **human** | Markdown quick-start + walkthrough for the browser user. | The pack's brief 01 + 04 user-facing copy. |
| **browser** | Setup + **full code examples for every operation**, for Playwright automation. | The Playwright runtime-discovery workflow (§5) + the `use-sg-playwright` recipes. |
| **api** | Machine-parseable: every method signature, params, returns, errors, window events. | **Generated** from the capability map + `sg-playwright-capabilities/SKILL.md` + the live `/health/capabilities`. |

Because `getSkills().api` is generated from the live capability surface, the page's
self-description is correct for **the exact deployment serving it** — closing D2/D4 at
the source rather than hand-syncing `capabilities.json`.

---

## 5. How an agent drives it (Playwright runtime-discovery)

Same workflow Claude uses for the infographic tool (`claude-playwright.md`), retargeted:

```javascript
// 1. discover the live spec for the EXACT deployed version
methods = page.evaluate('() => window.__tool.meta.getMethods()')
version = page.evaluate('() => window.__tool.meta.getVersion()')
skills  = page.evaluate('async () => await window.__tool.meta.getSkills()')

// 2. authenticate (auth-mode aware — the #1 first-attempt 401, see Decision #7)
await __tool.setAuth({ token: params.token, authMode: 'apiKey' })   // or 'proxy' for /pw

// 3. run a workflow (native /sequence/execute payload)
result = await __tool.sequence({ steps: params.steps, screenshot_per_step: true })

// 4. read typed results (per-step screenshots as base64, like infographic's imageSrc)
b64 = result.steps[0].screenshot_b64
```

This gives **brief 06** its UI-surface execute path: an integration test opens `GET /`
in headless Chromium and drives `window.__tool.sequence(...)` / `.run(...)` — testing
the human console and the agent API as one (brief 06 §4).

---

## 6. Packaging — Q1b RESOLVED → reuse the real `sg-tool-api` on `sg-layout`

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ✅ Q1b RESOLVED (2026-06-21) → option (A): reuse the real component.           ║
║                                                                                ║
║  The house pattern registers window.__tool via the shared `sg-tool-api` web    ║
║  component, served (with sg-layout + dev panels) from                          ║
║  /components/{category}/{name}/v{major}/v{minor}/v{patch}/.                     ║
║                                                                                ║
║  DECISION: build the console on `sg-layout` + `sg-tool-api` + sg-tokens — the   ║
║  SAME composition the admin dashboard uses                                     ║
║  (sgraph_ai_service_playwright__api_site/admin/index.html:19 <sg-layout>,       ║
║   :7 sg-tokens.css). window.__tool is registered by the REAL sg-tool-api        ║
║  component, NOT a hand-rolled inline shim.                                      ║
║                                                                                ║
║  Why (A) over the rev-2 inline-shim recommendation: the operator wants the     ║
║  powerful shared-component features (routing, tokens, the explorer/console/     ║
║  manifest dev panels) and alignment with every other tool. This REVERSES the    ║
║  old Decision #1 (single self-contained no-deps file) — see README rev 3.       ║
║                                                                                ║
║  Consequence (now mandatory): the page depends on those components + their      ║
║  asset URLs being reachable. Decision #11 / brief 08 require every component/    ║
║  asset/fetch URL to be root_path-aware (templated like window.API_BASE, or      ║
║  CDN-absolute https://dev.tools.sgraph.ai/...) so the SAME image works behind    ║
║  /pw and at root. The CDN host needs browser egress; an offline deployment      ║
║  vendors/prefix-templates instead (brief 08).                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 7. Constraints any final shape must honour

1. **Use the real `sg-tool-api` contract.** `window.__tool` is registered by the
   served `sg-tool-api` component (Q1b → A); the `window.__tool` + `meta.*` +
   `SGA_TOOL` surface is therefore the house pattern by construction, so agents that
   already know the pattern need no sg-playwright-specific knowledge.
2. **Root_path-aware asset/component URLs** (Decision #11, brief 08) — `sg-layout`,
   `sg-tool-api`, sg-tokens and the page's own JS load via a prefix-templated or
   CDN-absolute URL, never an absolute-rooted `/components/...` (breaks behind `/pw`).
3. **Auth-mode aware** — `X-API-Key` vs `x-sgraph-access-token` (Decision #7); a single
   hard-coded header reproduces the #1 first-attempt 401.
4. **Self-describing from live truth** — `getSkills().api` and `getManifest()` derive
   from `/health/capabilities` + the capability map, never from a pinned constant
   (closes D2/D4).
5. **Secret-safe** — `getLog()` and any state getter never expose the token; `setAuth`
   writes it but no getter reads it back.
6. **Component serving, not new service logic.** Reusing `sg-tool-api`/`sg-layout`
   needs a served-component path (the existing static-file convention, e.g.
   `sgraph_ai_service_playwright__api_site/components/.../v0/v0.1/v0.1.0/`, or the CDN),
   designed in brief 01 + brief 08 — **not** a new runtime endpoint or new service
   logic (Decision #9 still holds).
7. **Type_Safe N/A** — this is browser JS; CLAUDE.md's Type_Safe rules govern the
   *service*. The client still sends only real `Schema__*` field names (briefs 02/03).

---

## 8. Recommendation

Register `window.__tool` via the **real `sg-tool-api` web component, mounted on
`sg-layout`** (Q1b option A — operator-decided), with `getSkills()` generated from the
code-derived capability surface. This delivers the agentic JS API the house style
mandates, identical to every other sgraph.ai tool, and brings the explorer/console/
manifest dev panels for free. The trade for the dropped no-deps property is handled by
Decision #11 / brief 08: the component, token, and page-JS URLs are root_path-aware, so
the same Docker image still runs on laptop/CI/Web/Fargate/Lambda and works behind `/pw`
and at root. Phases 1-4 + 6 proceed without the JS-API layer; Phase 5 is purely
additive and never on the critical path — the console is fully usable from the human UI
(itself now on `sg-layout`) before `window.__tool` is exercised programmatically.
