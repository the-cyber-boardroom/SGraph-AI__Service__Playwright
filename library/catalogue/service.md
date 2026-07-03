---
title: "Catalogue — Playwright Service"
file: service.md
shard: service
as_of: v0.2.28
last_refreshed: 2026-05-17 (PM sync)
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Playwright Service

The browser-automation FastAPI service. **The legacy `sgraph_ai_service_playwright/` top-level package was deleted in BV2.11 (2026-05-05).** The service now lives under `sg_compute_specs/playwright/` and is shipped as a Docker Hub image (`diniscruz/sg-playwright:{version}`); the AWS Lambda packaging carried by the old layout has been retired.

- **Canonical code root:** `sg_compute_specs/playwright/`
- **Service entry class:** `sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service`
- **Lambda handler module (also used for plain Docker `CMD`):** `sg_compute_specs.playwright.core.fast_api.lambda_handler`
- **Manifest:** `sg_compute_specs/playwright/manifest.py` — `spec_id='playwright'`, `Enum__Spec__Stability.STABLE`, capabilities = `BROWSER_AUTOMATION | VAULT_WRITES | SIDECAR_ATTACH`.
- **Detailed spec contracts (CITE — do not duplicate):** [`library/docs/specs/v0.20.55__routes-catalogue-v2.md`](../docs/specs/v0.20.55__routes-catalogue-v2.md), [`library/docs/specs/v0.20.55__schema-catalogue-v2.md`](../docs/specs/v0.20.55__schema-catalogue-v2.md).

> **D1/D5 corrected (2026-06-23).** Earlier text claimed "no `Routes__Session` is wired today (sessions were removed in v0.1.24)". That is **stale** — `Fast_API__Playwright__Service.setup_routes()` (`:103-113`) wires both `Routes__Inspect` (`:110`, `POST /inspect`) and `Routes__Session` (`:111`, four `/session/*` routes). Itemised below the **code-verified total is 21 direct endpoints + 8 admin**. CLAUDE.md's "16 direct endpoints" / "Routes__Session removed in v0.1.24" line is therefore also stale — flagged for the human (do not rely on it).

---

## API Surface — Endpoints by Route Class

All route classes are mounted by `Fast_API__Playwright__Service.setup_routes()`. The admin surface is inherited from `Agentic_FastAPI` / `Agentic_Admin_API`.

### Routes__Health — 3 endpoints (`sg_compute_specs/playwright/core/fast_api/routes/Routes__Health.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/health/info` | `Routes__Health.info` | App info |
| GET | `/health/status` | `Routes__Health.status` | Service status |
| GET | `/health/capabilities` | `Routes__Health.capabilities` | Declared capabilities |

### Routes__Browser — 6 endpoints (`Routes__Browser.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| POST | `/browser/navigate` | `Routes__Browser.navigate` | `Schema__Browser__One_Shot__Response` (JSON) |
| POST | `/browser/click` | `Routes__Browser.click` | JSON |
| POST | `/browser/fill` | `Routes__Browser.fill` | JSON |
| POST | `/browser/get-content` | `Routes__Browser.get_content` | JSON (HTML populated) |
| POST | `/browser/get-url` | `Routes__Browser.get_url` | JSON |
| POST | `/browser/screenshot` | `Routes__Browser.screenshot` | `image/png` raw bytes; timings via `X-*-Ms` headers |

### Routes__Screenshot — 2 endpoints (`Routes__Screenshot.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| POST | `/screenshot` | `Routes__Screenshot.screenshot` | `Schema__Screenshot__Response` (JSON, base64 PNG) |
| POST | `/screenshot/batch` | `Routes__Screenshot.batch` | `Schema__Screenshot__Batch__Response` (JSON) |

### Routes__Sequence — 1 endpoint (`Routes__Sequence.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| POST | `/sequence/execute` | `Routes__Sequence.execute` | `Schema__Sequence__Response` (Layer-3 multi-step) |

