---
name: sg-playwright-capabilities
description: Code-derived reference of the FULL sg-playwright capability surface — every HTTP endpoint, its request/response schema and field defaults, and every one of the 25 declarative step verbs with their parameters and enums. Trigger when you need the EXACT shape of a request or response, the complete list of endpoints/step actions, a field's default value or type, which probe verbs /inspect allows, or you are building/extending a client or the default "Try it out" test page and need a checkable field-by-field map. This is the lookup table; for task-oriented "how do I drive a browser over HTTP" recipes and the auth-header split use the companion skill `use-sg-playwright`. Source of truth is the code under `sg_compute_specs/playwright/core/` at v0.2.63 — not capabilities.json (frozen at v0.1.29) nor the reality doc (stale on endpoint count). file_path:line references included so every claim is verifiable.
---

# sg-playwright-capabilities

Reference map of everything the service can do, traced from
`sg_compute_specs/playwright/core/`. Pair with `use-sg-playwright` for recipes
and auth. When code and `capabilities.json` / the reality doc disagree, **the
code wins** — both of those are stale (see Drift, bottom).

## Endpoint index (21 direct + 8 admin)

Wired in `fast_api/Fast_API__Playwright__Service.py:103-114`.

| Method | Path | Request schema | Response | Notes |
|---|---|---|---|---|
| GET | `/` | — | HTML | "Try it out" test page (`Routes__Index`) |
| GET | `/health/info` | — | `Schema__Service__Info` | versions, deployment target, code_source, capabilities |
| GET | `/health/status` | — | `Schema__Health` | `healthy:bool`, checks[], timestamp |
| GET | `/health/capabilities` | — | `Schema__Service__Capabilities` | what THIS deployment can do |
| POST | `/browser/navigate` | `Schema__Browser__Navigate__Request` | `…One_Shot__Response` (JSON) | one-shot |
| POST | `/browser/click` | `Schema__Browser__Click__Request` | `…One_Shot__Response` | one-shot |
| POST | `/browser/fill` | `Schema__Browser__Fill__Request` | `…One_Shot__Response` | one-shot |
| POST | `/browser/get-content` | `Schema__Browser__Get_Content__Request` | `…One_Shot__Response` | `_`→`-` in path |
| POST | `/browser/get-url` | `Schema__Browser__Get_Url__Request` | `…One_Shot__Response` | |
| POST | `/browser/screenshot` | `Schema__Browser__Screenshot__Request` | **raw `image/png`** | timings via `X-*-Ms` headers |
| POST | `/sequence/execute` | `Schema__Sequence__Request` | `Schema__Sequence__Response` | the 25-verb language |
| POST | `/screenshot` | `Schema__Screenshot__Request` | `Schema__Screenshot__Response` | url→png/html, JS via own allow_all runner |
| POST | `/screenshot/batch` | `Schema__Screenshot__Batch__Request` | `…Batch__Response` | items[] OR steps[]+screenshot_per_step |
| POST | `/inspect` | `Schema__Inspect__Request` | `Schema__Inspect__Response` | snapshot-once probe-many (read-only probes) |
| POST | `/session/open` | `Schema__Session__Open__Request` | `…Open__Response` | stateful; `expires_in_ms` |
| POST | `/session/{id}/act` | `Schema__Session__Act__Request` | `Schema__Sequence__Response` | sequence-shape body |
| POST | `/session/{id}/probe` | `Schema__Session__Probe__Request` | `Schema__Inspect__Response` | inspect-shape body, no navigate |
| POST | `/session/{id}/close` | — | `dict` | `{session_id, closed}` |
| GET | `/metrics` | — | `text/plain` | Prometheus exposition |
| GET | `/auth/set-cookie-form` | — | HTML | bypasses API-key middleware |
| POST | `/auth/set-auth-cookie` | form | — | bypasses API-key middleware |
| GET | `/admin/{health,info,env,boot-log,error,skills/{name},manifest,capabilities}` | — | JSON/markdown | unauthenticated read-only |

