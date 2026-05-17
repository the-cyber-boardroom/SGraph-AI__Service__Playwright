# agent-mitmproxy — Reality Index

**Domain:** `agent-mitmproxy/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** migrated from `_archive/v0.1.31/02__agent-mitmproxy-sibling.md` (v0.1.32 / v0.1.33).

The `agent_mitmproxy/` sibling package — a forward HTTP/HTTPS proxy (mitmproxy) with FastAPI admin, two duck-typed addons, and reverse-proxied web UI. Runs alongside the Playwright service on the same EC2 host. Not a Lambda — tunnels + `CONNECT` semantics don't survive the Lambda Function URL adapter.

**Canonical package:** `agent_mitmproxy/`. Image: `agent_mitmproxy/docker/images/agent_mitmproxy/`. Ports: `:8080` (proxy), `:8000` (admin API), `:8081` (mitmweb UI, localhost only — exposed via admin-API reverse proxy).

> **Post-v0.1.31 note:** BV2.12 (2026-05-05) deleted `agent_mitmproxy/` and `tests/unit/agent_mitmproxy/` and migrated the functionality to `sg_compute_specs/mitmproxy`. The route and addon surface below was authoritative at v0.1.33. **VERIFY** against `sg_compute_specs/mitmproxy/` before quoting as current.

---

## EXISTS (code-verified at v0.1.33; partial-VERIFY since BV2.12)

### What it is

- **mitmweb** on `:8080` (proxy) + `:8081` (web UI, localhost-only).
- **FastAPI admin** on `:8000` — health, CA cert retrieval, interceptor config, reverse-proxy to mitmweb UI. API-key-gated.
- Two duck-typed mitmproxy **addons**: `Default_Interceptor` (request-id + timing stamps) and `Audit_Log` (NDJSON to stdout).
- Optional **`Prometheus_Metrics`** addon emitting `sg_mitmproxy_*` series via an isolated `CollectorRegistry`.

Both processes run as siblings under `supervisord` (PID 1), which forwards signals and restarts children on crash.

---

### Package layout (`agent_mitmproxy/`)

- `__init__.py` — exposes `path = os.path.dirname(...)`.
- `version` — `v0.1.32` (independent of the Playwright service version).
- `consts/env_vars.py` — `ENV_VAR__PROXY_AUTH_{USER,PASS}` (downstream auth), `ENV_VAR__UPSTREAM_{URL,USER,PASS}` (upstream forwarding — v0.1.33), `ENV_VAR__CA_CERT_PATH`, `ENV_VAR__INTERCEPTOR_PATH`, `ENV_VAR__MITMWEB_{HOST,PORT}`, `ENV_VAR__ADMIN_API_PORT`, `ENV_VAR__API_KEY_{NAME,VALUE}`.
- `consts/paths.py` — `PATH__CA_CERT_PEM = /root/.mitmproxy/mitmproxy-ca-cert.pem`, `PATH__CURRENT_INTERCEPTOR = /app/current_interceptor.py`.
- `consts/version.py` — reads `version` file, exports `version__agent_mitmproxy`.

### Addons (`agent_mitmproxy/addons/`)

| File | Class | What it does |
|------|-------|--------------|
| `default_interceptor.py` | `Default_Interceptor` | `request()` stamps `HEADER__REQUEST_ID` (12-char hex) + `HEADER__REQUEST_TS`; `response()` echoes id, sets `HEADER__ELAPSED_MS` + `HEADER__VERSION`. Module-level `addons = [Default_Interceptor()]`. |
| `audit_log_addon.py` | `Audit_Log` | Response-hook only; NDJSON to stdout (`ts, flow_id, method, scheme, host, path, status, bytes_request, bytes_response, elapsed_ms, client_addr, proxy_user`). Decodes Basic `Proxy-Authorization` to surface the user. |
| `prometheus_metrics_addon.py` | `Prometheus_Metrics` | Duck-typed addon. `response()` records `sg_mitmproxy_flows_total / flow_duration_seconds / bytes_request_total / bytes_response_total` into `MITMPROXY_REGISTRY` (isolated `CollectorRegistry`). No mitmproxy imports at module load. |
| `addon_registry.py` | (module) | `addons = [*interceptor_addons, *audit_addons, *metrics_addons]` — loaded by mitmweb via `-s`. |

### FastAPI app (`agent_mitmproxy/fast_api/`)

- `Fast_API__Agent_Mitmproxy.py` — extends `osbot_fast_api.Fast_API`; sets `self.config.enable_api_key = True`; wires `Routes__Health`, `Routes__CA`, `Routes__Config`, `Routes__Web`.
- `app.py` — `app = Fast_API__Agent_Mitmproxy().setup().app()` — uvicorn entry point.
- `routes/Routes__Health.py` — `/health/info` (`service_name`, `service_version`, `proxy_mode`: `direct` or `upstream` derived from `ENV_VAR__UPSTREAM_URL` at request time — new v0.1.33), `/health/status` (checks: CA cert exists, interceptor script exists).
- `routes/Routes__CA.py` — `/ca/cert` (PEM bytes via `application/x-pem-file`), `/ca/info` (path, size, SHA-256 fingerprint, notBefore / notAfter from `cryptography.x509`). 503 when file missing.
- `routes/Routes__Config.py` — `/config/interceptor` (read-only current script).
- `routes/Routes__Metrics.py` — `GET /metrics`; Prometheus text exposition from `MITMPROXY_REGISTRY`. API-key-gated.
- `routes/Routes__Web.py` — reverse-proxy for mitmweb UI (internal `127.0.0.1:8081`). Async `httpx.AsyncClient` on `self.router.get('/')` + `self.router.get('/{path:path}')`. Strips `X-API-Key` + `Host` outbound; strips hop-by-hop headers (`content-length / transfer-encoding / connection / keep-alive`) on the response.

### Schemas

- `schemas/service/Schema__Agent_Mitmproxy__Info.py` — `service_name`, `service_version`, `proxy_mode: Safe_Str__Text` (new v0.1.33).
- `schemas/service/Schema__Health__Check.py` and `Schema__Health.py`.
- `schemas/ca/Schema__CA__Cert__Info.py`.
- `schemas/config/Schema__Interceptor__Source.py` — `source: Safe_Str__Text__Dangerous` (preserves newlines + `#`).

