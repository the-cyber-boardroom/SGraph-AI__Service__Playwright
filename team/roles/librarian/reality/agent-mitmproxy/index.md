# agent-mitmproxy — Reality Index

**Domain:** `agent-mitmproxy/` | **Last updated:** 2026-05-18 | **Maintained by:** Librarian
**Code-source basis:** verified against `sg_compute_specs/mitmproxy/` at package version `v0.1.33` (post-BV2.12).

The mitmproxy sidecar: forward HTTP/HTTPS proxy with FastAPI admin, three duck-typed addons (two operational + one metrics), and reverse-proxied mitmweb UI. Runs alongside the Playwright service on the same EC2 host. Not a Lambda — tunnels and `CONNECT` semantics don't survive the Lambda Function URL adapter.

**Canonical package:** `sg_compute_specs/mitmproxy/` (since BV2.12 — 2026-05-05 — when the orphan `agent_mitmproxy/` package and `tests/unit/agent_mitmproxy/` test tree were deleted). Image: `sg_compute_specs/mitmproxy/docker/images/agent_mitmproxy/`. Ports: `:8080` (proxy), `:8000` (admin API), `:8081` (mitmweb UI, container-local — exposed via admin-API reverse proxy at `/web/*`).

---

## EXISTS (code-verified at package v0.1.33)

### What it is

- **mitmweb** on `:8080` (proxy) + `:8081` (web UI, container-local).
- **FastAPI admin** on `:8000` — health, CA cert retrieval, interceptor config, reverse-proxy to mitmweb UI, Prometheus metrics. API-key-gated (`config.enable_api_key = True`).
- Three duck-typed mitmproxy **addons**: `Default_Interceptor` (request-id + timing stamps), `Audit_Log` (NDJSON to stdout), `Prometheus_Metrics` (isolated `CollectorRegistry`).

Both processes run as siblings under `supervisord` (PID 1), which forwards signals and restarts children on crash.

---

### Package layout (`sg_compute_specs/mitmproxy/`)

- `__init__.py` — exposes `path = os.path.dirname(...)`.
- `version` — `v0.1.33` (independent of the Playwright service version).
- `manifest.py` — spec manifest entry.
- `core/consts/env_vars.py` — `ENV_VAR__PROXY_AUTH_{USER,PASS}` (downstream auth), `ENV_VAR__UPSTREAM_{URL,USER,PASS}` (upstream forwarding), `ENV_VAR__CA_CERT_PATH`, `ENV_VAR__INTERCEPTOR_PATH`, `ENV_VAR__MITMWEB_{HOST,PORT}`, `ENV_VAR__ADMIN_API_PORT`, `ENV_VAR__API_KEY_{NAME,VALUE}`.
- `core/consts/paths.py` — `PATH__CA_CERT_PEM = /root/.mitmproxy/mitmproxy-ca-cert.pem`, `PATH__CURRENT_INTERCEPTOR = /app/current_interceptor.py`.
- `core/consts/version.py` — reads `version` file, exports `version__agent_mitmproxy`.

### Addons (`sg_compute_specs/mitmproxy/core/addons/`)

| File | Class | What it does |
|------|-------|--------------|
| `default_interceptor.py` | `Default_Interceptor` | `request()` stamps `HEADER__REQUEST_ID` (12-char hex) + `HEADER__REQUEST_TS`; `response()` echoes id, sets `HEADER__ELAPSED_MS` + `HEADER__VERSION`. Module-level `addons = [Default_Interceptor()]`. |
| `audit_log_addon.py` | `Audit_Log` | Response-hook only; NDJSON to stdout (`ts, flow_id, method, scheme, host, path, status, bytes_request, bytes_response, elapsed_ms, client_addr, proxy_user`). Decodes Basic `Proxy-Authorization` to surface the user. |
| `prometheus_metrics_addon.py` | `Prometheus_Metrics` | Duck-typed addon. `response()` records `sg_mitmproxy_flows_total / flow_duration_seconds / bytes_request_total / bytes_response_total` into `MITMPROXY_REGISTRY` (isolated `CollectorRegistry`). No mitmproxy imports at module load. |
| `addon_registry.py` | (module) | `addons = [*interceptor_addons, *audit_addons, *metrics_addons]` — loaded by mitmweb via `-s`. |

### FastAPI app (`sg_compute_specs/mitmproxy/api/`)

