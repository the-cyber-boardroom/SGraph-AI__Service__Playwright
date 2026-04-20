# Playwright Service — Reality (v0.1.31)

See [README.md](README.md) for the index and split rationale.

---

## API surface — 18 endpoints

### Public (10, unchanged since v0.1.24)

- `GET  /health/info`
- `GET  /health/status`
- `GET  /health/capabilities`
- `POST /browser/navigate`
- `POST /browser/click`
- `POST /browser/fill`
- `POST /browser/screenshot`
- `POST /browser/get-content`
- `POST /browser/get-url`
- `POST /sequence/execute`

### Admin (8, landed in v0.1.29 — unauthenticated, read-only)

- `GET /admin/health`                      — `{status, code_source}`; flips `loaded → degraded` when `set_last_error(…)` is called.
- `GET /admin/info`                        — app name / stage / version / image_version / code_source / python_version.
- `GET /admin/env`                         — `{agentic_vars}` filtered to the `AGENTIC_` prefix only (no AWS / `SG_PLAYWRIGHT` leakage).
- `GET /admin/boot-log`                    — ring-buffer of boot progress lines (max 200).
- `GET /admin/error`                       — `{has_error, error}` last-error holder.
- `GET /admin/manifest`                    — points at `/openapi.json`, `/admin/capabilities`, and each SKILL file URL.
- `GET /admin/capabilities`                — `capabilities.json` contents (axioms + declared_narrowing).
- `GET /admin/skills/{name}`               — markdown SKILL content for `{human, browser, agent}`; 404 on unknown name when the API-key middleware isn't gating, 401 when it is (unknown names aren't on the exclude list).

Plus osbot-fast-api's `/auth/set-cookie-form` HTML UI + `/auth/set-auth-cookie` POST.

---

## Service classes — 9 of 10 live (v0.1.33)

