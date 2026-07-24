# playwright-service — Reality Index

**Domain:** `playwright-service/` | **Last updated:** 2026-07-03 | **Maintained by:** Librarian
**Code-source basis:** verified against `sg_compute_specs/playwright/` at v0.2.28 (post-BV2.11 / post-FV2.6); endpoint-surface re-verified against `sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py:103-113` at v0.2.63 (2026-06-23, D1 fix — see changelog).

The core FastAPI service: browser automation routes, the Type_Safe schema tree, the `Step__Executor` (sole owner of `page.*`), `Browser__Launcher`, `Sequence__Runner`, and the agentic admin / boot scaffolding layered on top.

**Canonical package:** `sg_compute_specs/playwright/core/`. Image base: `mcr.microsoft.com/playwright/python:v1.58.0-noble`. Image ships as **`diniscruz/sg-playwright`** on Docker Hub (post-v0.2.11 — the Lambda / ECR / S3-zip route was retired). Lambda handler stub (kept for parity, not in the live deployment path): `sg_compute_specs/playwright/core/fast_api/lambda_handler.py`.

The orphan `sgraph_ai_service_playwright/` package was **deleted in BV2.11 (2026-05-05)** and is not coming back. All paths below resolve to `sg_compute_specs/playwright/` (and `sg_compute_specs/playwright/core/` for runtime modules) only.

---

## EXISTS (code-verified at v0.2.28)

### API surface — 23 direct endpoints

Wired by `Fast_API__Playwright__Service.setup_routes()` (`sg_compute_specs/playwright/core/fast_api/Fast_API__Playwright__Service.py`). Ten in-repo route classes (`Routes__Index`, `Routes__Health`, `Routes__Browser`, `Routes__Sequence`, `Routes__Screenshot`, `Routes__Inspect`, `Routes__Session`, `Routes__Desktop`, `Routes__Metrics`, `Routes__Test_Pages`) plus `Routes__Set_Cookie` imported from `osbot_fast_api.api.routes.Routes__Set_Cookie`.

> **sg-playwright-vnc slice (2026-07-09).** 22 → **23** with `POST /desktop/browser` (`Routes__Desktop` → `Desktop__Browser__Manager`): opens a long-lived HEADED browser as a real session (composition over `session_open` + a NAVIGATE `session_act` — no new `page.*` caller) so the returned `session_id` drives the SAME browser a human watches in noVNC. Guarded: 400 unless `SG_PLAYWRIGHT__DISPLAY_MODE=vnc` (`Enum__Display__Mode`; the base image is headless — no X server). The **`diniscruz/sg-playwright-vnc`** image variant (`sg_compute_specs/playwright/vnc/`: Dockerfile `ARG BASE_IMAGE`, supervisord running xvfb/openbox/x11vnc/novnc/fastapi + an `autostart-browser.sh` oneshot reading `SG_PLAYWRIGHT__AUTOSTART_BROWSER`/`AUTOSTART_START_URL`) exposes the desktop on `:6080` (raw VNC `:5900` is `-localhost`). `Browser__Launcher` gained `DEFAULT_LAUNCH_ARGS__HEADED` (no `--single-process`, + `--start-maximized`) picked when `headless=false` and no caller args. CI builds/tests/publishes it beside the base image (`build-vnc-*`, `integration-test-vnc-image`, `push-vnc-manifest` in `ci-pipeline.yml`). Consumed by content_proxy's `cp-browser-{i}` fleet (see `../content-proxy/index.md`).

> **Iteration-2 addition (2026-06-23).** `Routes__Test_Pages` (`GET /test-pages/{name}`) was wired at `Fast_API__Playwright__Service.py:115`, taking the route family count from 21 to **22** (the one parameterised route served five fixed names at the time: `simple`, `form`, `dynamic`, `links`, `slow`). The concrete paths are appended to `AUTH__EXCLUDED_PATHS` in `setup()` (`Fast_API__Playwright__Service.py:58-60`) so the server-side browser fetches them keyless. See the Test-Pages sub-section below.

