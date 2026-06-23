---
title: "01 — Proposed UX pages (capability-driven console)"
file: 01__proposed-ux-pages.md
author: Architect (Claude)
date: 2026-06-21
repo: "SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)"
status: PROPOSED — design only, no INDEX_HTML changes
parent: README.md
covers: "User point (a) — test multiple features"
---

# 01 — Proposed UX pages

Covers the operator's **point (a)**: a test page that drives multiple features, not
just `/screenshot`. The design **builds the console on the shared sgraph.ai
component library** — `sg-layout` + `sg-tool-api` + sg-tokens (Decision #1, rev 3,
matching the admin dashboard at `sgraph_ai_service_playwright__api_site/admin/index.html:19,7`)
— and reorganises it as a **capability-driven console** (Decision #2) whose visible
controls follow the deployment's own `/health/capabilities`. Because the page now
loads served components and asset URLs, **every asset/component/fetch URL must be
root_path-aware** so the console works behind the `/pw` proxy and at root
(Decision #11, brief 08).

> No `INDEX_HTML` edits in this pack. This is the spec a downstream Dev phase
> implements against the existing `Routes__Index.py` seam (`__API_BASE__` injection
> at `:26`/`:613-614`, `post()` helper at `:484-487`). Component/asset URLs are
> templated through the same resolved root_path prefix as `window.API_BASE` (brief 08).

---

## 1. Bootstrap (runs once on load) — closes D6

On `DOMContentLoaded`, before rendering tabs:

1. `GET /health/info` → `Schema__Service__Info` (`service_version`,
   `playwright_version`, `chromium_version`, `deployment_target`, `code_source`,
   `capabilities`).
2. `GET /health/capabilities` → `Schema__Service__Capabilities`
   (`supports_video`, `available_browsers[]`, `supported_sinks[]`,
   `max_session_lifetime_ms`, `has_vault_access`, `has_s3_access`,
   `has_network_egress`, `proxy_configured`, `memory_budget_mb`,
   `supports_persistent`).

The response shapes the console:

| Capability field | UI effect |
|------------------|-----------|
| `supports_video === false` | Hide `video_start`/`video_stop` from the verb palette; grey "video unavailable" |
| `supported_sinks` | Sink picker offers only these; default `INLINE` if present |
| `available_browsers` | Browser selector (Session/Sequence `browser_config`) limited to these |
| `supports_persistent === false` | Disable the **Session** tab with a tooltip |
| `has_vault_access === false` | Hide the credentials/vault-cookie inputs |
| `proxy_configured` | Show a "egress via proxy" note in the Service pane |

Both calls use the selected auth mode + key (Decision #7), so the bootstrap works on
key-protected deployments — and the **health badge** is folded into this bootstrap,
fixing the always-degraded bug (map §7(b)#1, `Routes__Index.py:529`).

---

## 2. Top-level layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SG Playwright Service          ● healthy   v0.2.63 · chromium 131 · fargate   │  header: badge + /health/info summary
│ [ Auth: (•) X-API-Key  ( ) x-sgraph-access-token ]  [ key ········· 👁 ]      │  auth-mode toggle (Decision #7)
│                                                  API docs ↗   Skills ↗  ?Help  │
├───────────────┬──────────────────────────────────────────────────────────────┤
│  TABS (left)  │   REQUEST BUILDER (centre)        │   RESULT / RESPONSE (right) │
│  ───────────  │   ─────────────────────────────   │   ──────────────────────── │
│  ▸ Screenshot │   <per-tab form / step builder>   │   image | json | timings   │
│  ▸ Sequence   │                                   │   step-by-step results     │
│  ▸ Inspect    │   [ ▶ Execute ]                   │   trace-id (click-to-copy) │
│  ▸ Session    │   [ Copy curl ] [ Copy JSON ]     │   artefacts (b64/links)    │
│  ▸ Browser    │   [ Save ] [ Load ] [ Examples ]  │                            │
│  ▸ Debug      │                                   │                            │
│  ▸ Service    │                                   │                            │
└───────────────┴───────────────────────────────────┴────────────────────────────┘
```

Three-column shell: tab rail · request builder · response viewer. The current
two-column grid (`Routes__Index.py:50` `grid-template-columns:360px 1fr`) becomes a
tab-rail + builder + viewer. Reuses the existing dark theme tokens
(`:28-33` `--bg/--surface/--accent/...`).

Tabs map 1:1 to endpoint families (Decision #5). A tab is disabled (greyed, tooltip)
when the capability bootstrap says the deployment can't do it.

---

## 3. Per-tab design

### 3.1 Screenshot tab (migrates today's Single + Batch)

Sub-modes: **Single** (`POST /screenshot`) · **Batch** (`POST /screenshot/batch`,
`items` vs `steps` + `screenshot_per_step`). Fields per `Schema__Screenshot__Request`:
`url`, `click`, `javascript`, `full_page`, and **`format` relabelled** — the toggle
becomes **"Render: ( ) Image  ( ) HTML source"** to kill the "html is a screenshot
format" confusion (map §7(b)#8). The lightbox/grid renderer is carried over but with
the XSS + null-guard fixes (§5 below).

### 3.2 Sequence tab — the 24-verb step builder (headline)

The centrepiece. Builds `Schema__Sequence__Request` for `POST /sequence/execute`.

```
┌─ Sequence builder ────────────────────────────────────────────┐
│  Steps:                                            [+ add step]│
│  ┌─ 1 ─ navigate ──────────────────────────────── [⋮][×] ─┐   │
│  │  url        [ https://example.com            ]          │   │
│  │  wait_until [ load ▾ ]   referer [           ]          │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌─ 2 ─ wait_for ─────────────────────────────── [⋮][×] ─┐    │
│  │  ◉ text     [ Welcome ]   ○ selector  ○ url_pattern    │    │
│  │  ○ function [ … ] ⚠ needs server JS allowlist          │    │
│  └────────────────────────────────────────────────────────┘   │
│  ┌─ 3 ─ screenshot ───────────────────────────── [⋮][×] ─┐    │
│  │  □ full_page  selector [ ] viewport [WxH] frame_sel [ ]│    │
│  └────────────────────────────────────────────────────────┘   │
│  Capture: sink [ inline ▾ (from supported_sinks) ]  □ per-step │
│  ▸ Advanced: browser_config · credentials · sequence_config   │
└────────────────────────────────────────────────────────────────┘
```

**Verb palette** drives the "add step" menu. Each verb renders only its real fields
(from `Enum__Step__Action` + the per-verb schema in `schemas/steps/`):

| Verb | Builder fields rendered |
|------|-------------------------|
| `navigate` | `url`*, `wait_until` (load/domcontentloaded/networkidle), `referer` |
| `click` | `selector`*, `button` (left/right/middle), `click_count`, `delay_ms`, `force` |
| `fill` | `selector`*, `value`*, `clear_first` |
| `press` | `selector`, `key`* (Enum__Keyboard__Key dropdown) |
| `select` | `selector`*, `values`* (list) |
| `hover` | `selector`* |
| `scroll` | `selector`, `x`, `y` |
| `wait` | `duration_ms` |
| `wait_for` | radio over `text`/`selector`/`url_pattern`/`function`/`network_idle_ms`/`state`; `visible`, `selector_gone` |
| `screenshot` | `full_page`, `selector`, `save_as`, `viewport`, `frame_selector` |
| `set_viewport` | `viewport`* (width/height) |
| `evaluate` | `expression`*, `return_type` (json/string/number/boolean) — **allowlist hint** |
| `dispatch_event` | `selector`*, `event_type`*, `event_init` |
| `video_start`/`video_stop` | only when `supports_video`; `codec`, `save_as` |
| `get_content` | `selector`, `content_format` (html/text), `inline_in_response` |
| `get_url` / `get_network_failures` | (no fields) |
| `get_text` / `get_html` | `selector`, `inline_in_response` |
| `get_dom_tree` | `root_selector`, `max_depth`, `include_invisible` |
| `get_a11y_tree` | `root_selector`, `interesting_only` |
| `get_pdf` | `format`, `landscape`, `print_background` |
| `get_console_tail` | `lines` |

Steps are reorderable (drag `⋮`) and each carries the base fields `id`,
`continue_on_error`, `timeout_ms` under an "Advanced" expander.

**Allowlist affperdance (Q3):** `evaluate` and `wait_for: function` show an inline
"⚠ this step needs the server's JS allowlist; default deployments deny-all — it will
report `failed`/`partial`, not 422" hint. The UI never tries to mutate the allowlist.

**Result renderer:** `Schema__Sequence__Response` → a step-by-step list. Per step:
status pill (`passed`/`failed`/`skipped`), `duration_ms`, and the verb's lifted field
(map §3 result table) — `get_url`→`url`, `get_text`→`text`, `get_dom_tree`→`dom_tree`
(collapsible JSON), `screenshot`/`get_pdf`→`artefacts[].inline_b64` thumbnail,
`evaluate`→`return_value`. Top bar shows `status`, `steps_passed/total`,
`total_duration_ms`, `trace_id` (click-to-copy), and the `timings` block.

### 3.3 Inspect tab — snapshot-once, probe-many

Builds `Schema__Inspect__Request`: a single `navigate` block, a `settle[]`
(wait-for-style) list, and a **named-probes** map. The probe verb dropdown is
restricted to the read-only set (`get_url, get_text, get_html, get_dom_tree,
get_a11y_tree, screenshot, get_console_tail, get_network_failures`) — the UI refuses
to add a mutating verb here, matching the server's 422. `diagnostics_on_fail`
checkbox (default on). Result renderer keys `probe_results` by name and shows the
`diagnostics` block (`console_log`, `network_failures`) on failure.

### 3.4 Session tab — stateful open/act/probe/close

Disabled unless `supports_persistent`. A small state machine UI:
`open` → shows `session_id` + `expires_in_ms` countdown → repeated `act` (sequence
shape) / `probe` (inspect shape) panels reusing the Sequence/Inspect builders →
`close`. Page state persists across act/probe; the UI shows the live session id and a
"close" affordance. Auto-expiry surfaced from `expires_in_ms`.

### 3.5 Browser tab — one-shot verbs

Six buttons → `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}`,
each with its tiny request form. `navigate/click/fill/get-content/get-url` return
`Schema__Browser__One_Shot__Response` (JSON viewer); `screenshot` returns **raw
`image/png`** with timings in `X-*-Ms` response headers (viewer reads the headers,
renders the image blob).

### 3.6 Debug tab — console + network

Convenience wrapper: runs a `/inspect` with `navigate` + `get_console_tail` +
`get_network_failures` probes against a target URL, renders the console log lines and
the failed-request list. Aimed at "why is this page broken" triage. (No new endpoint —
just a curated `/inspect` body.)

### 3.7 Service tab — health/info/capabilities/metrics

Read-only dashboards:
- `/health/info` — version/target/code_source card.
- `/health/capabilities` — the full capability table (also used by bootstrap).
- `/health/status` — checks list + timestamp.
- `/metrics` — raw Prometheus text (`GET /metrics`, `text/plain`) in a `<pre>` with a
  "copy" button. Optional tiny parse into a key/value table.
- Links to `/admin/skills/{human,browser,agent}` and `/auth/set-cookie-form`.

---

## 4. Shared console logic (Decision #1 — built on `sg-layout` + `sg-tool-api`)

| Component | Responsibility |
|-----------|----------------|
| `bootstrap()` | the two health calls + capability gating (§1) |
| `authHeaders()` | returns `{[mode]: key}` for the selected auth mode (Decision #7) — single source for every request, incl. the badge |
| `request(method, path, body)` | thin `fetch` wrapper; reads status BEFORE parsing; falls back to `r.text()` on non-JSON (fixes map §7(b)#7) |
| `escHtml(s)` | the existing `:479-481` escaper, now applied to **every** user-echoed string incl. `url` (fixes the XSS) |
| `stepBuilder(verb)` | renders a verb's fields from a verb→fields table |
| `resultRenderer(resp)` | renders sequence/inspect/screenshot responses uniformly |
| `curlExporter(method, path, body)` | "Copy as curl" (Decision #6) |
| `workflowIO` | save/load/import/export — designed in brief 03 |

These are the console's own logic, wired into the `sg-layout` shell and driving (and
driven by) the `sg-tool-api` `window.__tool` bridge (brief 05 rev 3). The
`window.__tool` registration itself comes from the served `sg-tool-api` component
(Q1b resolved → option A), not a hand-rolled inline shim. All of it — and the
component/token assets it loads — resolves through the root_path-aware URL rule
(Decision #11, brief 08) so it works behind `/pw` and at root.

---

## 5. Bug-fix list folded into the rebuild (Phase 1)

All from `00__capability-baseline.md §3` (map §7(b)). Phase 1 ships these even before
the new tabs land:

1. **Health badge reuses the entered key + auth mode** — no more always-degraded.
   (`Routes__Index.py:529`.)
2. **`escHtml()` applied to every echoed string** incl. `${url}` in thumb/lightbox
   labels (`:468`, `:471`, `:559`, `:563`) — closes the injection vector.
3. **`Array.isArray(data.screenshots)` guard** before the batch render (`:445`).
4. **Empty-`lbShots` early-return** in lightbox nav (`:558-571`).
5. **Status-before-parse** in `request()` so a 500 HTML page shows the HTTP status,
   not a JSON parse error (`:327`, `:443`).
6. **"Render: Image / HTML source"** relabel of the `format` toggle (`:208-213`).
7. **`label`/`for` association** on the API-key input (`:186-191`).
8. **In-UI note** that the key is stored in cleartext localStorage (`:288-291`).
9. **Debounce** the URL `oninput` localStorage writes (`:291`, `:364`).

> AppSec sign-off (README checklist) covers items 2 + 8 specifically.

---

## 6. Why build on the shared components (Decision #1 rev-3 justification)

**Rev-1/rev-2 of this pack kept a single self-contained `INDEX_HTML` with no external
deps.** Rev 3 reverses that: per the operator (2026-06-21) the console is built on the
shared sgraph.ai component library — `sg-layout` (panel/routing shell) + `sg-tool-api`
(the `window.__tool` bridge) + sg-tokens — exactly as the admin dashboard does
(`sgraph_ai_service_playwright__api_site/admin/index.html:19` `<sg-layout id="root-layout">`,
`:7` `sg-tokens.css`). The trade is deliberate: we give up the zero-dependency property
to gain the powerful shared-component features (routing, design tokens, the
explorer/console/manifest dev panels) and to align the test page with every other tool.

The 5-target parity argument (`CLAUDE.md` Architecture — one Docker image runs on
laptop / CI / Claude Web / Fargate / Lambda) is **preserved by Decision #11, not by
single-file-ness**: the components are still served same-origin and their URLs are
templated through the same resolved root_path prefix as `window.API_BASE`
(`Routes__Index.py:26`/`:613-614`, `Root_Path__Resolver.py:41-53`), so the same image
works standalone at root and behind the `/pw` reverse proxy. Where a component is
loaded CDN-absolute (`https://dev.tools.sgraph.ai/...`) it is prefix-independent but
requires browser egress to that host — an offline/locked-down deployment must vendor or
prefix-template it instead. Brief 08 specifies the full URL rule and the
CDN-vs-vendored-vs-prefixed trade-off; the `escHtml`/localStorage notes above are
unaffected.