- **DELETED** `service/Proxy__Auth__Binder.py` — CDP Fetch dance for Chromium proxy auth. Now dead code: the `agent_mitmproxy` sidecar handles upstream auth; Playwright sees an unauthenticated local proxy.
- `service/Browser__Launcher.py` — `build_proxy_dict()` now reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` env var (no per-request proxy; auth branching removed).
- `service/Sequence__Runner.py` — `get_or_create_page()` reads `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` env var; no longer calls `proxy_auth_binder.bind()`.
- `service/Playwright__Service.py` — `proxy_auth_binder` field removed.

All other 9 service classes unchanged from v0.1.24.

---

## FastAPI app

- `agentic_fastapi/Agentic_FastAPI` — base class. `setup()` extends `AUTH__EXCLUDED_PATHS` with the 8 admin paths (middleware uses exact match, so unknown `/admin/skills/{name}` audiences 401 before the route's 404 can land — accepted). `setup_routes()` calls `super().setup_routes()` then `self.add_routes(Agentic_Admin_API, skills_dir, capabilities_path)`. `resolve_skills_dir()` defaults to the in-tree `skills/` folder; `resolve_capabilities_path()` prefers `/var/task/capabilities.json` when present (baked into the Lambda image), else the repo-root stub.
- `agentic_fastapi/Agentic_Admin_API` — `Fast_API__Routes` subclass registering the 8 admin routes. `env()` filters `os.environ` by `AGENTIC_` prefix; `skills__name(name)` reads `skills/skill__{name}.md` and 404s on unknown; `capabilities()` reads the JSON file, returns `Schema__Agentic__Capabilities`.
- `agentic_fastapi/Agentic_Boot_State` — module-level ring buffer (`BOOT_LOG_MAX_LINES = 200`) + `_last_error` string; `get_boot_log()` returns a copy (callers can't mutate); `set_last_error(None)` coerces to `''`; `reset_boot_state()` for tests.
- `agentic_fastapi_aws/Agentic_Boot_Shim` — writes to `Agentic_Boot_State` on each stage (`image_version=…`, `code_source=…`, `status=loaded`) and on failure (`status=degraded …` + `set_last_error(CRITICAL ERROR: …)`).
- `fast_api/Fast_API__Playwright__Service` — extends `Agentic_FastAPI`; `setup_routes()` starts with `super().setup_routes()` so the admin surface always lands.
- `fast_api/lambda_handler.run()` — unchanged (still fires everything on import).

---

## Schemas

All schemas are one-class-per-file, `Type_Safe` only, no Pydantic, no Literals.

### L1 admin schemas (`agentic_fastapi/schemas/`) — 8 files, new in v0.1.29

- `Schema__Agentic__Health`        — `status: Safe_Str__Text`, `code_source: Safe_Str__Text__Dangerous` (Dangerous preserves `/`, `:` in `s3:bucket/key`).
- `Schema__Agentic__Info`          — `app_name / app_stage: Safe_Str__Text`; `app_version / image_version: Safe_Str__Version`; `code_source / python_version: Safe_Str__Text__Dangerous`.
- `Schema__Agentic__Env`           — `agentic_vars : Dict[Safe_Str__Text, Safe_Str__Text__Dangerous]`.
- `Schema__Agentic__Boot_Log`      — `lines : List[Safe_Str__Text__Dangerous]`.
- `Schema__Agentic__Error`         — `has_error: bool`, `error: Safe_Str__Text__Dangerous`.
- `Schema__Agentic__Manifest`      — `app_name: Safe_Str__Text`, `openapi_path / capabilities_path: Safe_Str__Url__Path`, `skills: Dict[Safe_Str__Text, Safe_Str__Url__Path]`.
- `Schema__Agentic__Skill`         — `name: Safe_Str__Text`, `content: Safe_Str__Markdown`.
- `Schema__Agentic__Capabilities`  — `app: Safe_Str__Text`, `version: Safe_Str__Version`, `axioms / declared_narrowing: List[Safe_Str__Text]`.

### Other schema folders

Unchanged from v0.1.24, with the following exceptions from v0.1.33 (P2 proxy cleanup):

- **DELETED** `schemas/browser/Schema__Proxy__Config.py` — proxy is now boot-time infrastructure, not per-request.
- **DELETED** `schemas/browser/Schema__Proxy__Auth__Basic.py` — same reason.
- `schemas/browser/Schema__Browser__Config.py` — `proxy: Schema__Proxy__Config` field removed.
- `schemas/browser/Schema__Browser__Launch__Result.py` — `proxy: Schema__Proxy__Config` field removed.

---

## Consts

- `consts/env_vars.py` — `SG_PLAYWRIGHT__*` boot-loader constants removed (v0.1.29); `ENV_VAR__AGENTIC_*` added. Unrelated `SG_PLAYWRIGHT__*` constants (proxy creds, vault refs, sink config) preserved.

---

## Packaging

- `pyproject.toml` (Poetry, Python ^3.12) unchanged from v0.1.24.
- `requirements.txt` at repo root (mirrors runtime deps).

---

## Public endpoint

- **Dev:** `https://dev.playwright.sgraph.ai/` — CloudFront in front of the Lambda Function URL. Post-deploy, `/admin/*` is reachable alongside the 10 public endpoints.

---

## EC2 two-container stack (v0.1.33)

- `docker-compose.yml` (repo root) — brings up Playwright + agent_mitmproxy on a shared `sg-net` bridge network. Playwright on host `:8000`, sidecar admin API on host `:8001`, sidecar proxy `:8080` Docker-network-only (never on host). Reads from `.env` (see `.env.example`). `SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://agent-mitmproxy:8080` + `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=true` are wired in.
- `.env.example` (repo root) — template for ECR registry, API key, optional upstream forwarding vars.
- `scripts/provision_ec2.py` (v0.1.33) — unified EC2 provisioner replacing the two spike scripts. t3.large AL2023 instance; IAM role `sg-playwright-ec2` + SSM access; SG `playwright-ec2` opens `:8000` + `:8001` (sidecar proxy stays internal). UserData installs `docker docker-compose-plugin`, logs into ECR, pulls both images, writes `/opt/sg-playwright/docker-compose.yml` inline, runs `docker compose up -d`. `--terminate` tears down by `Name=sg-playwright-ec2` tag.
- **DELETED** `scripts/provision_mitmproxy_ec2.py` and `tests/unit/scripts/test_provision_mitmproxy_ec2.py` — replaced by unified script above.
- Tests: `tests/unit/scripts/test_provision_ec2.py` (19 tests).
