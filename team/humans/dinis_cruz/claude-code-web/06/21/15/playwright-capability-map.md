---
title: "SG Playwright Service — Code-Derived Capability Map"
author: Dev (claude)
date: 2026-06-21
branch: claude/amazing-pasteur-3srh6x
code_version: v0.2.63
code_basis: "sg_compute_specs/playwright/core/ @ v0.2.63"
purpose: "Precise, code-first map of every HTTP endpoint, request/response schema, and the declarative step language, to drive improvements to the default 'Try it out' test page (INDEX_HTML in Routes__Index.py)."
status: "Phase 1 — read + map. No UI code changed in this phase."
---

# SG Playwright Service — Capability Map

Everything below is traced from code under
`sg_compute_specs/playwright/core/`, not from briefs or the UI. Each claim
carries a `file_path:line` so it is checkable.

The canonical package is `sg_compute_specs/playwright/core/`. The orphan
`sgraph_ai_service_playwright/` package referenced by older docs was deleted in
BV2.11 and is gone. Route wiring is in
`fast_api/Fast_API__Playwright__Service.py:103-114`.

---

## 1. Endpoint surface (what is actually wired)

`Fast_API__Playwright__Service.setup_routes()`
(`fast_api/Fast_API__Playwright__Service.py:103-114`) mounts these route
classes. The `super().setup_routes()` call also lands the agentic `/admin/*`
surface from `Agentic_FastAPI`.

| # | Route class | Wired at | Paths |
|---|-------------|----------|-------|
| 1 | `Routes__Index` | line 105 | `GET /` |
| 2 | `Routes__Health` | line 106 | `GET /health/info`, `/health/status`, `/health/capabilities` |
| 3 | `Routes__Browser` | line 107 | `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}` |
| 4 | `Routes__Sequence` | line 108 | `POST /sequence/execute` |
| 5 | `Routes__Screenshot` | line 109 | `POST /screenshot`, `POST /screenshot/batch` |
| 6 | `Routes__Inspect` | line 110 | `POST /inspect` |
| 7 | `Routes__Session` | line 111 | `POST /session/open`, `/session/{id}/act`, `/session/{id}/probe`, `/session/{id}/close` |
| 8 | `Routes__Metrics` | line 112 | `GET /metrics` |
| 9 | `Routes__Set_Cookie` | line 113 | `GET /auth/set-cookie-form`, `POST /auth/set-auth-cookie` |
| + | `Agentic_Admin_API` | `super()` (line 104) | `GET /admin/{health,info,env,boot-log,error,skills/{name},manifest,capabilities}` |

**Direct endpoint count: 21** (1 index + 3 health + 6 browser + 1 sequence +
2 screenshot + 1 inspect + 4 session + 1 metrics + 2 auth), plus 8 `/admin/*`.

> **DISCREPANCY (see §6):** the reality doc and `CLAUDE.md` both claim "16
> direct endpoints" and that `Routes__Session` was "removed in v0.1.24". The
> code wires **both `Routes__Inspect` and `Routes__Session`**
> (`Fast_API__Playwright__Service.py:110-111`). They exist. The "16" count and
> the "Session removed" line are stale.

### Auth

API-key middleware is enabled by the `Serverless__Fast_API__Config` default
(`Fast_API__Playwright__Service.py:55`). Header is `X-API-Key` for direct
access; the production `/pw` proxy translates `x-sgraph-access-token` →
`X-API-Key` upstream (see `library/skills/use-sg-playwright/SKILL.md`).
**Excluded from auth:** the 8 `/admin/*` paths and the two `/auth/*`
set-cookie paths are appended to `AUTH__EXCLUDED_PATHS`. `GET /` (the test
page) and `GET /metrics` are subject to the middleware in principle, but the
test page's own health badge calls `/health/status` **without** a key
(`Routes__Index.py:529`) — works only when no key is configured.

---

## 2. Per-endpoint request / response schemas

Paths note: osbot-fast-api maps `_` → `-` in inferred paths, so
`get_content` → `/browser/get-content`, etc.