> **set_cookie slice (2026-07-03).** The step vocabulary grew 24 → **25** with `set_cookie` (`Enum__Step__Action.SET_COOKIE`, `Schema__Step__Set_Cookie`) — sets a cookie on the per-request BrowserContext, STATELESS (fresh context per request, discarded after; a "reload" is a second `navigate` in the same request). Execution stays inside the single-owner boundary: `Step__Executor.execute_set_cookie` passes `page.context` to `Credentials__Loader.add_cookie` (the only `context.add_cookies` caller). The url-vs-domain cross-field rule (`exactly one of url / domain`, `path` defaults `/`) lives in `Request__Validator.validate_step`. The fixture list grew to **six** with `/test-pages/cookies`, and the console gained the S6 gallery example + "needs egress" chips on W1–W9 (F6).

> **D1 corrected (2026-06-23).** The previous text said "16 direct endpoints" and claimed `Routes__Session` was removed in v0.1.24. That is **stale**: the code wires both `Routes__Inspect` (`Fast_API__Playwright__Service.py:110`, `POST /inspect`) and `Routes__Session` (`:111`, the four `/session/*` routes). Counting them gives **21** direct endpoints. The "removed" claim was a regression in the doc, not the code. See the Inspect (1) + Session (4) sub-sections below.