- `Fast_API__Agent_Mitmproxy.py` — extends `osbot_fast_api.api.Fast_API`; sets `self.config.enable_api_key = True`; wires `Routes__Health`, `Routes__CA`, `Routes__Config`, `Routes__Metrics`, `Routes__Web`.
- `app.py` — `app = Fast_API__Agent_Mitmproxy().setup().app()` — uvicorn entry point.
- `routes/Routes__Health.py` — `/health/info` (`Schema__Agent_Mitmproxy__Info`: `service_name`, `service_version`, `proxy_mode` = `direct`|`upstream`), `/health/status` (checks: CA cert exists, interceptor script exists).
- `routes/Routes__CA.py` — `/ca/cert` (PEM bytes via `application/x-pem-file`), `/ca/info` (path, size, SHA-256 fingerprint, notBefore / notAfter from `cryptography.x509`). 503 when file missing.
- `routes/Routes__Config.py` — `/config/interceptor` (read-only current script).
- `routes/Routes__Metrics.py` — `GET /metrics`; Prometheus text exposition from `MITMPROXY_REGISTRY`.
- `routes/Routes__Web.py` — reverse-proxy for mitmweb UI (internal `127.0.0.1:8081`). Uses `router.api_route('/', methods=ALL_METHODS)` + `router.api_route('/{path:path}', methods=ALL_METHODS)` — **all methods, not just GET** (so flow-mutation POSTs through the UI work). Strips `Host` + `Content-Length` + `X-API-Key` outbound; strips hop-by-hop headers (`content-length / transfer-encoding / connection / keep-alive`) on the response.

### Schemas (`sg_compute_specs/mitmproxy/schemas/`)

- `service/Schema__Agent_Mitmproxy__Info.py` — `service_name`, `service_version`, `proxy_mode: Safe_Str__Text`.
- `service/Schema__Health.py` + `Schema__Health__Check.py`.
- `ca/Schema__CA__Cert__Info.py`.
- `config/Schema__Interceptor__Source.py` — `source: Safe_Str__Text__Dangerous` (preserves newlines + `#`).

### Docker (`sg_compute_specs/mitmproxy/docker/`)