### Routes__Inspect — 1 endpoint (`Routes__Inspect.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| POST | `/inspect` | `Routes__Inspect.inspect` | `Schema__Inspect__Response` (Φ5 snapshot-once-probe-many) |

### Routes__Session — 4 endpoints (`Routes__Session.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| POST | `/session/open` | `Routes__Session.open` | `session_id` + `expires_in_ms` |
| POST | `/session/{session_id}/act` | `Routes__Session.act` | `Schema__Sequence__Response` |
| POST | `/session/{session_id}/probe` | `Routes__Session.probe` | `Schema__Inspect__Response` |
| POST | `/session/{session_id}/close` | `Routes__Session.close` | `{closed: true}` |

### Routes__Metrics — 1 endpoint (`Routes__Metrics.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/metrics` | `Routes__Metrics.metrics` | Prometheus text exposition |

### Routes__Index — 1 endpoint (`Routes__Index.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/` | `Routes__Index.index` | Capability-driven agent-native **console** (HTML) — v0.2.64 rebuild (was the two-tab "Try it out" toy); 8 tabs, 25-verb sequence builder, S1–S6 (self-contained `/test-pages/*`; S6 = set_cookie → reload → screenshot) + W1–W9 gallery (each W badged "needs egress" — external URLs), in-app docs, in-page `window.__tool`, root_path-aware for `/pw`. Iteration 2: light center/right/bottom work panes (dark header + rail), `<sg-layout>` wrapping (CDN-optional, localStorage `sg-playwright:console:layout:v1`, CSS-grid fallback), framed screenshot viewer (Download + Open-in-new-tab), insecure-origin-safe `copyText`, bottom `window.__tool` REPL |

### Routes__Test_Pages — 1 route, 6 names (`Routes__Test_Pages.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/test-pages/{name}` | `Routes__Test_Pages.page` | Deterministic HTML fixture (`name` ∈ simple/form/dynamic/links/slow/cookies) for the console S-series; 404 with HTML-escaped reflected name for unknown. Six concrete paths appended to `AUTH__EXCLUDED_PATHS` in `setup()` (keyless for the server-side browser). `cookies` renders `document.cookie` into `#cookie-list` / `#has-cookies` / `#no-cookies` (set_cookie / S6 target; the demo cookie must not be HttpOnly) |

### Routes__Set_Cookie — 2 endpoints (from `osbot_fast_api`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/auth/set-cookie-form` | osbot-fast-api | HTML form |
| POST | `/auth/set-auth-cookie` | osbot-fast-api | Sets API-key cookie |

### Agentic_Admin_API — 8 endpoints (`core/agentic_fastapi/Agentic_Admin_API.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/admin/health` | `health` | `Schema__Agentic__Health` |
| GET | `/admin/info` | `info` | `Schema__Agentic__Info` |
| GET | `/admin/env` | `env` | `Schema__Agentic__Env` (AGENTIC_* only) |
| GET | `/admin/boot-log` | `boot_log` | Ring-buffer (max 200 lines) |
| GET | `/admin/error` | `error` | Last-error holder |
| GET | `/admin/skills/{name}` | `skills__name` | Markdown SKILL content |
| GET | `/admin/manifest` | `manifest` | Discovery manifest (OpenAPI + SKILL URLs) |
| GET | `/admin/capabilities` | `capabilities` | `capabilities.json` contents |

**Code-verified total: 22 direct + 8 admin = 30 endpoints** (3 health + 6 browser + 2 screenshot + 1 sequence + 1 inspect + 4 session + 1 metrics + 1 index + 1 test-pages + 2 set-cookie + 8 admin). Re-verified 2026-06-23 against `Fast_API__Playwright__Service.py:103-115` (iteration 2 added `Routes__Test_Pages` at `:115`). CLAUDE.md's "16 direct endpoints" / "Routes__Session removed in v0.1.24" is stale — flagged for the human.

