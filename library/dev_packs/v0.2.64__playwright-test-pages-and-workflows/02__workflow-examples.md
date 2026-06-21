---
title: "02 — Workflow examples (gallery + test fixtures)"
file: 02__workflow-examples.md
author: Architect (Claude)
date: 2026-06-21
repo: "SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)"
status: PROPOSED — example bodies, no runtime code
parent: README.md
covers: "User point (b) — multiple complex example workflows"
---

# 02 — Workflow examples

Covers **point (b)**: a gallery of genuinely complex workflows in the **real** step
language. Each is a runnable `POST /sequence/execute` body (or `/inspect` /
`/screenshot/batch` where noted), with commentary. Every verb is cited from
`schemas/enums/Enum__Step__Action.py:8-34`; every field from the per-verb schema rows
in the capability map §3 / `sg-playwright-capabilities/SKILL.md`.

These serve **two jobs**: (1) one-click "example gallery" seeds in the console
(brief 01), and (2) integration-test fixtures (brief 06 maps each to an assertion).

> **Capture note (the #1 gotcha):** a `screenshot` step "passes" but emits **no
> artefact** unless a capture sink is set. To get `inline_b64` back, every workflow
> below that captures sets `"capture_config": {"screenshot": {"enabled": true,
> "sink": "inline"}}` at the top level (map §4; `use-sg-playwright/SKILL.md` gotchas).

---

## W1 — Multi-step form fill + wait_for + screenshot-per-step

Exercises `navigate`, `fill`, `click`, `wait_for` (text), `screenshot`. Set
`capture_config.screenshot_per_step`-style by adding a `screenshot` after each action.

```json
POST /sequence/execute
{
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } },
  "sequence_config": {},
  "steps": [
    { "action": "navigate", "url": "https://example.com/login", "wait_until": "domcontentloaded" },
    { "action": "fill",     "selector": "#email",    "value": "demo@example.com" },
    { "action": "fill",     "selector": "#password", "value": "hunter2" },
    { "action": "screenshot", "full_page": false },
    { "action": "click",    "selector": "button[type=submit]" },
    { "action": "wait_for", "text": "Welcome", "timeout_ms": 10000 },
    { "action": "screenshot", "full_page": true }
  ]
}
```

Commentary: `wait_for` with `text` (not a blind `wait`) gates the post-submit
capture. Each `screenshot` yields `step_results[i].artefacts[0].inline_b64`.

---

## W2 — Login then navigate then extract

`navigate` → `fill`/`click` → `wait_for` → `navigate` (deep link) → `get_text` +
`get_url`.

```json
POST /sequence/execute
{
  "capture_config": {},
  "sequence_config": {},
  "steps": [
    { "action": "navigate", "url": "https://app.example.com/login" },
    { "action": "fill",     "selector": "#user", "value": "demo" },
    { "action": "fill",     "selector": "#pass", "value": "demo" },
    { "action": "click",    "selector": "#sign-in" },
    { "action": "wait_for", "url_pattern": "**/dashboard**", "timeout_ms": 15000 },
    { "action": "navigate", "url": "https://app.example.com/reports/42" },
    { "action": "wait_for", "selector": "[data-ready=true]" },
    { "action": "get_url" },
    { "action": "get_text", "selector": "main" }
  ]
}
```

Commentary: `wait_for: url_pattern` confirms the post-login redirect; the second
`navigate` reuses the authenticated context. `get_url`→`url`, `get_text`→`text` in the
step results.

---

## W3 — Scrape DOM tree + accessibility tree (via /inspect, the efficient pattern)

`/inspect` snapshots once, probes many. All probe verbs are read-only.

```json
POST /inspect
{
  "navigate": { "url": "https://sgraph.ai" },
  "settle":   [ { "action": "wait_for", "state": "networkidle" } ],
  "probes": {
    "current_url": { "action": "get_url" },
    "page_text":   { "action": "get_text" },
    "dom":         { "action": "get_dom_tree",  "max_depth": 6, "include_invisible": false },
    "a11y":        { "action": "get_a11y_tree", "interesting_only": true },
    "html_head":   { "action": "get_html", "selector": "head" }
  },
  "diagnostics_on_fail": true
}
```

Commentary: results land under `probe_results.{current_url,page_text,dom,a11y,html_head}`.
`get_dom_tree` pierces open shadow roots; `get_a11y_tree` returns the CDP flat
`{nodes:[...]}` shape (filter `ignored === false` for "interesting").

---

## W4 — Render a PDF

`navigate` → `wait_for` → `get_pdf`. PDF needs a capture sink (PDF artefact).

```json
POST /sequence/execute
{
  "capture_config": { "pdf": { "enabled": true, "sink": "inline" } },
  "sequence_config": {},
  "steps": [
    { "action": "navigate", "url": "https://sgraph.ai/about", "wait_until": "load" },
    { "action": "wait_for", "state": "networkidle" },
    { "action": "get_pdf", "format": "A4", "landscape": false, "print_background": true }
  ]
}
```

Commentary: `get_pdf`→`step_results[i].artefacts[]` of `artefact_type: PDF`. `format`
defaults `A4`, `print_background` defaults `true`.

---

## W5 — Capture console + network failures on a failing page (debug)

Read-only `/inspect` with the two diagnostic probes — seeds the console's **Debug tab**
(brief 01 §3.6).

```json
POST /inspect
{
  "navigate": { "url": "https://example.com/broken" },
  "settle":   [],
  "probes": {
    "console":  { "action": "get_console_tail", "lines": 200 },
    "failures": { "action": "get_network_failures" },
    "shot":     { "action": "screenshot", "full_page": true }
  },
  "diagnostics_on_fail": true
}
```

Commentary: `get_console_tail`→`console_log`, `get_network_failures`→`network_failures`.
Note the console/network buffers capture **load-time** events
(`page.on('console')` / `page.on('requestfailed')`), so probe after the navigate
settles.

---

## W6 — Viewport + frame-scoped + selector-scoped capture

Exercises `set_viewport`, then three `screenshot` variants: full-page, selector-scoped,
and frame-scoped.

```json
POST /sequence/execute
{
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } },
  "sequence_config": {},
  "steps": [
    { "action": "navigate",     "url": "https://example.com" },
    { "action": "set_viewport", "viewport": { "width": 1440, "height": 900 } },
    { "action": "screenshot",   "full_page": true },
    { "action": "screenshot",   "selector": "header.site-header" },
    { "action": "screenshot",   "frame_selector": "iframe#embed", "viewport": { "width": 800, "height": 600 } }
  ]
}
```

Commentary: covers the screenshot fields the current UI hides
(`viewport`/`selector`/`frame_selector`) — only `full_page` is exposed today (map
§7(a)#12).

---

## W7 — Multi-step interaction: hover → select → press → scroll → evaluate

Wide verb coverage incl. the allowlist-gated `evaluate`.

```json
POST /sequence/execute
{
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } },
  "sequence_config": {},
  "steps": [
    { "action": "navigate", "url": "https://example.com/catalog" },
    { "action": "hover",    "selector": "nav .menu" },
    { "action": "select",   "selector": "#sort", "values": ["price-asc"] },
    { "action": "press",    "selector": "#search", "key": "Enter" },
    { "action": "scroll",   "y": 2000 },
    { "action": "wait_for", "selector": ".results .item" },
    { "action": "evaluate", "expression": "document.querySelectorAll('.item').length", "return_type": "number" },
    { "action": "screenshot", "full_page": true }
  ]
}
```

Commentary: `select.values` is a list; `press.key` is an `Enum__Keyboard__Key` value.
The `evaluate` step is **allowlist-gated** — on a default deny-all deployment it
reports `error_message` containing "allowlist" and the sequence goes `partial`, NOT
422. The console flags this (brief 01 §3.2, Q3). Use this workflow to demonstrate the
allowlist behaviour in the gallery.

---

## W8 — Batch independent screenshots (gallery for /screenshot/batch)

`Schema__Screenshot__Batch__Request` mode 1 (`items`, N independent sessions).

```json
POST /screenshot/batch
{
  "items": [
    { "url": "https://sgraph.ai",        "full_page": true },
    { "url": "https://example.com",      "format": "png" },
    { "url": "https://example.org",      "javascript": "document.body.style.zoom='80%'" }
  ]
}
```

And mode 2 (`steps` in one session + per-step capture):

```json
POST /screenshot/batch
{
  "steps": [
    { "url": "https://example.com/page1" },
    { "url": "https://example.com/page2" },
    { "url": "https://example.com/page3" }
  ],
  "screenshot_per_step": true
}
```

Commentary: the `javascript` field on `/screenshot` runs via its OWN `allow_all`
runner — distinct from the allowlist-gated `evaluate` verb (map §2.3 / §5). This is
why "run JS then capture" works on `/screenshot` but `evaluate` in `/sequence` does
not on a default deployment.

---

## W9 — Stateful session: open, act, probe, probe, close

Exercises `/session/*` (Session tab, brief 01 §3.4). Amortises navigate across probes.

```
POST /session/open
  { "browser_config": {} }
  → { "session_id": "<sid>", "expires_in_ms": 300000 }

POST /session/<sid>/act        (sequence-shape body)
  { "steps": [ { "action": "navigate", "url": "https://app.example.com" },
               { "action": "wait_for", "text": "Dashboard" } ] }

POST /session/<sid>/probe      (inspect-shape body, NO navigate)
  { "settle": [], "probes": { "url": { "action": "get_url" },
                              "text": { "action": "get_text" } } }

POST /session/<sid>/probe      (again — page state persists)
  { "settle": [], "probes": { "dom": { "action": "get_dom_tree", "max_depth": 4 } } }

POST /session/<sid>/close
  → { "session_id": "<sid>", "closed": true }
```

Commentary: `act` returns `Schema__Sequence__Response`; `probe` returns
`Schema__Inspect__Response`. Only available when `capabilities.supports_persistent`.

---

## Gallery manifest

The console (brief 01) ships these as one-click "Load example" buttons. Each loads
into the relevant tab's builder so the user can edit before running.

| ID | Title | Endpoint | Verbs / shape exercised |
|----|-------|----------|-------------------------|
| W1 | Form fill + wait + per-step shots | `/sequence/execute` | navigate, fill, click, wait_for(text), screenshot |
| W2 | Login then navigate then extract | `/sequence/execute` | wait_for(url_pattern), get_url, get_text |
| W3 | Scrape DOM + a11y | `/inspect` | get_dom_tree, get_a11y_tree, get_html, get_url, get_text |
| W4 | Render PDF | `/sequence/execute` | get_pdf (+ pdf capture sink) |
| W5 | Console + network on a failing page | `/inspect` | get_console_tail, get_network_failures |
| W6 | Viewport/frame/selector capture | `/sequence/execute` | set_viewport, scoped screenshot |
| W7 | Hover/select/press/scroll/evaluate | `/sequence/execute` | hover, select, press, scroll, evaluate (allowlist) |
| W8 | Batch screenshots (items + steps) | `/screenshot/batch` | items[], steps[]+screenshot_per_step, /screenshot allow_all JS |
| W9 | Stateful session | `/session/*` | open/act/probe/probe/close |
