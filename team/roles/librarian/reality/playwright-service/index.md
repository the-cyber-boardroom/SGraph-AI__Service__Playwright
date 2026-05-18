# playwright-service — Reality Index

**Domain:** `playwright-service/` | **Last updated:** 2026-05-18 | **Maintained by:** Librarian
**Code-source basis:** verified against `sg_compute_specs/playwright/` at v0.2.28 (post-BV2.11 / post-FV2.6).

The core FastAPI service: browser automation routes, the Type_Safe schema tree, the `Step__Executor` (sole owner of `page.*`), `Browser__Launcher`, `Sequence__Runner`, and the agentic admin / boot scaffolding layered on top.

**Canonical package:** `sg_compute_specs/playwright/core/`. Image base: `mcr.microsoft.com/playwright/python:v1.58.0-noble`. Image ships as **`diniscruz/sg-playwright`** on Docker Hub (post-v0.2.11 — the Lambda / ECR / S3-zip route was retired). Lambda handler stub (kept for parity, not in the live deployment path): `sg_compute_specs/playwright/core/fast_api/lambda_handler.py`.

The orphan `sgraph_ai_service_playwright/` package was **deleted in BV2.11 (2026-05-05)** and is not coming back. All paths below resolve to `sg_compute_specs/playwright/` (and `sg_compute_specs/playwright/core/` for runtime modules) only.

---

## EXISTS (code-verified at v0.2.28)

### API surface — 16 direct endpoints

Wired by `Fast_API__Playwright__Service.setup_routes()` (`sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py:88-96`). Six in-repo route classes plus `Routes__Set_Cookie` imported from `osbot_fast_api.api.routes.Routes__Set_Cookie`.

#### Health (3) — `Routes__Health`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health/info` | Service identity (`Schema__Service__Info`) |
| GET | `/health/status` | Liveness (`Schema__Health`) |
| GET | `/health/capabilities` | Declared capabilities (`Schema__Service__Capabilities`) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Health.py:31-43`.

#### Browser one-shot (6) — `Routes__Browser`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/browser/navigate` | Page navigation step |
| POST | `/browser/click` | Click step |
| POST | `/browser/fill` | Fill input step |
| POST | `/browser/get-content` | Extract page HTML / text (osbot-fast-api maps `_` → `-` in paths) |
| POST | `/browser/get-url` | Current URL |
| POST | `/browser/screenshot` | Raw PNG `Response` — bypasses JSON serialisation |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Browser.py:51-82`. Each launches fresh Chromium, runs a tiny sequence, tears down.

#### Screenshot (2) — `Routes__Screenshot` (mounted at root, prefix `/`)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/screenshot` | Single screenshot (`Schema__Screenshot__Request` → `dict`) |
| POST | `/screenshot/batch` | Batch screenshots (`Schema__Screenshot__Batch__Request` → `dict`) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Screenshot.py:25-42`. OpenAPI examples injected by `attach_screenshot_examples()` in `Fast_API__Playwright__Service`.

#### Sequence (1) — `Routes__Sequence`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/sequence/execute` | Layer-3 multi-step declarative sequence |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Sequence.py:27-31`.

#### Metrics (1) — `Routes__Metrics` (mounted at root, prefix `/`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/metrics` | Prometheus text exposition (`text/plain`). Module-level `_REGISTRY` in `metrics/Metrics__Collector.py`. |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Metrics.py:24-33`.

#### Index (1) — `Routes__Index` (mounted at root, prefix `/`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Static "Try it out" mini-site (HTML) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py:601-612`.

#### Set-Cookie (2) — `osbot_fast_api.api.routes.Routes__Set_Cookie`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/auth/set-cookie-form` | HTML UI for setting the auth cookie |
| POST | `/auth/set-auth-cookie` | Cookie write |

Both paths sit in `AUTH__EXCLUDED_PATHS` so they bypass the API-key middleware.

### Admin surface (8) — `Agentic_Admin_API` (mounted by `Agentic_FastAPI.setup_routes()` super-call)

Unauthenticated read-only (paths appended to `AUTH__EXCLUDED_PATHS` in `Agentic_FastAPI.setup()`).