### 2.1 Health — `Routes__Health` (`fast_api/routes/Routes__Health.py:31-43`)

| Method | Path | Req | Resp schema | Resp fields |
|--------|------|-----|-------------|-------------|
| GET | `/health/info` | — | `Schema__Service__Info` | `service_name, service_version, image_version, playwright_version, chromium_version, deployment_target(Enum), capabilities(Schema__Service__Capabilities), code_source` |
| GET | `/health/status` | — | `Schema__Health` | `healthy: bool, checks: List[Schema__Health__Check], timestamp` |
| GET | `/health/capabilities` | — | `Schema__Service__Capabilities` | `max_session_lifetime_ms, supports_persistent, supports_video, available_browsers: List[Enum__Browser__Name], supported_sinks: List[Enum__Artefact__Sink], memory_budget_mb, has_vault_access, has_s3_access, has_network_egress, proxy_configured` |

Sources: `schemas/service/Schema__Service__Info.py:14-22`,
`Schema__Health.py:13-16`, `Schema__Service__Capabilities.py:15-25`.

### 2.2 Browser one-shot — `Routes__Browser` (`fast_api/routes/Routes__Browser.py:51-82`)

Each launches fresh Chromium, runs a tiny sequence, tears down. All return
`Schema__Browser__One_Shot__Response` JSON **except** `/browser/screenshot`,
which returns **raw `image/png` bytes** with timings surfaced as `X-*-Ms`
response headers (`Routes__Browser.py:66-74`).

| Method | Path | Request schema (key fields) |
|--------|------|------------------------------|
| POST | `/browser/navigate` | `Schema__Browser__Navigate__Request` |
| POST | `/browser/click` | `Schema__Browser__Click__Request` |
| POST | `/browser/fill` | `Schema__Browser__Fill__Request` |
| POST | `/browser/get-content` | `Schema__Browser__Get_Content__Request` |
| POST | `/browser/get-url` | `Schema__Browser__Get_Url__Request` |
| POST | `/browser/screenshot` | `Schema__Browser__Screenshot__Request` → `image/png` |

### 2.3 Screenshot — `Routes__Screenshot` (`fast_api/routes/Routes__Screenshot.py:32-38`, mounted at root)

**`POST /screenshot`** — `Schema__Screenshot__Request`
(`schemas/screenshot/Schema__Screenshot__Request.py:13-18`):

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `url` | `Safe_Str__Url__Permissive` | No* | `None` (None = stay on current page, steps mode only) |
| `click` | `Safe_Str__Selector` | No | `None` |
| `javascript` | `Safe_Str__JS__Expression` | No | `None` |
| `full_page` | `bool` | No | `False` |
| `format` | `Enum__Screenshot__Format` (`png`/`html`) | No | `png` |

Response `Schema__Screenshot__Response`
(`Schema__Screenshot__Response.py:13-18`): `url, screenshot_b64 (str|None),
html (Safe_Str__Page__Content|None), duration_ms, trace_id`.