---

## Service Classes (`sg_compute_specs/playwright/core/service/`)

All 11 service classes verified present 2026-05-17:

| Class | Responsibility |
|-------|---------------|
| `Playwright__Service` | Top-level orchestrator. Exposes `browser_navigate`, `browser_click`, `browser_fill`, `browser_get_content`, `browser_get_url`, `browser_screenshot`, `screenshot_simple`, `screenshot_batch`, `execute_sequence`, `run_one_shot`, `setup`. |
| `Browser__Launcher` | Carve-out from the `Step__Executor` rule: handles Chromium process lifecycle. `build_proxy_dict()` reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL`. |
| `Step__Executor` | **ONLY class that calls `page.*`** Playwright methods. |
| `Sequence__Runner` | Runs a multi-step sequence; calls `Step__Executor`. |
| `Sequence__Dispatcher` | Routes step types to `Step__Executor`. |
| `Artefact__Writer` | **ONLY class that writes to sinks** (screenshots, HTML, video). |
| `Request__Validator` | **ALL cross-schema validation** lives here. |
| `Request__Watchdog` | Hard-timeout watchdog; `os._exit(2)` when a request exceeds the cap. Disabled via `ENV_VAR__WATCHDOG_DISABLED='1'` for tests. |
| `Capability__Detector` | Detects browser capabilities; primed on `setup()`. |
| `Credentials__Loader` | Loads vault credentials. Also the ONLY class that calls `context.add_cookies` — the `set_cookie` step verb lands here via `add_cookie(context, step)` (stateless: per-request context only). |
| `JS__Expression__Allowlist` | Allowlist gate for `evaluate` step actions — defaults to deny-all. |

> Historical note: `Proxy__Auth__Binder` was removed in v0.1.33; the `agent_mitmproxy` sidecar (also since deleted in BV2.12, 2026-05-05) handled upstream proxy auth.

---

## Step Action Registry (`core/dispatcher/step_schema_registry.py`)

25 step actions live today in `STEP_SCHEMAS : Dict__Step__Schemas__By_Action` (re-verified 2026-07-03 against `step_schema_registry.py:52-78` and `Enum__Step__Action`; the set_cookie slice took it from 24 to 25):

| Enum value | Request schema | Result schema |
|-----------|---------------|---------------|
| `NAVIGATE` | `Schema__Step__Navigate` | `Schema__Step__Result__Base` |
| `CLICK` | `Schema__Step__Click` | `Schema__Step__Result__Base` |
| `FILL` | `Schema__Step__Fill` | `Schema__Step__Result__Base` |
| `PRESS` | `Schema__Step__Press` | `Schema__Step__Result__Base` |
| `SELECT` | `Schema__Step__Select` | `Schema__Step__Result__Base` |
| `HOVER` | `Schema__Step__Hover` | `Schema__Step__Result__Base` |
| `SCROLL` | `Schema__Step__Scroll` | `Schema__Step__Result__Base` |
| `WAIT_FOR` | `Schema__Step__Wait_For` | `Schema__Step__Result__Base` |
| `SCREENSHOT` | `Schema__Step__Screenshot` | `Schema__Step__Result__Base` |
| `VIDEO_START` | `Schema__Step__Video__Start` | `Schema__Step__Result__Base` |
| `VIDEO_STOP` | `Schema__Step__Video__Stop` | `Schema__Step__Result__Base` |
| `EVALUATE` | `Schema__Step__Evaluate` | `Schema__Step__Result__Evaluate` |
| `DISPATCH_EVENT` | `Schema__Step__Dispatch_Event` | `Schema__Step__Result__Base` |
| `SET_VIEWPORT` | `Schema__Step__Set_Viewport` | `Schema__Step__Result__Base` |
| `WAIT` | `Schema__Step__Wait` | `Schema__Step__Result__Base` |
| `GET_CONTENT` | `Schema__Step__Get_Content` | `Schema__Step__Result__Get_Content` |
| `GET_URL` | `Schema__Step__Get_Url` | `Schema__Step__Result__Get_Url` |
| `GET_TEXT` | `Schema__Step__Get_Text` | `Schema__Step__Result__Base` |
| `GET_HTML` | `Schema__Step__Get_Html` | `Schema__Step__Result__Base` |
| `GET_DOM_TREE` | `Schema__Step__Get_Dom_Tree` | `Schema__Step__Result__Base` |
| `GET_A11Y_TREE` | `Schema__Step__Get_A11y_Tree` | `Schema__Step__Result__Base` |
| `GET_PDF` | `Schema__Step__Get_Pdf` | `Schema__Step__Result__Base` |
| `GET_CONSOLE_TAIL` | `Schema__Step__Get_Console_Tail` | `Schema__Step__Result__Base` |
| `GET_NETWORK_FAILURES` | `Schema__Step__Get_Network_Failures` | `Schema__Step__Result__Base` |
| `SET_COOKIE` | `Schema__Step__Set_Cookie` | `Schema__Step__Result__Base` |

Result schemas not listed in `STEP_RESULT_SCHEMAS` default to `Schema__Step__Result__Base` via `result_schema_for()`. Helpers: `parse_step(step_dict, step_index)`.

---

## Schemas (`core/schemas/`)

Schemas live in folders by concern; see folder list (one class per file per rule #21):

| Folder | Purpose |
|--------|---------|
| `core/schemas/browser/` | Per-action one-shot request schemas (Navigate, Click, Fill, Get_Content, Get_Url, Screenshot) + `Schema__Browser__One_Shot__Response` |
| `core/schemas/screenshot/` | `Schema__Screenshot__Request`, `Schema__Screenshot__Response`, `Schema__Screenshot__Batch__Request`, `Schema__Screenshot__Batch__Response` |
| `core/schemas/sequence/` | `Schema__Sequence__Request`, `Schema__Sequence__Response`, `Schema__Sequence__Timings` |
| `core/schemas/steps/` | Per-step request schemas (16 step schemas, one per file) |
| `core/schemas/results/` | Step-result schemas (`Schema__Step__Result__Base`, `Get_Content`, `Get_Url`, `Evaluate`) |
| `core/schemas/session/` | Session-shape schemas — surfaced by the wired `Routes__Session` (`/session/*`, `Fast_API__Playwright__Service.py:111`); behind the `supports_persistent` capability |
| `core/schemas/capture/` | Video / artefact capture schemas |
| `core/schemas/artefact/` | `Artefact__Writer` output schemas |
| `core/schemas/service/` | Service-level config schemas |
| `core/schemas/primitives/` | `Safe_Str__*`, `Safe_Int__*`, identifiers (e.g. `Step_Id`) |
| `core/schemas/enums/` | `Enum__Step__Action`, etc. |
| `core/schemas/collections/` | Type-safe collections (`Dict__Step__Schemas__By_Action`, `Dict__Step__Result__Schemas__By_Action`) |
| `core/schemas/core/` | Shared core types |

Authoritative naming/typing rules: see [`library/guides/v3.28.0__safe_primitives.md`](../guides/v3.28.0__safe_primitives.md) and the schema catalogue spec (cited above).

---

## FastAPI Architecture

- `core/fast_api/Fast_API__Playwright__Service.py` — extends `Agentic_FastAPI`; holds one `Playwright__Service` instance + a `Request__Watchdog`; wires the route classes in `setup_routes()`; injects custom Swagger examples for `/screenshot` and `/screenshot/batch`.
- `core/fast_api/lambda_handler.py` — boots everything on import. Also serves as the Docker `CMD` for the standalone image.
- `core/agentic_fastapi/Agentic_FastAPI.py` — base class providing the admin surface + API-key middleware via `Serverless__Fast_API`.
- `core/agentic_fastapi/Agentic_Admin_API.py` — mounts the 8 admin routes.
- `core/agentic_fastapi/Agentic_Boot_State.py` — boot-log ring buffer + last-error holder.

API-key enforcement: `Serverless__Fast_API__Config` reads `FAST_API__AUTH__API_KEY__NAME` / `FAST_API__AUTH__API_KEY__VALUE`. The `/auth/set-cookie-form` and `/auth/set-auth-cookie` paths bypass the middleware.

---

## Prometheus Metrics

`core/metrics/Metrics__Collector.py` — module-level `CollectorRegistry` (read by `Routes__Metrics` with no service injection). Six metric families:

- `sg_playwright_request_total`
- `sg_playwright_request_duration_seconds`
- `sg_playwright_chromium_launch_seconds`
- `sg_playwright_navigate_seconds`
- `sg_playwright_chromium_teardown_seconds`
- `sg_playwright_total_duration_seconds`

Populated by `Playwright__Service.run_one_shot()` and `browser_screenshot()`.

---

## Docker Image (Spec ships as one image, runs anywhere)

- **Base:** `mcr.microsoft.com/playwright/python:v1.58.0-noble` (CLAUDE.md: v1.58.2 is not published)
- **Dockerfile:** `sg_compute_specs/playwright/Dockerfile`
- **Image name:** `diniscruz/sg-playwright:{version}`
- **CMD:** `python3 -m sg_compute_specs.playwright.core.fast_api.lambda_handler`
- **EXPOSE:** `8000`
- **Build-time guard:** asserts `playwright == 1.58.0` against the base image to catch interpreter / install mismatches in the Microsoft base.
- **Lambda Web Adapter:** REMOVED. The previous packaging path (with LWA + `/var/task`) was retired when the service was promoted into `sg_compute_specs/`.

---

## Outside Service Layer

- `sg_compute_specs/playwright/cli/Cli__Playwright.py` — wired into `sg playwright` typer namespace (see [`cli.md`](cli.md)).
- `sg_compute_specs/playwright/service/Playwright__Service.py` (different from the `core/service/Playwright__Service.py` orchestrator!) — the spec-level service that integrates with `Spec__Service__Base`, plus `Playwright__AMI__Helper`, `Playwright__AWS__Client`, `Playwright__Compose__Template`, `Playwright__Stack__Mapper`, `Playwright__User_Data__Builder`. These belong to the SG/Compute spec contract (covered in [`specs.md`](specs.md)), not the in-Lambda runtime.

---

## Reality + Spec Cross-Links

| Source of truth | Path |
|-----------------|------|
| Reality (Playwright service domain) | `team/roles/librarian/reality/playwright-service/index.md` — VERIFY: not yet migrated; current shim is [`team/roles/librarian/reality/_archive/v0.1.31/01__playwright-service.md`](../../team/roles/librarian/reality/_archive/v0.1.31/01__playwright-service.md) |
| Reality (SG/Compute spec — incl. Playwright spec wrapping) | [`team/roles/librarian/reality/sg-compute/specs.md`](../../team/roles/librarian/reality/sg-compute/specs.md) |
| Routes catalogue (spec) | [`library/docs/specs/v0.20.55__routes-catalogue-v2.md`](../docs/specs/v0.20.55__routes-catalogue-v2.md) |
| Schema catalogue (spec) | [`library/docs/specs/v0.20.55__schema-catalogue-v2.md`](../docs/specs/v0.20.55__schema-catalogue-v2.md) |
| CI pipeline (spec) | [`library/docs/specs/v0.20.55__ci-pipeline.md`](../docs/specs/v0.20.55__ci-pipeline.md) |
| Testing patterns | [`library/guides/v3.1.1__testing_guidance.md`](../guides/v3.1.1__testing_guidance.md) |