**Auth:** `X-API-Key` direct; `x-sgraph-access-token` via the `/pw` proxy
(proxy rewrites it to `X-API-Key` upstream). `/admin/*` and `/auth/*` are
excluded from the middleware.

## Key request schemas

### `Schema__Screenshot__Request`
`url` (Url, None=stay on page in steps mode) · `click` (Selector) ·
`javascript` (JS expr, **not** allowlist-gated here) · `full_page` (bool,
False) · `format` (`png`|`html`, default `png`).
`/screenshot/batch`: `items: [Screenshot__Request]` (independent sessions) OR
`steps: [Screenshot__Request]` + `screenshot_per_step` (bool, False).

### `Schema__Sequence__Request`
`sequence_id` (auto) · `browser_config` · `credentials` (vault cookies/storage/
headers) · `capture_config` (artefact sinks) · `sequence_config` · `steps:
List[dict]` (parsed by `action` discriminator) · `trace_id`.

### `Schema__Inspect__Request`
`navigate` (Step__Navigate, req) · `settle: List[dict]` (wait-for-style, req,
may be []) · `probes: Dict[str,dict]` (req, READ-ONLY verbs) ·
`diagnostics_on_fail` (bool, True) · `browser_config` · `capture_config` ·
`credentials` · `timeout_ms` · `trace_id`.
Allowed probe verbs: `get_url, get_text, get_html, get_dom_tree, get_a11y_tree,
screenshot, get_console_tail, get_network_failures`. A mutating verb → HTTP 422.

## Key response schemas

- `Schema__Service__Info`: `service_name, service_version, image_version,
  playwright_version, chromium_version, deployment_target, capabilities, code_source`.
- `Schema__Service__Capabilities`: `max_session_lifetime_ms, supports_persistent,
  supports_video, available_browsers[], supported_sinks[], memory_budget_mb,
  has_vault_access, has_s3_access, has_network_egress, proxy_configured`.
- `Schema__Health`: `healthy:bool, checks:[Schema__Health__Check], timestamp`.
- `Schema__Screenshot__Response`: `url, screenshot_b64(str|None), html(|None),
  duration_ms, trace_id`.
- `Schema__Sequence__Response`: `sequence_id, trace_id, status
  (completed|partial|failed), engine, total_duration_ms, steps_total/passed/
  failed/skipped, step_results:[Schema__Step__Result__Base], artefacts, timings`.

## The 25 step verbs

Base fields (every step): `action`, `id` (None), `continue_on_error` (False),
`timeout_ms` (30000). `*` = required.

| Verb | Verb-specific fields (type / default) |
|---|---|
| `navigate` | `url`* · `wait_until` (load) · `referer` |
| `click` | `selector`* · `button` (left) · `click_count` (1) · `delay_ms` (0) · `force` (False) |
| `fill` | `selector`* · `value`* · `clear_first` (True) |
| `press` | `selector` · `key`* |
| `select` | `selector`* · `values`* (list) |
| `hover` | `selector`* |
| `scroll` | `selector` · `x` (0) · `y` (0) |
| `wait` | `duration_ms` (0) |
| `wait_for` | `selector` · `text` · `url_pattern` · `state` · `visible` (True) · `selector_gone` (False) · `function` (allowlist) · `network_idle_ms` |
| `screenshot` | `full_page` (False) · `selector` · `save_as` · `viewport` · `frame_selector` |
| `set_viewport` | `viewport`* (width 1280 / height 800) |
| `evaluate` | `expression`* · `return_type` (json) — **allowlist-gated, deny-all default** |
| `dispatch_event` | `selector`* · `event_type`* · `event_init` |
| `video_start` | `codec` (webm) — context-level via capture_config |
| `video_stop` | `save_as` — context-level |
| `get_content` | `selector` · `content_format` (html) · `inline_in_response` (True) |
| `get_url` | — |
| `get_text` | `selector` · `inline_in_response` (True) |
| `get_html` | `selector` · `inline_in_response` (True) |
| `get_dom_tree` | `root_selector` · `max_depth` (8) · `include_invisible` (False) |
| `get_a11y_tree` | `root_selector` · `interesting_only` (True) |
| `get_pdf` | `format` (A4) · `landscape` (False) · `print_background` (True) |
| `get_console_tail` | `lines` (100) |
| `get_network_failures` | — |
| `set_cookie` | `name`* · `value`* · `url` OR `domain` (+`path`, default `/`) · `secure` (False) · `http_only` (False) · `same_site` (Strict/Lax/None) · `expires` — **stateless: cookie lives only in this request's fresh browser context** |