- `Docker__Agent_Mitmproxy__Base.py` — `IMAGE_NAME = 'agent_mitmproxy'`; extends `Type_Safe`; `setup()` wires `Create_Image_ECR`.
- `ECR__Docker__Agent_Mitmproxy.py` — `ecr_setup()` + `publish_docker_image()`; Docker Desktop `credsStore: desktop` workaround (deletes `~/.docker/config.json` on that marker).
- `images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl; `EXPOSE 8080 8000`; `CMD ["/app/entrypoint.sh"]`. Build context is the **repo root**.
- `images/agent_mitmproxy/supervisord.conf` — `[supervisord] nodaemon=true`; `[program:mitmweb]` runs `/bin/sh /tmp/run_mitmweb.sh` (wrapper script written by entrypoint to avoid supervisord `%(ENV_*)s` crash on unset vars); `[program:admin_api]` runs uvicorn. Both `autorestart=true`; logs to stdout/stderr.
- `images/agent_mitmproxy/entrypoint.sh` — seeds `/app/current_interceptor.py` from baked default if absent; builds mitmweb command conditionally (optional `--proxyauth` for downstream auth, optional `--mode upstream:{URL}` + `--set upstream_auth={USER}:{PASS}` for upstream forwarding); writes fully-resolved command to `/tmp/run_mitmweb.sh`; `exec supervisord`.

---

### API surface — 7 routes (6 distinct paths + `/web/*` wildcard)

All API-key-gated via osbot-fast-api middleware (`FAST_API__AUTH__API_KEY__{NAME,VALUE}`).

| Method | Path | What it returns |
|--------|------|-----------------|
| GET | `/health/info` | Service name + version + `proxy_mode` (direct / upstream) |
| GET | `/health/status` | `{healthy, checks[], timestamp}`; checks: `ca_cert_exists`, `interceptor_script_exists` |
| GET | `/ca/cert` | Raw PEM (`application/x-pem-file`); 503 when absent |
| GET | `/ca/info` | PEM metadata (path, size, SHA-256 fingerprint, notBefore / notAfter) |
| GET | `/config/interceptor` | Current interceptor source (read-only) |
| GET | `/metrics` | Prometheus text exposition from `MITMPROXY_REGISTRY` |
| ANY | `/web/` + `/web/{path:path}` | Reverse-proxy to internal mitmweb UI (all HTTP verbs) |

> **Path corrections vs the v0.1.33 freeze doc:** the reverse-proxy is mounted at `/web/*` (tag `web`), not `/ui/*`, and the route accepts **all methods**, not just GET. The Prometheus `/metrics` endpoint is wired by `Routes__Metrics` (not the optional bolt-on described in the legacy doc).

---

### EC2 deployment

The standalone `scripts/provision_mitmproxy_ec2.py` no longer exists at the repo root. The sidecar now ships as part of the per-launch compose file generated by `sg_compute_specs/playwright/service/Playwright__Compose__Template.py` — set `--with-mitmproxy` on `sg-compute spec playwright create` to land the 3-container shape (host-plane + sg-playwright + agent-mitmproxy).

The placeholder file `tests/unit/scripts/test_provision_mitmproxy_ec2.py` still exists but is a single `@pytest.mark.skip` documenting that the script is PROPOSED — not implemented.

#### vault-app `--with-playwright` stack (v0.2.43)

The `sg va create --with-playwright` 4-container stack runs a **vanilla `mitmproxy/mitmproxy:latest`** image (not the custom `agent_mitmproxy` image above) as the egress proxy for the Playwright browser — see `sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py`. Playwright is pointed at it via `SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://agent-mitmproxy:8080` + `IGNORE_HTTPS_ERRORS`, so every request the browser makes (including everything reached through the vault's `/pw/*` reverse proxy) flows through mitmproxy.

The proxy runs **`mitmdump`** (NOT `mitmweb`) — `mitmdump --listen-port=8080 --set block_global=false --set termlog_verbosity=info --set flow_detail=1 --scripts=/interceptors/active.py`. No web UI; instead it streams script-load errors + one line per proxied request to **stdout**, so `docker logs vault-app-agent-mitmproxy-1` and `sg va logs --source mitmproxy` show live activity. There is no `sp vault-app open mitmweb` target and no `mitmweb_url` in `info` (both removed — they pointed at a `:8000` admin API the vanilla image never had).

As of v0.2.43 an **intercept script** can be loaded into that proxy at create time:

- `mitmdump` runs with `--scripts=/interceptors/active.py`; the host dir `/opt/vault-app/interceptors` is bind-mounted read-only.
- `Vault_App__User_Data__Builder.render_interceptor_block()` writes `active.py` to the host **before `compose up`** (a no-op stub when none is chosen).
- CLI: `sg va create --with-playwright --interceptor-script <file>` reads the local Python file and ships its source inline (`Cli__Vault_App._set_extras`).
- Resolution chain: `Schema__Vault_App__Interceptor__Choice` (`kind` ∈ {`none`, `inline`}) → `Vault_App__Interceptor__Resolver.resolve()` → source string → user-data builder. `Schema__Vault_App__Create__Request.interceptor` carries the choice.
- mitmproxy hot-reloads `active.py` on change, so a future `set-interceptor`-over-SSM command could swap the script on a running stack without a recreate (not yet implemented).

**Interceptor env vars (v0.2.43):** the agent-mitmproxy compose service has an `env_file: /opt/vault-app/interceptors/active.env` (mirrors Firefox's `env_source`/`env_file` pattern). `Vault_App__User_Data__Builder.render_interceptor_block()` always writes `active.env` (empty placeholder when none, `chmod 600`) before `compose up`, so the env_file reference always resolves. CLI: `--interceptor-env-file <file>` (dotenv) + repeatable `--interceptor-env KEY=VALUE` merge into `Schema__Vault_App__Create__Request.interceptor_env`. The interceptor script reads them via `os.environ`.

**Name prefix / tags (v0.2.43):** `--name-prefix <p>` prefixes the `Name` tag (`<p>-<stack-name>`), stamps an additive `Namespace=<p>` tag, and emits a prefixed-KEY **duplicate** of every tag (`<p>-StackType`, …) for console grouping. Originals are kept verbatim so the lifecycle filters (Purpose / StackName / StackType) and read-back values (StackEngine → podman, …) keep working. See `Vault_App__Service.apply_name_prefix`.

This vault-app path is independent of the custom-image addon registry / FastAPI admin API described above — it is plain `mitmdump` with a single `--scripts` file.

---

### CI

The standalone `.github/workflows/ci__agent_mitmproxy.yml` was **deleted in BV2.12 (2026-05-05)**. The mitmproxy package is now tested under the unified `ci-pipeline.yml` `run-unit-tests` job (which runs `pytest tests/ci/` + `pytest tests/unit/`; package tests live under `sg_compute_specs/mitmproxy/tests/` and are picked up by repository-level test discovery via pyproject + the editable install in CI).

The image is currently built/pushed via the docker helper classes (`Docker__Agent_Mitmproxy__Base` + `ECR__Docker__Agent_Mitmproxy`) but no dedicated CI job builds it — the image lives in ECR as `agent_mitmproxy` and is pulled at EC2 launch time.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sibling: [`playwright-service/index.md`](../playwright-service/index.md)
- Infra: [`infra/index.md`](../infra/index.md) — image build + CI workflow notes
- QA: [`qa/index.md`](../qa/index.md) — current `sg_compute_specs/mitmproxy/tests/` inventory
- SG/Compute: [`sg-compute/index.md`](../sg-compute/index.md) — `sg_compute_specs/mitmproxy/` is now a spec sibling of `playwright/`