> The `/screenshot` surface runs JS via its own `allow_all` runner (the
> `javascript` field is NOT gated by the deny-all step allowlist — see §5 and
> the consumer skill's gotchas table). This is distinct from the `evaluate`
> step verb in `/sequence`.

**`POST /screenshot/batch`** — `Schema__Screenshot__Batch__Request`
(`Schema__Screenshot__Batch__Request.py:18-21`):

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `items` | `List[Schema__Screenshot__Request]` | — | Mode 1: N independent browser sessions |
| `steps` | `List[Schema__Screenshot__Request]` | — | Mode 2: sequential steps in one session |
| `screenshot_per_step` | `bool` | `False` | Mode 2 only: capture after each step (else only after last) |

Response `Schema__Screenshot__Batch__Response`
(`Schema__Screenshot__Batch__Response.py:13-15`): `screenshots:
List[Schema__Screenshot__Response], duration_ms`.

### 2.4 Sequence — `Routes__Sequence` (`fast_api/routes/Routes__Sequence.py:28-29`)

**`POST /sequence/execute`** — `Schema__Sequence__Request`
(`schemas/sequence/Schema__Sequence__Request.py:24-31`):

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `sequence_id` | `Sequence_Id` | `None` | Auto-generated if omitted |
| `browser_config` | `Schema__Browser__Config` | `None` | Defaults applied when omitted |
| `credentials` | `Schema__Session__Credentials` | `None` | Vault cookies / storage state / headers |
| `capture_config` | `Schema__Capture__Config` | (instantiated) | Artefact capture (screenshot/video/content sinks) |
| `sequence_config` | `Schema__Sequence__Config` | (instantiated) | Sequence-level options |
| `steps` | `List[dict]` | — | Heterogeneous; parsed by dispatcher via `STEP_SCHEMAS` on the `action` discriminator |
| `trace_id` | `Safe_Str__Trace_Id` | `None` | |

Response `Schema__Sequence__Response` (typed return →
OpenAPI advertises the schema): `sequence_id, trace_id, status
(completed/partial/failed), engine, total_duration_ms, steps_total/passed/
failed/skipped, step_results: List[Schema__Step__Result__Base], artefacts,
timings`.

### 2.5 Inspect — `Routes__Inspect` (`fast_api/routes/Routes__Inspect.py:34-36`, mounted at root)

**`POST /inspect`** — snapshot-once, probe-many.
`Schema__Inspect__Request` (`schemas/inspect/Schema__Inspect__Request.py:40-49`):

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `navigate` | `Schema__Step__Navigate` | Yes | — |
| `settle` | `List[dict]` (wait-for-style) | Yes | — (empty list = skip) |
| `probes` | `Dict[str, dict]` (name → read-only probe step) | Yes | — |
| `diagnostics_on_fail` | `bool` | No | `True` |
| `browser_config` | `Schema__Browser__Config` | No | `None` |
| `capture_config` | `Schema__Capture__Config` | No | `None` |
| `credentials` | `Schema__Session__Credentials` | No | `None` |
| `timeout_ms` | `Safe_UInt__Timeout_MS` | No | `None` |
| `trace_id` | `Safe_Str__Trace_Id` | No | `None` |

Allowed probe verbs (read-only): `get_url, get_text, get_html, get_dom_tree,
get_a11y_tree, screenshot, get_console_tail, get_network_failures`. A
mutating verb in `probes` → HTTP 422. Response `Schema__Inspect__Response`:
`inspect_id, trace_id, status, engine, total_duration_ms, navigate_result,
settle_results, probe_results: Dict[str, Schema__Step__Result__Base],
diagnostics, artefacts, timings`.

### 2.6 Session — `Routes__Session` (`fast_api/routes/Routes__Session.py:41-55`, mounted at root)

Opt-in stateful: amortise navigate + decrypt across many probe batches.

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/session/open` | `Schema__Session__Open__Request` | `Schema__Session__Open__Response` (`session_id`, `expires_in_ms`) |
| POST | `/session/{session_id}/act` | `Schema__Session__Act__Request` (sequence-shape) | `Schema__Sequence__Response` |
| POST | `/session/{session_id}/probe` | `Schema__Session__Probe__Request` (inspect-shape) | `Schema__Inspect__Response` |
| POST | `/session/{session_id}/close` | — | `dict` (`{session_id, closed}`) |

### 2.7 Metrics — `Routes__Metrics` (`fast_api/routes/Routes__Metrics.py:27-29`)

`GET /metrics` → raw `text/plain` Prometheus exposition from the module-level
`_REGISTRY` in `metrics/Metrics__Collector.py`. Not JSON.

### 2.8 Auth set-cookie — `Routes__Set_Cookie` (osbot-fast-api)

`GET /auth/set-cookie-form` (HTML UI) + `POST /auth/set-auth-cookie`. Both
bypass the API-key middleware.

### 2.9 Admin — `Agentic_Admin_API` (`agentic_fastapi/Agentic_Admin_API.py`)

8 unauthenticated read-only routes: `GET /admin/{health, info, env, boot-log,
error, skills/{name}, manifest, capabilities}`. `skills/{name}` serves the
`human` / `browser` / `agent` SKILL markdown from `core/skills/`.

---

## 3. The declarative step language (24 verbs)

Action enum: `schemas/enums/Enum__Step__Action.py:8-34` (24 values). Registry:
`dispatcher/step_schema_registry.py:51-76` (`STEP_SCHEMAS`) and `:81-85`
(`STEP_RESULT_SCHEMAS`). Executor handlers:
`service/Step__Executor.py` (per method) + dispatch table in
`service/Step__Executor__Base.py:42-65`.

**Base fields on every step** (`schemas/steps/Schema__Step__Base.py:16-20`):
`action (Enum__Step__Action)`, `id (Step_Id, default None)`,
`continue_on_error (bool, False)`, `timeout_ms (Safe_UInt__Timeout_MS, 30000)`.

| Verb | Schema | Verb-specific fields (type / default) | Executor |
|------|--------|----------------------------------------|----------|
| `navigate` | `Schema__Step__Navigate` | `url`* (Url), `wait_until` (Enum__Wait__State, `load`), `referer` (Url, None) | `execute_navigate` (Step__Executor.py:91) |
| `click` | `Schema__Step__Click` | `selector`* , `button` (Enum__Mouse__Button, `left`), `click_count` (UInt, 1), `delay_ms` (UInt ms, 0), `force` (bool, False) | `execute_click` (:99) |
| `fill` | `Schema__Step__Fill` | `selector`*, `value`*, `clear_first` (bool, True) | `execute_fill` (:112) |
| `press` | `Schema__Step__Press` | `selector` (None), `key`* (Enum__Keyboard__Key) | `execute_press` (:268) |
| `select` | `Schema__Step__Select` | `selector`*, `values`* (List[Text]) | `execute_select` (:279) |
| `hover` | `Schema__Step__Hover` | `selector`* | `execute_hover` (:288) |
| `scroll` | `Schema__Step__Scroll` | `selector` (None), `x` (Int, 0), `y` (Int, 0) | `execute_scroll` (:296) |
| `wait_for` | `Schema__Step__Wait_For` | `selector`, `text`, `url_pattern`, `state` (Enum__Wait__State), `visible` (True), `selector_gone` (False), `function` (JS expr), `network_idle_ms` — all optional | `execute_wait_for` (:234) |
| `wait` | `Schema__Step__Wait` | `duration_ms` (Timeout_MS, 0) | `execute_wait` (:260) |
| `screenshot` | `Schema__Step__Screenshot` | `full_page` (False), `selector`, `save_as`, `viewport` (Schema__Viewport), `frame_selector` | `execute_screenshot` (:123) |
| `video_start` | `Schema__Step__Video__Start` | `codec` (Enum__Video__Codec, `webm`) | context-level (capture_config.video) |
| `video_stop` | `Schema__Step__Video__Stop` | `save_as` | context-level |
| `evaluate` | `Schema__Step__Evaluate` | `expression`* (JS expr), `return_type` (Enum__Evaluate__Return_Type, `json`) | `execute_evaluate` (:207) — **allowlist-gated** |
| `dispatch_event` | `Schema__Step__Dispatch_Event` | `selector`*, `event_type`* (Key), `event_init` (Dict, None) | `execute_dispatch_event` (:316) |
| `set_viewport` | `Schema__Step__Set_Viewport` | `viewport`* (Schema__Viewport) | `execute_set_viewport` (:307) |
| `get_content` | `Schema__Step__Get_Content` | `selector`, `content_format` (Enum__Content__Format, `html`), `inline_in_response` (True) | `execute_get_content` (:145) |
| `get_url` | `Schema__Step__Get_Url` | — | `execute_get_url` (:185) |
| `get_text` | `Schema__Step__Get_Text` | `selector`, `inline_in_response` (True) | `execute_get_text` (:329) |
| `get_html` | `Schema__Step__Get_Html` | `selector`, `inline_in_response` (True) | `execute_get_html` (:350) |
| `get_dom_tree` | `Schema__Step__Get_Dom_Tree` | `root_selector`, `max_depth` (UInt, 8), `include_invisible` (False) | `execute_get_dom_tree` (:373) |
| `get_a11y_tree` | `Schema__Step__Get_A11y_Tree` | `root_selector`, `interesting_only` (True) | `execute_get_a11y_tree` (:390) |
| `get_pdf` | `Schema__Step__Get_Pdf` | `format` (Str, `A4`), `landscape` (False), `print_background` (True) | `execute_get_pdf` (:418) |
| `get_console_tail` | `Schema__Step__Get_Console_Tail` | `lines` (UInt, 100) | `execute_get_console_tail` (:431) |
| `get_network_failures` | `Schema__Step__Get_Network_Failures` | — | `execute_get_network_failures` (:446) |

`*` = required.

### Step result (`schemas/results/Schema__Step__Result__Base.py:32-58`)

Every result carries every "lifted" field (most null). Key ones by verb:
`content/content_format/content_type` (get_content), `url` (get_url),
`return_value/return_type` (evaluate), `text` (get_text), `html` (get_html),
`dom_tree` (get_dom_tree), `accessibility_tree` (get_a11y_tree), `console_log`
(get_console_tail), `network_failures` (get_network_failures), `artefacts`
(screenshot/get_pdf). Plus `step_id, step_index, action, status
(Enum__Step__Status: pending/running/passed/failed/skipped), duration_ms,
error_message, error_type (Enum__Step__Error__Type)`.

### Enums referenced

- `Enum__Wait__State`: `load`, `domcontentloaded`, `networkidle`
- `Enum__Mouse__Button`: `left`, `right`, `middle`
- `Enum__Keyboard__Key`: `Enter, Tab, Escape, Backspace, Delete, ArrowUp/Down/Left/Right, Control+a/c/v`
- `Enum__Video__Codec`: `webm`, `mp4`
- `Enum__Evaluate__Return_Type`: `json`, `string`, `number`, `boolean`
- `Enum__Content__Format`: `html`, `text`
- `Enum__Screenshot__Format` (screenshot endpoint): `png`, `html`

---

## 4. Capture / artefact options

`Schema__Capture__Config` drives artefact emission. Artefacts referenced via
`Schema__Artefact__Ref` (`schemas/artefact/Schema__Artefact__Ref.py:23-34`):
`artefact_type (Enum__Artefact__Type: SCREENSHOT/PDF/PAGE_CONTENT/VIDEO/
CONSOLE_LOG/NETWORK_LOG)`, `sink (Enum__Artefact__Sink: VAULT/S3/LOCAL_FILE/
INLINE)`, `size_bytes`, `content_hash`, `width/height` (screenshots),
`vault_ref/s3_ref/local_ref`, `inline_b64` (base64, 20 MB cap), `captured_at`.

Without a `capture_config` screenshot sink, a `screenshot` step "passes" but
emits no artefact — set `capture_config.screenshot.{enabled:true, sink:inline}`
to get `inline_b64` back (see consumer skill gotchas).

---

## 5. Security gate — JS allowlist

`evaluate` step verb is allowlist-gated by
`service/JS__Expression__Allowlist.py` — **deny-all by default**. A
non-allowlisted `evaluate` (or `wait_for: function`) does NOT 422; the step
fails with `error_message` containing "allowlist" and the sequence status goes
`failed` / `partial` (Sequence__Runner keeps one bad step from aborting). The
`/screenshot` endpoint's `javascript` field is a SEPARATE path with its own
`allow_all` runner, so simple "run JS before capture" works there even though
`evaluate` is gated.

---

## 6. Discrepancies found (code vs docs vs UI)

| # | Source claims | Code reality | Severity |
|---|---------------|--------------|----------|
| D1 | `CLAUDE.md` + reality `playwright-service/index.md:16,102`: "16 direct endpoints", "Routes__Session removed in v0.1.24" | `Fast_API__Playwright__Service.py:110-111` wires **`Routes__Inspect` AND `Routes__Session`**. Real direct count is **21** (+8 admin). `/inspect` and `/session/*` are live. | **High** — reality doc stale; flag to Librarian. |
| D2 | `capabilities.json:3` declares `"version": "v0.1.29"` | Repo `version` is **v0.2.63**. The root stub is frozen at v0.1.29; `/admin/capabilities` serves this stale version. | Medium — version drift in self-declared capabilities. |
| D3 | `capabilities.json:9` `declared_narrowing: []`; `core/skills/skill__agent.md:18-20` says axioms are pinned to v0.1.29 list, "lockdown layers deferred" | Matches the stub, but the stub itself is stale vs code. | Low — consistent with the stale stub, not with the running service version. |
| D4 | `core/skills/skill__agent.md:2` self-labels "FIRST-PASS PLACEHOLDER (v0.1.29). TODO — expand before v0.2." | We are at v0.2.63; the agent SKILL never got expanded and predates `/inspect`, `/session/*`, and the 24-verb step language entirely. | Medium — core skill under-documents the surface. |
| D5 | UI exposes only `/screenshot` and `/screenshot/batch` | Service supports 21 direct endpoints incl. the full `/sequence` 24-verb language, `/inspect`, `/session/*`. The test page is a thin slice of the surface. | High — drives the UI-improvement backlog (§7). |
| D6 | `health/capabilities` schema (`Schema__Service__Capabilities`) advertises `supports_video, available_browsers, supported_sinks, has_vault_access`, etc. | These are real, populated by `Capability__Detector` — but the UI never fetches `/health/capabilities`, so users can't see what the deployment can do. | Medium — UI gap. |

> The **consumer skill** `library/skills/use-sg-playwright/SKILL.md` is, by
> contrast, accurate and current: it documents all 24 verbs, `/inspect`,
> `/session/*`, the auth-header split, and worked recipes. It contradicts the
> reality doc (which is the stale one).

---

## 7. UI: exposed vs not-exposed, and the improvement backlog

Current test page: `INDEX_HTML` in `fast_api/routes/Routes__Index.py`
(~581 lines of HTML/CSS/JS, lines 20-601). API base injected at line 26
(`window.API_BASE="__API_BASE__"`, replaced per-request at :614, default `/pw`).
`post()` helper at :484-487 sends `X-API-Key` when a key is present. Health
badge polls `/health/status` (:529).

### Tabs today

- **Single** (lines 200-238) → `POST /screenshot`. Fields: `url`,
  `format` (png/html), `javascript`, `click`, `full_page`.
- **Batch** (lines 242-269) → `POST /screenshot/batch`. Modes: "Independent
  sessions" (`items`) vs "Sequential steps" (`steps` + `screenshot_per_step`).
  Per-card: `url`, `format`, `javascript`, `click`, `full_page`.

### (a) Capabilities the SERVICE supports but the UI does NOT expose

1. **`POST /sequence/execute` — the entire 24-verb step language.** The
   headline feature. No way to build/run a multi-step sequence in the UI. A
   JSON sequence editor + "run" + step-results renderer would expose
   navigate/click/fill/press/select/hover/scroll/wait/wait_for/get_*/evaluate/
   get_pdf/etc.
2. **`POST /inspect` — snapshot-once, probe-many.** The most efficient read
   pattern. UI exposes nothing.
3. **`POST /session/*` — stateful open/act/probe/close.** Not exposed.
4. **`POST /browser/*` one-shot verbs** (navigate, click, fill, get-content,
   get-url, get-url, raw screenshot). Not exposed — the UI only uses the
   higher-level `/screenshot`.
5. **PDF rendering** (`get_pdf` step / artefact). Not exposed.
6. **DOM tree / a11y tree / text / html extraction** (`get_dom_tree`,
   `get_a11y_tree`, `get_text`, `get_html`). Not exposed.
7. **Console tail + network failures** (`get_console_tail`,
   `get_network_failures`) — great for a "debug" panel. Not exposed.
8. **`GET /health/capabilities`** — show the user what THIS deployment can do
   (video? sinks? vault? browsers? memory budget?). Not fetched.
9. **`GET /health/info`** — service/playwright/chromium versions, deployment
   target, code_source. Not shown (only a binary health dot).
10. **`GET /metrics`** — a "metrics" / "stats" view. Not exposed.
11. **`evaluate` return types** and the allowlist behaviour — no UI affordance
    or explanation.
12. **`full_page`, `viewport`, `selector`-scoped screenshot, `frame_selector`**
    on the screenshot step — UI only has `full_page`.
13. **Capture sinks** (inline/vault/s3/local) — no UI control; users can't pick
    where artefacts go.
14. **`/auth/set-cookie-form`** — a link/embed for the cookie helper. Not
    surfaced.
15. **OpenAPI `/docs` deep-links per endpoint** — the header links to `/docs`
    generally but nothing maps a UI action to its schema.

### (b) UX / correctness issues in the current HTML/JS

1. **Health badge calls `/health/status` with no `X-API-Key`**
   (`Routes__Index.py:529`). On a deployment WITH an API key configured, the
   badge will 401 and always read "degraded" even when healthy. Should reuse
   the entered key (or be marked best-effort).
2. **Unescaped `${url}` interpolation** into HTML attributes (lightbox label
   ~:468). A URL containing `"` breaks the markup / is an injection vector.
   HTML-escape all user-echoed strings.
3. **No `Array.isArray(data.screenshots)` guard** on the batch response; a
   malformed/empty response throws in the render path.
4. **No null/empty guard in lightbox navigation** (~:570-571) — empty
   `lbShots` throws on property access.
5. **API key stored in `localStorage` in cleartext** (:288-291). Acceptable
   for a dev tool but should at least be flagged in-UI; combined with issue #2
   the XSS surface matters.
6. **`oninput` on every URL field with no debounce** (~:364) — minor, but
   fires constantly.
7. **Generic `catch`/`r.json()` masking** — if the server returns non-JSON
   (e.g. a 500 HTML page), the parse error hides the real HTTP status.
8. **`format=html` "screenshot" is mislabeled** — returns page HTML, not an
   image. The toggle naming conflates "render mode" with "screenshot format";
   confusing for first-time users.
9. **No label/`for` association** on the API-key input (a11y).

### (c) Nice-to-haves

1. **"Copy as curl"** for every request the UI builds — pairs with the
   consumer skill's curl recipes.
2. **Pre-filled example gallery** (the consumer skill's 5 recipes as
   one-click "load example" buttons).
3. **Response viewer with timings** (`X-*-Ms` headers from `/browser/screenshot`;
   `timings` block from `/sequence`).
4. **Auth-mode toggle** (direct `X-API-Key` vs `/pw` `x-sgraph-access-token`)
   matching the two real deployment paths in the consumer skill.
5. **Trace-id surfacing + click-to-copy** (already returned in responses).
6. **Dark/light toggle, keyboard shortcuts, request history.**
7. **Inline link to the relevant `/admin/skills/{human|browser|agent}` doc.**

---

## 8. Where things are

| Thing | Path |
|-------|------|
| Route wiring | `sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py:103-114` |
| Test page (target of next phase) | `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` (`INDEX_HTML`, lines 20-601) |
| Step action enum | `sg_compute_specs/playwright/core/schemas/enums/Enum__Step__Action.py` |
| Step registry | `sg_compute_specs/playwright/core/dispatcher/step_schema_registry.py` |
| Step schemas | `sg_compute_specs/playwright/core/schemas/steps/` |
| Step results | `sg_compute_specs/playwright/core/schemas/results/` |
| Executor | `sg_compute_specs/playwright/core/service/Step__Executor.py` (+ `Step__Executor__Base.py`) |
| JS allowlist | `sg_compute_specs/playwright/core/service/JS__Expression__Allowlist.py` |
| Capabilities stub | `capabilities.json` (repo root, v0.1.29 — stale) |
| Consumer skill (accurate) | `library/skills/use-sg-playwright/SKILL.md` |
| Core skills | `sg_compute_specs/playwright/core/skills/skill__{human,browser,agent}.md` |
| Reality doc (stale on count/session) | `team/roles/librarian/reality/playwright-service/index.md` |
