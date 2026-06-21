---
title: "04 — In-app docs & help"
file: 04__docs-and-help.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED — design only, no runtime code
parent: README.md
covers: "User point (d) — in-app docs and help"
---

# 04 — In-app docs & help

Covers **point (d)**: documentation surfaced inside the console. The governing
principle: **docs are generated from the service's own self-description, never
hand-maintained** — so they cannot drift the way `capabilities.json` (D2),
`skill__agent.md` (D4), and the reality doc (D1) have.

---

## 1. Sources the page reads (live, not baked)

| Source | Endpoint | What it documents |
|--------|----------|-------------------|
| Capabilities | `GET /health/capabilities` | what THIS deployment can do (video? sinks? browsers? vault? memory budget?) — the bootstrap result (brief 01 §1) |
| Service info | `GET /health/info` | service/playwright/chromium versions, deployment target, `code_source` |
| OpenAPI | `GET /docs` (Swagger UI) + the underlying `/openapi.json` | every endpoint's request/response schema, live against the running stack |
| Admin skills | `GET /admin/skills/{human,browser,agent}` | the served SKILL markdown (human/browser/agent personas) |

The verb reference (§2) is generated from a **single static verb table embedded in
`INDEX_HTML`** — the same table that drives the Sequence builder (brief 01 §3.2). One
table, two consumers (builder + docs), so the docs and the controls can never
disagree. That table is the only "baked" doc data, and it is small, explicit, and
co-located with the builder that uses it.

> Why a co-located table rather than `/openapi.json` for the verb fields? `/sequence`
> takes `steps: List[dict]` (heterogeneous, parsed by the `action` discriminator via
> `STEP_SCHEMAS`) — OpenAPI advertises the envelope, not the per-verb field shapes.
> The per-verb fields live in `schemas/steps/` and the registry
> (`dispatcher/step_schema_registry.py:51-85`). The embedded table mirrors those; a
> Phase-4 stretch goal is to have a build-time check assert the table matches the
> registry so it cannot rot (brief 06 §5).

---

## 2. In-page step-verb reference

A "Reference" pane (reachable from the `?Help` header link, brief 01) renders the
24-verb table: verb name, one-line purpose, fields with types + defaults, and the
result field it populates. Sourced from the embedded verb table; values match the
capability map §3.

Layout sketch:

```
┌─ Step verb reference ──────────────────────────── search [____] ┐
│  navigate     Go to a URL                                       │
│    url* (Url)   wait_until (load|domcontentloaded|networkidle)  │
│    referer (Url)                          → result: (none)      │
│  ────────────────────────────────────────────────────────────  │
│  get_dom_tree Compact JSON DOM tree                             │
│    root_selector  max_depth (8)  include_invisible (false)      │
│                                           → result: dom_tree    │
│  ... (all 24) ...                                               │
│  Enums: wait_until {load,domcontentloaded,networkidle} ·        │
│         button {left,right,middle} · key {Enter,Tab,Escape,...} │
│         return_type {json,string,number,boolean} · ...          │
└─────────────────────────────────────────────────────────────────┘
```

Each verb row has a **"+ add to sequence"** action that drops a pre-filled step into
the Sequence builder — docs and authoring are the same surface.

---

## 3. Contextual help on each control

Every builder field carries a `?` affordance (title attribute + on-click popover)
explaining it, sourced from the embedded table's per-field notes:

- `wait_for` predicate radios show the precedence table from
  `use-sg-playwright/SKILL.md` ("function > network_idle_ms > text > selector...").
- `evaluate` / `wait_for: function` show the **allowlist** warning (deny-all default;
  failure is `partial`/`failed`, not 422) — Q3.
- The capture-sink picker explains "no sink ⇒ screenshot passes but emits no
  artefact; pick `inline` to get `inline_b64` back" (the #1 gotcha).
- The auth-mode toggle explains the `X-API-Key` (direct) vs `x-sgraph-access-token`
  (`/pw` proxy) split — and that sending the wrong header 401s every call.

---

## 4. Per-endpoint `/docs` deep-links

The header keeps the `API docs ↗` link (`Routes__Index.py:177`), and each tab adds a
"schema ↗" link to the relevant OpenAPI operation in Swagger UI
(`<API_BASE>/docs#/<tag>/<operationId>`). This maps a UI action to its live schema —
closing map §7(a)#15 (the header links to `/docs` generally but nothing maps a UI
action to its schema).

---

## 5. Why this can't drift (D1/D2/D4 defence)

| Drift risk | Defence |
|------------|---------|
| Deployment lacks a capability the docs claim | Capabilities pane is the live `/health/capabilities` response (Decision #2). |
| Version shown is the stale `capabilities.json` v0.1.29 (D2) | Version comes from `/health/info` (`service_version`), never the root stub. |
| Verb reference goes stale vs the registry (D4-style) | Verb table is co-located with the builder; Phase-4 build-time check (brief 06 §5) asserts it matches `STEP_SCHEMAS`. |
| Endpoint count wrong (D1) | The Service tab renders what's actually wired (the UI calls the live endpoints); it does not echo the reality doc's "16". |

The result: a first-time operator opening `GET /` gets accurate, deployment-specific
documentation without anyone hand-editing a doc string — and the in-app docs become
the antidote to the very discrepancies the capability map found.
