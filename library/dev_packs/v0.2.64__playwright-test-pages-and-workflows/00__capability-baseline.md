---
title: "00 — Capability baseline"
file: 00__capability-baseline.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED (baseline distillation — facts traced to code)
parent: README.md
---

# 00 — Capability baseline

The single source of truth for this pack is the code-derived capability map:
`team/humans/dinis_cruz/claude-code-web/06/21/15/playwright-capability-map.md`.
This file distils it into the baseline the pack builds on — **what exists**, **what
the current UI exposes vs omits**, and **the D1-D6 discrepancies the pack must not
re-introduce.** Every claim carries a `file_path:line` so it is checkable. Read the
full map for the per-field schema tables; this is the orientation layer.

> **Rule:** where this pack, the reality doc, and the code disagree, **the code
> wins.** The reality doc and `capabilities.json` are demonstrably stale (D1, D2).

---

## 1. What exists today (the surface the UI should reach)

Route wiring: `sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py:103-114`.

**21 direct endpoints + 8 admin.**

| Family | Endpoints | Reached by current UI? |
|--------|-----------|------------------------|
| Index | `GET /` | n/a (it IS the UI) |
| Health | `GET /health/{info,status,capabilities}` | only `/health/status` (badge) |
| Browser one-shot | `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}` | **No** |
| Sequence | `POST /sequence/execute` (24-verb language) | **No** |
| Screenshot | `POST /screenshot`, `POST /screenshot/batch` | **Yes — the only thing exposed** |
| Inspect | `POST /inspect` (snapshot-once, probe-many) | **No** |
| Session | `POST /session/{open,{id}/act,{id}/probe,{id}/close}` | **No** |
| Metrics | `GET /metrics` (Prometheus text) | **No** |
| Auth | `GET /auth/set-cookie-form`, `POST /auth/set-auth-cookie` | **No** |
| Admin | `GET /admin/{health,info,env,boot-log,error,skills/{name},manifest,capabilities}` | **No** |

The 24-verb step vocabulary is the headline. Verb names (authoritative, cited
verbatim from `schemas/enums/Enum__Step__Action.py:8-34`):

```
navigate  click   fill    press   select  hover   scroll  wait    wait_for
screenshot  video_start  video_stop  evaluate  dispatch_event  set_viewport
get_content  get_url  get_text  get_html  get_dom_tree  get_a11y_tree  get_pdf
get_console_tail  get_network_failures
```

Detail per verb (fields/defaults/executor line) is in the capability map §3 and the
`sg-playwright-capabilities` skill; brief 02 cites the exact field names each example
workflow uses.

---

## 2. What the current UI exposes vs omits

Current page: `INDEX_HTML` in `Routes__Index.py` (lines 20-601). API base injected at
`Routes__Index.py:26` (`window.API_BASE="__API_BASE__"`, resolved per-request at
`:613-614`, default `/pw`). `post()` helper at `:484-487` sends `X-API-Key` when a key
is present. Health badge polls `/health/status` at `:529`.

**Two tabs only:**

- **Single** (`:200-238`) → `POST /screenshot`. Fields: `url`, `format` (png/html),
  `javascript`, `click`, `full_page`.
- **Batch** (`:242-269`) → `POST /screenshot/batch`. Modes: independent `items` vs
  sequential `steps` + `screenshot_per_step`. Per-card: `url`, `format`, `javascript`,
  `click`, `full_page`.

**Omitted (the backlog this pack addresses)** — from map §7(a): the entire
`/sequence` 24-verb language, `/inspect`, `/session/*`, `/browser/*` one-shots, PDF,
DOM/a11y/text/html extraction, console-tail + network-failures debug, the live
`/health/capabilities` + `/health/info` display, `/metrics`, `evaluate` return-types +
allowlist behaviour, full_page/viewport/selector-scoped/frame screenshots, capture
sinks, the `/auth/set-cookie-form` helper, and per-action `/docs` deep-links.

---

## 3. The real bugs in the current HTML/JS (Phase-1 fix list)

From map §7(b). Each is a concrete, citable defect — brief 01 designs the fix.

