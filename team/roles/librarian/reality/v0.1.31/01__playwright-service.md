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

## Service classes — 10 of 10 live

Unchanged from v0.1.24.

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

Unchanged from v0.1.24.

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

## EC2 spike (v0.1.31)

- `scripts/provision_ec2.py` — throwaway EC2 spin-up to reproduce Firefox/WebKit-on-Lambda hangs on a t3.large AL2023 host. IAM role `sg-playwright-ec2-spike` + matching instance profile (attaches `AmazonEC2ContainerRegistryReadOnly` + `AmazonSSMManagedInstanceCore`). SG `playwright-ec2-spike` (no `sg-` prefix — AWS reserves that for SG IDs). UserData installs Docker, `aws ecr get-login-password`, `docker pull`, and runs the container on `:8000` with `FAST_API__AUTH__API_KEY__*` + `SG_PLAYWRIGHT__DEPLOYMENT_TARGET=container` + `SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000`. `--terminate` tears down any instance tagged `Name=sg-playwright-ec2-spike`.
- Tests: `tests/unit/scripts/test_provision_ec2.py`.
