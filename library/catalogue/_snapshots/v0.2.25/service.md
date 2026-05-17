---
title: "Catalogue — Playwright Service"
file: service.md
shard: service
as_of: v0.2.25
last_refreshed: 2026-05-17
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

> VERIFY: CLAUDE.md still asserts `25 endpoints (3 health + 5 session + 16 browser Layer 0 + 1 sequence Layer 3)`. The route classes wired in `Fast_API__Playwright__Service.setup_routes()` (verified 2026-05-17) total 23 routes when itemised below — no `Routes__Session` is wired today (sessions were removed in v0.1.24 per the file header). The CLAUDE.md count needs reconciliation; the table below is the code-truth.

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

### Routes__Metrics — 1 endpoint (`Routes__Metrics.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/metrics` | `Routes__Metrics.metrics` | Prometheus text exposition |

### Routes__Index — 1 endpoint (`Routes__Index.py`)

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET | `/` | `Routes__Index.index` | Static "Try it out" mini-site (HTML) |

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

**Code-verified total: 23 endpoints** (3 health + 6 browser + 2 screenshot + 1 sequence + 1 metrics + 1 index + 2 set-cookie + 8 admin). The CLAUDE.md "25" figure includes some count not represented in `setup_routes()` today — flag for reconciliation under a follow-up.

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
| `Credentials__Loader` | Loads vault credentials. |
| `JS__Expression__Allowlist` | Allowlist gate for `evaluate` step actions — defaults to deny-all. |

> Historical note: `Proxy__Auth__Binder` was removed in v0.1.33; the `agent_mitmproxy` sidecar (also since deleted in BV2.12, 2026-05-05) handled upstream proxy auth.

---

## Step Action Registry (`core/dispatcher/step_schema_registry.py`)

16 step actions live today in `STEP_SCHEMAS : Dict__Step__Schemas__By_Action`:

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
| `GET_CONTENT` | `Schema__Step__Get_Content` | `Schema__Step__Result__Get_Content` |
| `GET_URL` | `Schema__Step__Get_Url` | `Schema__Step__Result__Get_Url` |

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
| `core/schemas/session/` | Session-shape schemas — VERIFY: present on disk but not surfaced by any wired route today |
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