| Bug | Location | Symptom | Fix (brief 01) |
|-----|----------|---------|----------------|
| **Health badge sends no API key** | `Routes__Index.py:529` (`fetch(window.API_BASE + '/health/status')` with no headers) | On a key-protected deployment the badge 401s → always "degraded" even when healthy | Reuse the entered key + selected auth header (Decision #7); mark best-effort |
| **Unescaped `${url}` into HTML** | lightbox/thumb labels ~`:468`, `:471`, `:559`, `:563` (`title="${url}"`, template literals) | A URL with `"` or `<` breaks markup / is an XSS vector | HTML-escape every user-echoed string via the existing `escHtml` (`:479-481`), which is currently applied to `s.html` but NOT to `url` |
| **No `Array.isArray` guard on batch response** | `execBatch` `:445` (`data.screenshots || []`) → `showBatchGrid` | A malformed/non-array `screenshots` throws in the render path | Guard `Array.isArray(data.screenshots)` before iterating |
| **No null/empty guard in lightbox nav** | `renderLightbox` `:558-571` | Empty `lbShots` throws on property access | Early-return when `lbShots.length === 0` |
| **API key in cleartext localStorage** | `:288-291` | Acceptable for a dev tool but undeclared | In-UI note; combined with the `${url}` XSS fix this matters |
| **`oninput` with no debounce** | URL fields ~`:364`, `:291` | Fires every keystroke (localStorage write per char) | Debounce; minor |
| **Generic `r.json()` masks non-JSON errors** | `:327`, `:443` | A 500 HTML page → JSON parse error hides the real HTTP status | Read status first; fall back to `r.text()` on parse failure |
| **`format=html` mislabeled as a "screenshot format"** | `:208-213` toggle, `Enum__Screenshot__Format` (`png`/`html`) | "HTML source" is a render mode, not an image format; confuses first-time users | Relabel as "Render mode: Image / HTML source"; brief 01 |
| **No `label`/`for` on API-key input** | `:186-191` | a11y gap | Associate label |

---

## 4. The D1-D6 discrepancies — what the pack must NOT re-introduce

From map §6. These are the traps; the pack's designs are written to avoid each.

| # | Stale source | Code reality | How this pack avoids it |
|---|--------------|--------------|-------------------------|
| **D1** | `CLAUDE.md` + reality doc `playwright-service/index.md:16,102`: "16 direct endpoints", "Routes__Session removed in v0.1.24" | `Fast_API__Playwright__Service.py:110-111` wires **both `Routes__Inspect` AND `Routes__Session`**. Real count is **21** direct (+8 admin). | UI tabs (Decision #5) include Inspect + Session because they exist. Pack flags D1 to Librarian (sign-off) but does **not** edit the reality doc. |
| **D2** | `capabilities.json:3` declares `"version": "v0.1.29"`; `/admin/capabilities` serves it | Repo `version` is **v0.2.63**. The root stub is frozen. | The UI reads `GET /health/capabilities` (the live `Schema__Service__Capabilities`, populated by `Capability__Detector`) — **never** the stale `capabilities.json`. Decision #2. |
| **D3** | `capabilities.json:9` `declared_narrowing: []` matches the stale stub | Consistent with the stub, not the running version | Not surfaced in UI; no action. |
| **D4** | `core/skills/skill__agent.md:2` self-labels "FIRST-PASS PLACEHOLDER (v0.1.29)" and predates the 24-verb language | We are at v0.2.63 | In-app docs (brief 04) generate from the **live** capability surface, not from `skill__agent.md`. So docs can't inherit the placeholder's staleness. |
| **D5** | UI exposes only `/screenshot` + `/screenshot/batch` | Service supports 21 endpoints incl. the full 24-verb language | **This pack's entire reason for existing.** Briefs 01-02 expose the omitted surface. |
| **D6** | `health/capabilities` advertises `supports_video`, `available_browsers`, `supported_sinks`, `has_vault_access`, etc. but the UI never fetches it | Real, populated by `Capability__Detector` | Decision #2 makes the UI capability-driven: it fetches `/health/capabilities` on load and shapes itself to the response. Closes D6 at the root. |

> The **consumer skill** `library/skills/use-sg-playwright/SKILL.md` is accurate and
> current (24 verbs, `/inspect`, `/session/*`, auth split, recipes). When it
> contradicts the reality doc, the skill (and the code) is right.

---

## 5. Prior-pack cross-check (v0.2.9 → now)

The closest precedent, `library/dev_packs/v0.2.9__improve-playwritght-api/brief_3__playwright_service_features.md`,
requested several step verbs. **Most now exist** — the new pack must not re-request
them:

| v0.2.9 feature request | Status today | Evidence |
|------------------------|--------------|----------|
| FR-1 `wait_for_function` | **EXISTS** as `wait_for` with a `function` field | map §3 `wait_for` row; `use-sg-playwright/SKILL.md` predicate table |
| FR-2 `wait` (fixed delay) | **EXISTS** as verb `wait` (`duration_ms`) | `Enum__Step__Action.WAIT = "wait"`; map §3 |
| FR-3 `scroll to_bottom` | Verb `scroll` EXISTS (`selector`/`x`/`y`); `to_bottom` shorthand **not confirmed** | map §3 `scroll` row — fields are `selector`/`x`/`y` only |
| FR-4 `wait_after_ms` on base step | **Not present** — base fields are `action`/`id`/`continue_on_error`/`timeout_ms` | `schemas/steps/Schema__Step__Base.py:16-20` |
| FR-5 `screenshot.wait_for_selector` | **Not present** — screenshot fields are `full_page`/`selector`/`save_as`/`viewport`/`frame_selector` | map §3 `screenshot` row |
| FR-6 `get_content.content` always-str | `get_content` EXISTS; result field documented as `content/content_format/content_type` | map §3 + result-field table |

Per Decision #9, this pack proposes **no new verbs** — FR-3/4/5 remain open feature
requests for a *future* pack and are out of scope here. The pack's job is to expose
what already exists.

---

## 6. Pointers

| Thing | Path |
|-------|------|
| Full capability map (source of truth) | `team/humans/dinis_cruz/claude-code-web/06/21/15/playwright-capability-map.md` |
| Route wiring | `sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py:103-114` |
| Test page (target) | `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` (`INDEX_HTML`, `:20-601`) |
| Step action enum | `sg_compute_specs/playwright/core/schemas/enums/Enum__Step__Action.py:8-34` |
| Step registry | `sg_compute_specs/playwright/core/dispatcher/step_schema_registry.py:51-85` |
| Capabilities (live, what UI reads) | `Schema__Service__Capabilities` via `GET /health/capabilities` |
| Capabilities stub (stale, do NOT read) | `capabilities.json` (repo root, v0.1.29) |
| Consumer skill (accurate) | `library/skills/use-sg-playwright/SKILL.md` |
| Capability lookup skill | `library/skills/sg-playwright-capabilities/SKILL.md` |