| Path | What it returns | Source |
|------|-----------------|--------|
| `GET /admin/health` | `{status, code_source}`; flips `loaded → degraded` when `set_last_error(...)` fires | `Agentic_Admin_API.health` |
| `GET /admin/info` | app name / stage / version / image_version / code_source / python_version | `.info` |
| `GET /admin/env` | `{agentic_vars}` filtered to `AGENTIC_*` prefix only (no AWS / `SG_PLAYWRIGHT` leakage) | `.env` |
| `GET /admin/boot-log` | Ring-buffer of boot lines (max 200) | `.boot_log` |
| `GET /admin/error` | `{has_error, error}` last-error holder | `.error` |
| `GET /admin/skills/{name}` | Markdown SKILL content (`human` / `browser` / `agent`); 404 on unknown name | `.skills__name` |
| `GET /admin/manifest` | Points at `/openapi.json`, `/admin/capabilities`, per-SKILL file URLs | `.manifest` |
| `GET /admin/capabilities` | `capabilities.json` (axioms + declared_narrowing) | `.capabilities` |

Source: `sg_compute_specs/playwright/core/agentic_fastapi/Agentic_Admin_API.py:64-130`.

> **Historical:** `Routes__Session` and `Routes__Quick` were removed in v0.1.24 — sessions are no longer a wire-visible resource, and `/quick/*` was absorbed into the stateless `/browser/*` surface. The comment block in `Fast_API__Playwright__Service.py:18-20` preserves this fact.

---

### Service classes — 11 live (`sg_compute_specs/playwright/core/service/`)

| Class | File | Notes |
|-------|------|-------|
| `Browser__Launcher` | `Browser__Launcher.py` | Reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` for boot-time proxy. Carve-out: also touches `page.*` for process lifecycle. |
| `Sequence__Runner` | `Sequence__Runner.py` | `get_or_create_page()` reads `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS`. |
| `Sequence__Dispatcher` | `Sequence__Dispatcher.py` | Step dispatch into `Step__Executor`. |
| `Playwright__Service` | `Playwright__Service.py` | Service composition root. (`proxy_auth_binder` field removed in v0.1.33.) |
| `Step__Executor` | `Step__Executor.py` | **Only class allowed to call `page.*`.** |
| `Artefact__Writer` | `Artefact__Writer.py` | **Only class allowed to write to sinks.** |
| `Request__Validator` | `Request__Validator.py` | Cross-schema validation. |
| `Request__Watchdog` | `Request__Watchdog.py` | Background thread; fires `os._exit(2)` when a request exceeds the hard cap. |
| `JS__Expression__Allowlist` | `JS__Expression__Allowlist.py` | Deny-all default for the `evaluate` action. |
| `Credentials__Loader` | `Credentials__Loader.py` | Vault-side credentials hydration. |
| `Capability__Detector` | `Capability__Detector.py` | Primed in `Fast_API__Playwright__Service.setup()`. |

(`Proxy__Auth__Binder` was deleted in v0.1.33 — replaced by the `agent_mitmproxy` sidecar pattern; the sidecar lives under `sg_compute_specs/mitmproxy/` post-BV2.12.)

There is **no separate `sg_compute_specs/playwright/service/` "core" duplicate** — the higher-level `service/` folder at `sg_compute_specs/playwright/service/` is the *spec orchestration* layer (`Playwright__Service`, `Playwright__Compose__Template`, `Playwright__User_Data__Builder`, `Playwright__AMI__Helper`, `Playwright__AWS__Client`, `Playwright__Stack__Mapper`) consumed by `sg-compute spec playwright create`. See [`sg-compute/index.md`](../sg-compute/index.md) for that surface.

---

### FastAPI app classes (`sg_compute_specs/playwright/core/agentic_fastapi/` + `core/fast_api/`)

- `agentic_fastapi/Agentic_FastAPI` — base. `setup()` extends `AUTH__EXCLUDED_PATHS` with the 8 admin paths (including the per-SKILL `/admin/skills/{name}` paths). `setup_routes()` mounts `Agentic_Admin_API`. `resolve_capabilities_path()` prefers `/var/task/capabilities.json` over the repo-root stub.
- `agentic_fastapi/Agentic_Admin_API` — `Fast_API__Routes` subclass for the 8 admin routes.
- `agentic_fastapi/Agentic_Boot_State` — module-level ring buffer (`BOOT_LOG_MAX_LINES = 200`) + `_last_error`. `get_boot_log()` returns a copy.
- `fast_api/Fast_API__Playwright__Service` — extends `Agentic_FastAPI`; `setup()` runs `service.setup()` + `watchdog.setup().start()` + middleware + screenshot OpenAPI examples; `setup_routes()` chains `super().setup_routes()` so the admin surface always lands.
- `fast_api/lambda_handler.py` — Lambda-parity stub (the service deploys as a Docker Hub image now, not Lambda; the handler is kept for local-test parity).

---

### Schemas

All `Type_Safe`, one class per file, no Pydantic, no Literals. Sub-trees under `sg_compute_specs/playwright/core/schemas/`:

`sequence/`, `browser/`, `screenshot/`, `session/`, `service/`, `results/`, `artefact/`, `steps/`, `enums/`, `collections/`, `core/`, `capture/`, `primitives/{text,auth,browser,vault,identifiers,host,s3,numeric}/`.

#### L1 admin schemas (`agentic_fastapi/schemas/` under `core/`)

| Schema | Fields |
|--------|--------|
| `Schema__Agentic__Health` | `status`, `code_source` |
| `Schema__Agentic__Info` | `app_name`, `app_stage`, `app_version`, `image_version`, `code_source`, `python_version` |
| `Schema__Agentic__Env` | `agentic_vars: Dict[Safe_Str__Text, Safe_Str__Text__Dangerous]` |
| `Schema__Agentic__Boot_Log` | `lines: List[Safe_Str__Text__Dangerous]` |
| `Schema__Agentic__Error` | `has_error: bool`, `error: Safe_Str__Text__Dangerous` |
| `Schema__Agentic__Manifest` | `app_name`, `openapi_path / capabilities_path: Safe_Str__Url__Path`, `skills: Dict[…]` |
| `Schema__Agentic__Skill` | `name`, `content: Safe_Str__Markdown` |
| `Schema__Agentic__Capabilities` | `app`, `version`, `axioms / declared_narrowing: List[Safe_Str__Text]` |

#### Deletions (v0.1.33 P2 proxy cleanup, still in force)

- `schemas/browser/Schema__Proxy__Config.py` — gone.
- `schemas/browser/Schema__Proxy__Auth__Basic.py` — gone.
- `Schema__Browser__Config.proxy` and `Schema__Browser__Launch__Result.proxy` fields removed. Proxy is now boot-time infrastructure.

---

### Consts (`sg_compute_specs/playwright/core/consts/`)

- `env_vars.py` — two namespaces: framework-level `AGENTIC_*` (boot loader: `APP_NAME`, `APP_STAGE`, `APP_VERSION`, `CODE_LOCAL_PATH`, `CODE_SOURCE`, `CODE_SOURCE_S3_BUCKET`, `CODE_SOURCE_S3_KEY`, `IMAGE_VERSION`, `ADMIN_MODE`) + app-specific `SG_PLAYWRIGHT__*` (auth tokens, vault, browser defaults including `DEFAULT_HEADLESS` / `DEFAULT_PROXY_URL` / `IGNORE_HTTPS_ERRORS`, watchdog, sink config).
- `version.py` — `version__sgraph_ai_service_playwright` (reads `core/version`).
- `image_version.py` — `image_version` constant.

### Packaging

- `sg_compute_specs/pyproject.toml` (Poetry, Python ^3.12) — top-level spec package.
- `requirements.txt` at repo root mirrors runtime deps for the FastAPI image.

### Public endpoint

- **Dev:** `https://dev.playwright.sgraph.ai/` — CloudFront in front of the Docker Hub image (post v0.2.11 the Lambda Function URL is gone). `/admin/*` reachable alongside the 16 direct public endpoints.

