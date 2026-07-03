---
title: "Agentic JS API pattern — research grounding for dev-pack brief 05"
file: agentic-js-api-research.md
author: Claude (orchestrator)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ claude/amazing-pasteur-3srh6x
status: RESEARCH — source grounding for library/dev_packs/v0.2.64__.../05__js-api.md
sources:
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/how-it-works.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/claude-playwright.md
  - https://sgraph.ai/en-gb/library/use-cases/agentic-js-api/building-agent-native.md
note: "Provided by Dinis as the canonical precedent for point (f) — 'how we did the JS API on the multiple tools we developed'. This RESOLVES the brief-05 open question. Append '.md' to any sgraph.ai page path to read the markdown version."
---

# Agentic JS API pattern (sgraph.ai) — grounding for sg-playwright

## What it is
A **dual-surface** design: a tool ships BOTH a human-facing UI and a JavaScript API for agents,
backed by ONE shared tool state. "Both interact with the same underlying tool state. Neither is a
wrapper around the other." Agents drive the tool through a stable, typed JS surface instead of
reverse-engineering HTML — which removes Playwright's two classic failure modes (UI changes break
automations silently; timing/shadow-DOM non-determinism).

Three defining properties:
1. **Self-describing** — ships its own docs via `getSkills()` (human + browser + machine-readable).
2. **Deterministic** — typed signatures, explicit params, consistent return shapes; same input → same output.
3. **Dual-surface** — one page serves human and agent needs equally.

## Global objects
- `window.__tool` — the live tool instance executing in the browser.
- `window.__tool.meta` — discovery methods: `getMethods()`, `getVersion()`, `getManifest()`,
  `getSkills()`, `health()`, `getLog()`.
- `window.SGA_TOOL` — frozen event-name constants.
- `window.__tool_registry` — `find()`, `findAll()`, `findById()` for multi-instance pages.
- Window events for async ops, e.g. `tool:generation:started`, `tool:generation:complete`.

## Method surface (example tool — infographic generator, v0.1.37)
- **Async:** `connect({ apiKey, model? })`, `generate({ prompt?, model?, renderUI? })`.
- **Sync state:** `getState()`, `getGenerations(n?)`, `getPrompt()`, `getModel()`.
- **Sync config:** `setSystemPrompt(text)`, `setPrompt(text)`, `setModel(id)`, `setTemplate(nameOrId)`.
- **Sync control:** `stop()`.
- **Meta:** `getMethods`, `getVersion`, `getManifest`, `getSkills`, `health`, `getLog`.
- Result objects carry typed fields, e.g. `imageSrc` (base64 data URL), `duration`, `callId` (UUID).

## getSkills() — three self-describing docs
- **Human** — markdown quick-start + feature walkthrough for browser users.
- **Browser** — installation/setup + full code examples for every operation (for Playwright automation).
- **API** — structured, machine-parseable markdown: every method signature, params, returns, errors, window events.
> "The documentation never drifts from the implementation because it is served by the implementation."

## Web-component architecture
- `sg-tool-api` — the bridge that registers `window.__tool` on page load (instantiates an `SgToolApi`),
  handles method dispatch, and exposes the `meta.*` discovery methods.
- `sg-layout` — panel/routing container.
- Component layer — the actual handlers (LLM requests, generators, exporters, model pickers).
- Dev tools — `sg-tool-api-explorer`, `sg-tool-api-console`, `sg-tool-api-manifest`.
- Components are versioned and served from `/components/{category}/{name}/v{major}/v{minor}/v{patch}/`.
- Components can themselves be self-describing via `window.__component.meta.getSkill()`.

## How Claude drives it via Playwright (the runtime-discovery workflow)
```javascript
// 1. discover the live spec for the EXACT deployed version
methods = page.evaluate('() => window.__tool.meta.getMethods()')   // ~12 methods
version = page.evaluate('() => window.__tool.meta.getVersion()')
skills  = page.evaluate('async () => await window.__tool.meta.getSkills()')

// 2. connect + configure + run
await __tool.connect({ apiKey: params.key })
__tool.setTemplate('architecture')
result = await __tool.generate({ prompt: params.prompt })   // { imageSrc, duration, ... }

// 3. retrieve output (base64 PNG)
b64 = result['imageSrc'].split(',', 1)[1]   // strip data: prefix
```
Concurrency: `Promise.all([__tool.generate(...), __tool.generate(...)])` with independent `callId`s.
Persistent styling: `__tool.setSystemPrompt('You are a professional infographic designer...')`.

## Mandatory conditions for an "agent-native" tool
1. `window.__tool` registered on page load (via `sg-tool-api`).
2. Core operations exposed as **typed methods** (`connect()`, `generate()`, `getState()`) — not DOM pokes.
3. Tool ships its own skill files via `getSkills()`.

---

## Application to sg-playwright (for brief 05)
The sg-playwright "Try it out" page should itself become an **agent-native `window.__tool`**:
- Expose `window.__tool` whose typed methods wrap the service endpoints the page already calls:
  e.g. `screenshot({url, format, full_page, javascript, click})`, `batch({items})`,
  `sequence({steps, screenshot_per_step})`, `inspect(...)`, `session.open/act/probe/close(...)`,
  `health()`, `capabilities()`, `metrics()`.
- `window.__tool.meta.getSkills()` returns the human/browser/API trio — and the **API skill can be
  generated from the same code-derived capability map** (`.../06/21/15/playwright-capability-map.md`)
  and the new `library/skills/sg-playwright-capabilities/SKILL.md`, so it never drifts (kills D2/D4).
- This is recursive/elegant: an agent uses Playwright (the service) to drive a page (the test console)
  whose own `window.__tool` then drives the Playwright service — every layer self-describing.
- The workflow import/export (brief 03) becomes the natural payload type for `__tool.sequence(...)`.
- Open sub-question for the operator: align method NAMES + the `sg-tool-api` component reuse with the
  existing sgraph.ai component library (served from `/components/...`) vs. a self-contained inline shim
  in `INDEX_HTML`. The current test page is one self-contained HTML/JS file with no external deps —
  decide whether brief 05 reuses the `sg-tool-api` web component or ships a minimal inline `window.__tool`.
