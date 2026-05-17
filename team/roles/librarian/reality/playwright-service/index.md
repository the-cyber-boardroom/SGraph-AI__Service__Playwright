# playwright-service — Reality Index

**Domain:** `playwright-service/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** migrated from `_archive/v0.1.31/01__playwright-service.md` (v0.1.31 / v0.1.33).

The core FastAPI service: browser automation routes, the Type_Safe schema tree, the `Step__Executor` (sole owner of `page.*`), `Browser__Launcher`, `Sequence__Runner`, and the `Agentic_*` admin / boot scaffolding layered on top.

**Canonical package:** `sgraph_ai_service_playwright/`. Image base: `mcr.microsoft.com/playwright/python:v1.58.0-noble` (Lambda Web Adapter 1.0.0). Lambda handler: `sgraph_ai_service_playwright/fast_api/lambda_handler.py`.

> **Post-v0.1.31 note:** as of BV2.11 (2026-05-05), the Playwright Lambda packaging moved to `sg_compute_specs.playwright.core`. The `sgraph_ai_service_playwright/` package itself was deleted in that change. The route surface described below was authoritative at v0.1.33; verify against `sg_compute_specs/playwright/` before quoting it as current behaviour. **VERIFY**: route count and admin surface against the post-BV2.11 tree.

---

## EXISTS (code-verified at v0.1.33; partial-VERIFY since BV2.11)

### API surface — 19 endpoints (v0.1.33)

#### Public (10) — `/health/*` + `/browser/*` + `/sequence/*`

| Method | Path | Notes |
|--------|------|-------|
| GET  | `/health/info` | Service identity |
| GET  | `/health/status` | Liveness |
| GET  | `/health/capabilities` | Declared capabilities |
| POST | `/browser/navigate` | Page navigation step |
| POST | `/browser/click` | Click step |
| POST | `/browser/fill` | Fill input step |
| POST | `/browser/screenshot` | Capture screenshot, write to sink |
| POST | `/browser/get-content` | Extract page HTML / text |
| POST | `/browser/get-url` | Current URL |
| POST | `/sequence/execute` | Layer-3 multi-step sequence |

#### Metrics (1) — added v0.1.46

- `GET /metrics` — Prometheus text exposition (`text/plain`). API-key-gated. Module-level `CollectorRegistry` in `metrics/Metrics__Collector.py`. Populated by `Playwright__Service.run_one_shot()` and `browser_screenshot()`.

#### Admin (8) — landed v0.1.29, unauthenticated read-only

| Path | What it returns |
|------|-----------------|
| `GET /admin/health` | `{status, code_source}`; flips `loaded → degraded` when `set_last_error(…)` fires |
| `GET /admin/info` | app name / stage / version / image_version / code_source / python_version |
| `GET /admin/env` | `{agentic_vars}` filtered to `AGENTIC_*` prefix only (no AWS / `SG_PLAYWRIGHT` leakage) |
| `GET /admin/boot-log` | Ring-buffer of boot lines (max 200) |
| `GET /admin/error` | `{has_error, error}` last-error holder |
| `GET /admin/manifest` | Points at `/openapi.json`, `/admin/capabilities`, per-SKILL file URLs |
| `GET /admin/capabilities` | `capabilities.json` (axioms + declared_narrowing) |
| `GET /admin/skills/{name}` | Markdown SKILL content for `{human, browser, agent}`; 404 on unknown name |

Plus osbot-fast-api's `/auth/set-cookie-form` HTML UI + `/auth/set-auth-cookie` POST.

---

### Service classes — 9 of 10 live (post v0.1.33)

| Class | File | Notes |
|-------|------|-------|
| `Browser__Launcher` | `service/Browser__Launcher.py` | `build_proxy_dict()` reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL`. Carve-out: also touches `page.*` for process lifecycle. |
| `Sequence__Runner` | `service/Sequence__Runner.py` | `get_or_create_page()` reads `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` env var. |
| `Playwright__Service` | `service/Playwright__Service.py` | `proxy_auth_binder` field removed in v0.1.33. |
| `Step__Executor` | `service/Step__Executor.py` | Only class allowed to call `page.*`. |
| `Artefact__Writer` | `service/Artefact__Writer.py` | Only class allowed to write to sinks. |
| `Request__Validator` | `service/Request__Validator.py` | Cross-schema validation. |
| (others) | `service/*.py` | 9 surviving classes total. Unchanged from v0.1.24. |
| ~~`Proxy__Auth__Binder`~~ | (deleted) | CDP Fetch dance — replaced by `agent_mitmproxy` sidecar in v0.1.33. |

---

### FastAPI app classes

- `agentic_fastapi/Agentic_FastAPI` — base. `setup()` extends `AUTH__EXCLUDED_PATHS` with the 8 admin paths. `setup_routes()` chains `super().setup_routes()` then mounts `Agentic_Admin_API`. `resolve_capabilities_path()` prefers `/var/task/capabilities.json` (baked into Lambda) over the repo-root stub.
- `agentic_fastapi/Agentic_Admin_API` — `Fast_API__Routes` subclass for the 8 admin routes.
- `agentic_fastapi/Agentic_Boot_State` — module-level ring buffer (`BOOT_LOG_MAX_LINES = 200`) + `_last_error`. `get_boot_log()` returns a copy.
- `agentic_fastapi_aws/Agentic_Boot_Shim` — writes boot-state on each stage; pins `set_last_error(CRITICAL ERROR: …)` on failure inside Lambda, re-raises outside.
- `fast_api/Fast_API__Playwright__Service` — extends `Agentic_FastAPI`; `setup_routes()` starts with `super().setup_routes()` so the admin surface always lands.
- `fast_api/lambda_handler.run()` — fires everything on import.

---

### Schemas

All `Type_Safe`, one class per file, no Pydantic, no Literals.

#### L1 admin schemas (`agentic_fastapi/schemas/`, new v0.1.29)

| Schema | Fields |
|--------|--------|
| `Schema__Agentic__Health` | `status: Safe_Str__Text`, `code_source: Safe_Str__Text__Dangerous` |
| `Schema__Agentic__Info` | `app_name`, `app_stage`, `app_version`, `image_version`, `code_source`, `python_version` |
| `Schema__Agentic__Env` | `agentic_vars: Dict[Safe_Str__Text, Safe_Str__Text__Dangerous]` |
| `Schema__Agentic__Boot_Log` | `lines: List[Safe_Str__Text__Dangerous]` |
| `Schema__Agentic__Error` | `has_error: bool`, `error: Safe_Str__Text__Dangerous` |
| `Schema__Agentic__Manifest` | `app_name`, `openapi_path / capabilities_path: Safe_Str__Url__Path`, `skills: Dict[…]` |
| `Schema__Agentic__Skill` | `name`, `content: Safe_Str__Markdown` |
| `Schema__Agentic__Capabilities` | `app`, `version`, `axioms / declared_narrowing: List[Safe_Str__Text]` |

#### Deletions (v0.1.33 P2 proxy cleanup)

- `schemas/browser/Schema__Proxy__Config.py` — proxy is now boot-time infrastructure, not per-request.
- `schemas/browser/Schema__Proxy__Auth__Basic.py` — same reason.
- `Schema__Browser__Config.proxy` and `Schema__Browser__Launch__Result.proxy` fields removed.

Other schema folders unchanged from v0.1.24.

---

### Consts

- `consts/env_vars.py` — `SG_PLAYWRIGHT__*` boot-loader constants removed in v0.1.29; `ENV_VAR__AGENTIC_*` added. Unrelated `SG_PLAYWRIGHT__*` constants (proxy creds, vault refs, sink config) preserved.

### Packaging

- `pyproject.toml` (Poetry, Python ^3.12) — unchanged from v0.1.24.
- `requirements.txt` at repo root mirrors runtime deps.

### Public endpoint

- **Dev:** `https://dev.playwright.sgraph.ai/` — CloudFront in front of Lambda Function URL. `/admin/*` reachable alongside the 10 public endpoints.

---

### EC2 two-container stack (v0.1.33)

- `docker-compose.yml` (repo root) — Playwright + `agent_mitmproxy` on shared `sg-net` bridge. Playwright on host `:8000`; sidecar admin API on host `:8001`; sidecar proxy `:8080` Docker-network-only. Env wiring: `SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://agent-mitmproxy:8080` + `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=true`.
- `.env.example` — template for ECR registry, API key, optional upstream forwarding vars.
- `scripts/provision_ec2.py` — unified EC2 provisioner. t3.large AL2023; IAM role `sg-playwright-ec2` + SSM access; SG `playwright-ec2` opens `:8000` + `:8001`. UserData installs `docker docker-compose-plugin`, logs into ECR, pulls both images, writes inline `/opt/sg-playwright/docker-compose.yml`, runs `docker compose up -d`. `--terminate` tears down by `Name=sg-playwright-ec2` tag.
- **Deleted:** `scripts/provision_mitmproxy_ec2.py` + `tests/unit/scripts/test_provision_mitmproxy_ec2.py` — replaced by the unified script.
- Tests: `tests/unit/scripts/test_provision_ec2.py` (19 tests).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Source: [`_archive/v0.1.31/01__playwright-service.md`](../_archive/v0.1.31/01__playwright-service.md)
- Sibling: [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md) — the upstream-proxy companion
- Security: [`security/index.md`](../security/index.md) — JS expression allowlist + AppSec rules cited by `Step__Executor`
- Infra: [`infra/index.md`](../infra/index.md) — Docker image + CI pipeline
- QA: [`qa/index.md`](../qa/index.md) — test inventory
- SG/Compute: [`sg-compute/index.md`](../sg-compute/index.md) — current home of the Playwright Lambda after BV2.11