### Docker (`agent_mitmproxy/docker/`)

- `Docker__Agent_Mitmproxy__Base.py` — `IMAGE_NAME = 'agent_mitmproxy'`; extends `Type_Safe`; `setup()` wires `Create_Image_ECR`.
- `ECR__Docker__Agent_Mitmproxy.py` — `ecr_setup()` + `publish_docker_image()`; Docker Desktop `credsStore: desktop` workaround (deletes `~/.docker/config.json` on that marker).
- `images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl; `EXPOSE 8080 8000`; `CMD ["/app/entrypoint.sh"]`. Build context is the **repo root**.
- `images/agent_mitmproxy/supervisord.conf` — `[supervisord] nodaemon=true`; `[program:mitmweb]` runs `/bin/sh /tmp/run_mitmweb.sh` (wrapper script written by entrypoint — avoids supervisord `%(ENV_*)s` crash on unset vars); `[program:admin_api]` runs uvicorn. Both `autorestart=true`; logs to stdout/stderr.
- `images/agent_mitmproxy/entrypoint.sh` — seeds `/app/current_interceptor.py` from baked default if absent; builds mitmweb command conditionally (optional `--proxyauth` for downstream auth, optional `--mode upstream:{URL}` + `--set upstream_auth={USER}:{PASS}` for upstream forwarding); writes fully-resolved command to `/tmp/run_mitmweb.sh`; `exec supervisord`.
- `requirements.txt` — `mitmproxy`, `fastapi`, `uvicorn[standard]`, `httpx`, `cryptography`, `osbot-utils`, `osbot-fast-api`.

---

### API surface — 6 endpoints

All API-key-gated via `osbot_fast_api` middleware (`FAST_API__AUTH__API_KEY__{NAME,VALUE}`).

| Method | Path | What it returns |
|--------|------|-----------------|
| GET | `/health/info` | Service name + version + `proxy_mode` (direct / upstream) |
| GET | `/health/status` | `{healthy, checks[], timestamp}`; checks: `ca_cert_exists`, `interceptor_script_exists` |
| GET | `/ca/cert` | Raw PEM (`application/x-pem-file`); 503 when absent |
| GET | `/ca/info` | PEM metadata (path, size, SHA-256 fingerprint, notBefore / notAfter) |
| GET | `/config/interceptor` | Current interceptor source (read-only) |
| GET | `/ui` + `/ui/{path:path}` | Reverse-proxy to internal mitmweb UI |
| GET | `/metrics` | Prometheus text exposition (post-v0.1.33 addition) |

---

### EC2 spin-up (pre-unification)

- `scripts/provision_mitmproxy_ec2.py` — spike helper. **t3.small** box. Two ingress ports: `:8080` (proxy) + `:8000` (admin, app-layer API-key-gated). UserData installs Docker, `aws ecr get-login-password`, `docker pull`, runs container with `AGENT_MITMPROXY__PROXY_AUTH_{USER,PASS}` + `FAST_API__AUTH__API_KEY__{NAME,VALUE}`. IAM role `agent-mitmproxy-ec2-spike`; SG `agent-mitmproxy-ec2-spike`. `--terminate` tears down by tag.
- Tests: `tests/unit/scripts/test_provision_mitmproxy_ec2.py`.
- **Note (v0.1.33):** this spike script was superseded by the unified `scripts/provision_ec2.py` that brings up Playwright + sidecar together. The `provision_mitmproxy_ec2.py` and its tests were deleted in that pass.

---

### CI

See [`infra/index.md`](../infra/index.md) for the workflow details — `.github/workflows/ci__agent_mitmproxy.yml` is separate from the Playwright pipeline.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Source: [`_archive/v0.1.31/02__agent-mitmproxy-sibling.md`](../_archive/v0.1.31/02__agent-mitmproxy-sibling.md)
- Sibling: [`playwright-service/index.md`](../playwright-service/index.md)
- Infra: [`infra/index.md`](../infra/index.md) — image build + CI workflow + EC2 unified provisioner
- QA: [`qa/index.md`](../qa/index.md) — `tests/unit/agent_mitmproxy/` inventory
- SG/Compute: [`sg-compute/index.md`](../sg-compute/index.md) — `sg_compute_specs/mitmproxy/` is the post-BV2.12 home