---

### EC2 stack (current — `sg-compute spec playwright create`)

The standalone repo-root `docker-compose.yml` was retired. The compose file is now **generated per-launch** by `sg_compute_specs/playwright/service/Playwright__Compose__Template.py` and written to `/opt/sg-playwright/docker-compose.yml` on the launched EC2.

- **Default shape (2 containers):** host-plane + `diniscruz/sg-playwright` (Docker Hub pull).
- **`--with-mitmproxy` shape (3 containers):** + `agent_mitmproxy` (ECR pull).
- Published host ports: `:8000` (Playwright), `:8001` (mitmproxy admin, only with `--with-mitmproxy`). Host-plane stays on the internal `sg-net` bridge; reach it via SSM port-forward.
- IAM profile `playwright-ec2` grants SSM + ECR access.
- Stack lifecycle owned by `sg_compute_specs/playwright/service/Playwright__Service.py` (extends `Spec__Service__Base`).

(`scripts/provision_ec2.py` and `scripts/provision_mitmproxy_ec2.py` no longer exist at the repo root — both spike scripts were removed when the spec service took over. `tests/unit/scripts/test_provision_mitmproxy_ec2.py` survives as a `@pytest.mark.skip` placeholder.)

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sibling (sidecar): [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md)
- Security: [`security/index.md`](../security/index.md) — JS expression allowlist + AppSec rules cited by `Step__Executor`
- Infra: [`infra/index.md`](../infra/index.md) — Docker Hub image build + CI pipeline
- QA: [`qa/index.md`](../qa/index.md) — test inventory
- SG/Compute: [`sg-compute/index.md`](../sg-compute/index.md) — spec orchestration around the runtime
