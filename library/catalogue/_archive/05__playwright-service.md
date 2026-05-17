# 05 — Playwright Service

→ [Catalogue README](README.md)

The browser-automation FastAPI service. Lives in `sgraph_ai_service_playwright/`.
Runs on Lambda (Lambda Web Adapter), EC2, Docker, and local.

---

## API Surface — 19 Endpoints

### Health (3)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health/info` | App info |
| GET | `/health/status` | Service status |
| GET | `/health/capabilities` | Declared capabilities |

### Browser (10) — public, API-key-gated

| Method | Path |
|--------|------|
| POST | `/browser/navigate` |
| POST | `/browser/click` |
| POST | `/browser/fill` |
| POST | `/browser/screenshot` |
| POST | `/browser/get-content` |
| POST | `/browser/get-url` |
| POST | `/sequence/execute` |

### Metrics (1)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/metrics` | Prometheus text exposition, API-key-gated |

### Admin (8) — unauthenticated, read-only

| Path | Returns |
|------|---------|
| `GET /admin/health` | `{status, code_source}` |
| `GET /admin/info` | App name / stage / version / image_version / code_source |
| `GET /admin/env` | `AGENTIC_` prefixed env vars only |
| `GET /admin/boot-log` | Ring buffer of boot lines (max 200) |
| `GET /admin/error` | Last error holder |
| `GET /admin/manifest` | Links to OpenAPI + capabilities + skills |
| `GET /admin/capabilities` | `capabilities.json` contents |
| `GET /admin/skills/{name}` | Markdown skill content (human / browser / agent) |

Also: `/auth/set-cookie-form` + `/auth/set-auth-cookie` from osbot-fast-api.

---

## Service Classes (10 of 10 live)

`sgraph_ai_service_playwright/service/`

| Class | Responsibility |
|-------|---------------|
| `Playwright__Service` | Top-level orchestrator |
| `Browser__Launcher` | `page.*` process lifecycle; `build_proxy_dict()` reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` |
| `Step__Executor` | **ONLY class that calls `page.*`** Playwright methods |
| `Sequence__Runner` | Runs a multi-step sequence; calls `Step__Executor` |
| `Sequence__Dispatcher` | Routes step types to Step__Executor |
| `Artefact__Writer` | **ONLY class that writes to sinks** |
| `Request__Validator` | **ALL cross-schema validation** |
| `Request__Watchdog` | Timeout / watchdog management |
| `Capability__Detector` | Detects browser capabilities |
| `Credentials__Loader` | Loads vault credentials |
| `JS__Expression__Allowlist` | Allowlist gate for evaluate actions (defaults to deny-all) |

(Note: `Proxy__Auth__Binder` was deleted in v0.1.33 — proxy auth handled by agent_mitmproxy sidecar.)

---

## FastAPI Architecture

- `fast_api/Fast_API__Playwright__Service.py` — extends `Agentic_FastAPI`; `setup_routes()` wires all route files.
- `fast_api/lambda_handler.py` — fires everything on import (Lambda Web Adapter pattern).
- `agentic_fastapi/Agentic_FastAPI` — base class with admin surface + API-key middleware.
- `agentic_fastapi/Agentic_Admin_API` — registers the 8 admin routes.
- `agentic_fastapi/Agentic_Boot_State` — ring buffer + last-error holder.
- `agentic_fastapi_aws/Agentic_Boot_Shim` — writes boot-state stages on Lambda cold-start.

---

## Prometheus Metrics

`sgraph_ai_service_playwright/metrics/Metrics__Collector.py` — module-level `CollectorRegistry` with 6 metrics:

- `sg_playwright_request_total`
- `sg_playwright_request_duration_seconds`
- `sg_playwright_chromium_launch_seconds`
- `sg_playwright_navigate_seconds`
- `sg_playwright_chromium_teardown_seconds`
- `sg_playwright_total_duration_seconds`

Populated by `Playwright__Service.run_one_shot()` and `browser_screenshot()`.

---

## Docker Image

- **Base:** `mcr.microsoft.com/playwright/python:v1.58.0-noble` (v1.58.2 is not published)
- **Lambda adapter:** AWS Lambda Web Adapter 1.0.0
- **Baked:** `capabilities.json` → `/var/task/`; `image_version` file written at build time
- **Build:** `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py`
- **ECR push:** `tests/docker/test_ECR__Docker__SGraph-AI__Service__Playwright.py`

---

## agent_mitmproxy Sidecar

`agent_mitmproxy/` — forward-proxy sidecar. Runs alongside Playwright on EC2 via `docker-compose.yml`.

- Admin FastAPI: 6 endpoints (2 health + 2 CA + 1 config + 1 UI-proxy), API-key-gated
- Addons: `Default_Interceptor` (request-id + timestamps), `Audit_Log` (NDJSON to stdout), `Prometheus_Metrics` (4 `sg_mitmproxy_*` metrics)
- Docker: `python:3.12-slim` + supervisor + mitmweb + uvicorn

---

## Public Endpoint

- **Dev:** `https://dev.playwright.sgraph.ai/` — CloudFront → Lambda Function URL

---

## Cross-Links

- `08__aws-and-infrastructure.md` — Lambda deploy details
- `07__testing-patterns.md` — test patterns for this service
- `team/roles/librarian/reality/v0.1.31/01__playwright-service.md` — canonical reality
- `team/roles/librarian/reality/v0.1.31/02__agent-mitmproxy-sibling.md` — agent_mitmproxy reality