### Result fields by verb (`Schema__Step__Result__Base`)
`get_url`→`url` · `get_text`→`text` · `get_html`→`html` ·
`get_content`→`content/content_format/content_type` · `get_dom_tree`→`dom_tree`
· `get_a11y_tree`→`accessibility_tree` · `evaluate`→`return_value/return_type`
· `get_console_tail`→`console_log` · `get_network_failures`→`network_failures`
· `screenshot`/`get_pdf`→`artefacts[]`. Plus `step_id, step_index, action,
status (pending|running|passed|failed|skipped), duration_ms, error_message,
error_type`.

## Enums

`wait_until/state`: load · domcontentloaded · networkidle ·
`button`: left · right · middle ·
`key`: Enter · Tab · Escape · Backspace · Delete · Arrow{Up,Down,Left,Right} · Control+{a,c,v} ·
`codec`: webm · mp4 ·
`evaluate return_type`: json · string · number · boolean ·
`content_format`: html · text ·
`screenshot format` (endpoint): png · html ·
`artefact sink`: VAULT · S3 · LOCAL_FILE · INLINE ·
`artefact type`: SCREENSHOT · PDF · PAGE_CONTENT · VIDEO · CONSOLE_LOG · NETWORK_LOG.

## Artefacts & capture
`Schema__Artefact__Ref`: `artefact_type, sink, size_bytes, content_hash,
width/height (screenshots), vault_ref/s3_ref/local_ref, inline_b64 (base64,
20 MB cap), captured_at`. No `capture_config` sink ⇒ a `screenshot` step
passes but emits no artefact; set `capture_config.screenshot.{enabled:true,
sink:inline}` to receive `inline_b64`.

## Security
`evaluate` and `wait_for: function` go through `JS__Expression__Allowlist`
(`service/JS__Expression__Allowlist.py`), deny-all by default. A blocked JS
does NOT 422 — the step fails with "allowlist" in `error_message` and the
sequence goes `partial`/`failed`. The `/screenshot` `javascript` field is a
SEPARATE allow_all path.

## Source map
- Wiring `fast_api/Fast_API__Playwright__Service.py:103-114`
- Step enum `schemas/enums/Enum__Step__Action.py`
- Step registry `dispatcher/step_schema_registry.py`
- Step schemas `schemas/steps/` · results `schemas/results/`
- Executor `service/Step__Executor.py` (+ `Step__Executor__Base.py`)
- Allowlist `service/JS__Expression__Allowlist.py`

## Drift (do not trust these over the code)
- `capabilities.json` (repo root) pins `version: v0.1.29`; real version is
  `v0.2.63`. `/admin/capabilities` serves the stale value.
- Reality doc `team/roles/librarian/reality/playwright-service/index.md` says
  "16 direct endpoints" and "Routes__Session removed in v0.1.24" — both stale;
  `Routes__Inspect` and `Routes__Session` ARE wired.
- Core `skill__agent.md` self-labels "FIRST-PASS PLACEHOLDER (v0.1.29)" and
  predates the 25-verb language, `/inspect`, and `/session/*`.