#### Health (3) — `Routes__Health`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health/info` | Service identity (`Schema__Service__Info`) |
| GET | `/health/status` | Liveness (`Schema__Health`) — `healthy` aggregates **gating** checks only (see F1 note) |
| GET | `/health/capabilities` | Declared capabilities (`Schema__Service__Capabilities`) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Health.py:31-43`.

> **F1 health-semantics fix (2026-07-03).** `/health/status` used to compute `healthy = all(checks)` where one check was vault connectivity (`bool(SG_SEND_BASE_URL)`) — every deployment without the vault env var (laptop, plain `docker run`) reported unhealthy forever and the console badge showed `degraded`. Vault reachability is a **capability** (already surfaced as `capabilities.has_vault_access`), not liveness. Now:
> - `Schema__Health__Check` carries `gating : bool = True` (`sg_compute_specs/playwright/core/schemas/service/Schema__Health__Check.py:14`). Gating checks AND into `Schema__Health.healthy`; informational (`gating=False`) checks stay in the `checks` list with their detail but never flip the aggregate. Wire shape stays backward-compatible (`healthy` bool + `checks` list; each check gains the `gating` field).
> - `connectivity` is informational: `Capability__Detector.connectivity_check()` sets `gating=False` (`sg_compute_specs/playwright/core/service/Capability__Detector.py:200-206`). Aggregation: `Playwright__Service.get_health()` — `all(c.healthy for c in checks if c.gating)` (`sg_compute_specs/playwright/core/service/Playwright__Service.py:121-126`).
> - **Chromium version probe rewritten** (`chromium 0.0.0` fix, same F1): the old probe opened `sync_playwright()` inside the running service — under uvicorn's asyncio loop the sync API raises, so it always fell into the `0.0.0` fallback. `detect_chromium_version()` now reads the pip package's bundled driver metadata `playwright/driver/package/browsers.json` (`chromium` → `browserVersion`, e.g. `148.0.7778.96`) with a path-segment fallback on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`, then `0.0.0` (`Capability__Detector.py:153-184`). No browser launch, no subprocess — pure file read.
> - New primitive `Safe_Str__Version__Browser` (`sg_compute_specs/playwright/core/schemas/primitives/text/Safe_Str__Version__Browser.py`) — osbot's `Safe_Str__Version` caps at 3 segments × 3 digits (max 12 chars) and can never hold a real Chrome version, a third contributing cause of the permanent `0.0.0`. `Schema__Service__Info.chromium_version` now uses it.
> - CI image gate: `tests/integration_live/test_99_ui_console.py::test_6__console_renders_in_image_browser` (F4.2) makes the image's own Chromium render `GET /` from inside the container (`http://localhost:8000/`, API key planted as a cookie via the `set_cookie` step) and asserts via `get_dom_tree` that `#builder` is visible with a non-zero rect — catches the empty-shell console regression the HTML-substring check (test_2) cannot see.

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
| POST | `/sequence/execute` | Layer-3 multi-step declarative sequence (25-verb step language incl. `set_cookie` — per-request-context cookie, stateless) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Sequence.py:27-31`.

#### Inspect (1) — `Routes__Inspect`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/inspect` | Φ5 snapshot-once-probe-many read-only batch (`Schema__Inspect__Request` → `Schema__Inspect__Response`) |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Inspect.py:23,:39` (`ROUTES_PATHS__INSPECT = ['/inspect']`). Wired at `Fast_API__Playwright__Service.py:110`.

#### Session (4) — `Routes__Session`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/session/open` | Open a stateful session handle → `session_id` + `expires_in_ms` |
| POST | `/session/{session_id}/act` | Run a sequence-shape body on the held session → `Schema__Sequence__Response` |
| POST | `/session/{session_id}/probe` | Run an inspect-shape body (no navigate) → `Schema__Inspect__Response` |
| POST | `/session/{session_id}/close` | Release the session → `{closed: true}` |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Session.py:27-30,:58-61` (`ROUTES_PATHS__SESSION`). Wired at `Fast_API__Playwright__Service.py:111` (Φ7 — opt-in stateful session handles; available when `capabilities.supports_persistent`).

#### Metrics (1) — `Routes__Metrics` (mounted at root, prefix `/`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/metrics` | Prometheus text exposition (`text/plain`). Module-level `_REGISTRY` in `metrics/Metrics__Collector.py`. |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Metrics.py:24-33`.

#### Index (1) — `Routes__Index` (mounted at root, prefix `/`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Capability-driven, agent-native **console** (HTML) — 8 endpoint-family tabs, the 25-verb sequence builder, `/inspect` + `/session/*` + `/browser/*` + PDF + DOM/a11y/text/html surfaces, workflow import/export + the S1–S6 (self-contained `/test-pages/*` fixtures; S6 = set_cookie → reload → screenshot against `/test-pages/cookies`) **and** W1–W9 example gallery (every W entry carries `egress:true` and renders a "needs egress" chip — external URLs fail on egress-restricted deployments, F6), in-app docs generated from the live capability surface, and an in-page agentic `window.__tool`. Iterations 2–5 added: a **light** work-pane theme (header + tab rail stay dark); an `<sg-layout>` panel shell hosting **four** panes — Builder \| (Output over Examples) with a Console dock — via the documented `tag`-instantiation pattern (tiny `sg-pane-*` host elements relocate the pre-built pane content from `#pane-store`; the layout does NOT project existing nodes via `slot=`). Imported from `https://tools.sgraph.ai/core/sg-layout/v0.1.0/` (dev-host fallback), tree persisted to `localStorage['sg-playwright:console:layout:v3']` via the internal `events.on('layout:changed')` bus, plain-CSS-grid fallback + verify-or-revert guard when the component is absent or fails to mount, header "⟲ Layout" reset. Execution output lives in its own **Output** pane, focused via `focusPanel('output')` on every Execute. Also: a framed screenshot viewer with Download + Open-in-new-tab (single/batch/per-step — per-step artefact matching is case-insensitive on the enum VALUE `screenshot`); collapsible step-builder cards (click the `.step-head`); a `copyText` clipboard helper that survives insecure origins (`http://0.0.0.0`); and a bottom-dock `window.__tool` REPL console. Root_path-aware (`window.API_BASE`) so it works identically behind `/pw` and at root. Rebuilt from the two-tab screenshot toy in the v0.2.64 console effort (commits `9fe5917`, `f4c84ec`, `c27b8da`, `512da60`, `d562403`, `b539e2c`); set_cookie slice added S6 + the F6 egress chips. |

Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` (`INDEX_HTML` + the per-request `__API_BASE__` injection; the example gallery is `const GALLERY = [...]` and the verb table is `const VERBS = {...}`, both code-verified against `Enum__Step__Action` by `tests/unit/fast_api/routes/test_Routes__Index__verb_table_drift.py` and `test_Workflows__Gallery__Bodies.py`).

#### Set-Cookie (2) — `osbot_fast_api.api.routes.Routes__Set_Cookie`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/auth/set-cookie-form` | HTML UI for setting the auth cookie |
| POST | `/auth/set-auth-cookie` | Cookie write |

Both paths sit in `AUTH__EXCLUDED_PATHS` so they bypass the API-key middleware.

#### Test-Pages (1 route, 6 names) — `Routes__Test_Pages`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/test-pages/{name}` | Deterministic, self-contained HTML fixtures served BY this service for the console's S-series examples (Decision #5). `name` ∈ `{simple, form, dynamic, links, slow, cookies}` with stable element ids (`#username`/`#password`/`#submit`/`#welcome`, `#ready`, `#bottom`, `#loaded`, …). `cookies` renders `document.cookie` into `#cookie-list` (one `li#cookie-<name>` per cookie) with `#has-cookies` / `#no-cookies` banners — the S6 / set_cookie target (the demo cookie must not be HttpOnly: HttpOnly is invisible to `document.cookie`). Unknown names return a 404 with the reflected name **HTML-escaped** (no reflected-XSS) — note: when an API key is configured the middleware 401s unknown names BEFORE the 404 branch, because only the six known paths are auth-excluded (exact-match list; F5, accepted). |

The six concrete `/test-pages/{name}` paths are appended to `AUTH__EXCLUDED_PATHS` in `Fast_API__Playwright__Service.setup()` (`:58-60`) — the same mechanism that exempts `/auth/set-cookie-form` — so the server-side browser reaches them without an API key. The middleware matches `request.url.path` exactly, so the names are enumerated (`TEST_PAGE_NAMES`) rather than prefix-matched. Source: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Test_Pages.py`; tests: `tests/unit/fast_api/routes/test_Routes__Test_Pages.py`.

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

> **Historical (corrected 2026-06-23):** `Routes__Quick` was removed in v0.1.24 — `/quick/*` was absorbed into the stateless `/browser/*` surface. `Routes__Session` was **also** briefly removed in v0.1.24 but has since been **re-introduced** — the code now wires it at `Fast_API__Playwright__Service.py:111` (the four `/session/*` routes above). The earlier blanket "sessions are no longer a wire-visible resource" statement is **no longer true**; sessions are wire-visible again behind the `supports_persistent` capability. D1 was the stale residue of that removal claim.

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
| `JS__Expression__Allowlist` | `JS__Expression__Allowlist.py` | Deny-all default for the `evaluate` action (+ `wait_for.function`). `is_enabled()` reports whether ANY user JS can run. |
| `JS__Expression__Allowlist__Loader` | `JS__Expression__Allowlist__Loader.py` | Builds the boot-time script policy from env — `SG_PLAYWRIGHT__JS_ALLOW_ALL` (bypass) and `SG_PLAYWRIGHT__JS_ALLOWLIST_FILE` (curated exact-match list). **Both default OFF → deny-all preserved.** Applied to the main runner's validator in `Playwright__Service.setup()`; the `/screenshot` runner keeps its own separate `allow_all` validator. Surfaced as `Schema__Service__Capabilities.js_evaluate_enabled`. See `library/guides/v0.2.64__enabling-script-execution.md`. |
| `Credentials__Loader` | `Credentials__Loader.py` | Vault-side credentials hydration. Also the ONLY `context.add_cookies` caller — the `set_cookie` verb lands here via `add_cookie(context, step)` (stateless: per-request context only). |
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

- **Dev:** `https://dev.playwright.sgraph.ai/` — CloudFront in front of the Docker Hub image (post v0.2.11 the Lambda Function URL is gone). `/admin/*` reachable alongside the 21 direct public endpoints.

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
