# Agent Mitmproxy — Reality (v0.1.32 — sibling package)

NEW in v0.1.32. Lives at the repo root as a sibling to `sgraph_ai_service_playwright/`. Not a Lambda — runs on EC2 (tunnels + `CONNECT` semantics don't survive the Lambda Function URL adapter).

See [README.md](README.md) for the index and split rationale.

---

## What it is

A forward HTTP/HTTPS proxy (mitmproxy) with:

- **mitmweb** on `:8080` (proxy) + `:8081` (web UI, localhost-only).
- **FastAPI admin** on `:8000` — health, CA cert retrieval, interceptor config, reverse-proxy to the mitmweb UI. API-key-gated.
- Two duck-typed mitmproxy **addons**: `Default_Interceptor` (request-id + timing stamps) and `Audit_Log` (NDJSON to stdout).

Both processes run as siblings under `supervisord` (PID 1), which forwards signals and restarts children on crash.

---

## Package layout (`agent_mitmproxy/`)

- `__init__.py` — exposes `path = os.path.dirname(os.path.abspath(__file__))`.
- `version` — `v0.1.32` (independent of the Playwright service version).
- `consts/`
  - `env_vars.py` — `ENV_VAR__PROXY_AUTH_{USER,PASS}`, `ENV_VAR__CA_CERT_PATH`, `ENV_VAR__INTERCEPTOR_PATH`, `ENV_VAR__MITMWEB_{HOST,PORT}`, `ENV_VAR__ADMIN_API_PORT`, `ENV_VAR__API_KEY_{NAME,VALUE}`.
  - `paths.py` — `PATH__CA_CERT_PEM = /root/.mitmproxy/mitmproxy-ca-cert.pem`, `PATH__CURRENT_INTERCEPTOR = /app/current_interceptor.py`.
  - `version.py` — reads `version` file, exports `version__agent_mitmproxy`.
- `addons/`
  - `default_interceptor.py` — `Default_Interceptor`; `request()` stamps `HEADER__REQUEST_ID` (12-char hex) + `HEADER__REQUEST_TS`; `response()` echoes id, sets `HEADER__ELAPSED_MS` + `HEADER__VERSION`. Module-level `addons = [Default_Interceptor()]`.
  - `audit_log_addon.py` — `Audit_Log`; response-hook only; emits NDJSON to stdout (keys: `ts, flow_id, method, scheme, host, path, status, bytes_request, bytes_response, elapsed_ms, client_addr, proxy_user`). Decodes Basic `Proxy-Authorization` to surface the user.
  - `addon_registry.py` — `addons = [*interceptor_addons, *audit_addons]` — loaded by mitmweb via `-s`.
- `fast_api/`
  - `Fast_API__Agent_Mitmproxy.py` — extends `osbot_fast_api.Fast_API`; sets `self.config.enable_api_key = True` then wires `Routes__Health`, `Routes__CA`, `Routes__Config`, `Routes__Web`.
  - `app.py` — `app = Fast_API__Agent_Mitmproxy().setup().app()` — what uvicorn imports.
  - `routes/Routes__Health.py` — `/health/info` (`service_name`, `service_version`), `/health/status` (checks: CA cert exists, interceptor script exists).
  - `routes/Routes__CA.py` — `/ca/cert` (PEM bytes via `Response(..., media_type='application/x-pem-file')`), `/ca/info` (path, size, SHA-256 fingerprint, notBefore / notAfter from `cryptography.x509`). 503 when file missing.
  - `routes/Routes__Config.py` — `/config/interceptor` (read-only current script).
  - `routes/Routes__Web.py` — reverse-proxy for the mitmweb UI (internal `127.0.0.1:8081`). Async `httpx.AsyncClient` on `self.router.get('/')` + `self.router.get('/{path:path}')`. Strips `X-API-Key` + `Host` on the outbound call; strips `content-length` / `transfer-encoding` / `connection` / `keep-alive` on the response.
- `schemas/` — one class per file, `Type_Safe` only.
  - `service/Schema__Agent_Mitmproxy__Info.py`
  - `service/Schema__Health__Check.py`
  - `service/Schema__Health.py`
  - `ca/Schema__CA__Cert__Info.py`
  - `config/Schema__Interceptor__Source.py` — `source: Safe_Str__Text__Dangerous` (preserves newlines + `#`).
- `docker/`
  - `Docker__Agent_Mitmproxy__Base.py` — `IMAGE_NAME = 'agent_mitmproxy'`; extends `Type_Safe`; `setup()` wires `Create_Image_ECR` against this package's docker context.
  - `ECR__Docker__Agent_Mitmproxy.py` — `ecr_setup()` + `publish_docker_image()`; Docker Desktop `credsStore: desktop` workaround (deletes `~/.docker/config.json` when it carries that marker).
  - `images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl; `WORKDIR /app`; copies `agent_mitmproxy/` + supervisord.conf + entrypoint.sh; `EXPOSE 8080 8000`; `CMD ["/app/entrypoint.sh"]`. Build context is the **repo root** (`docker build -f agent_mitmproxy/docker/images/agent_mitmproxy/dockerfile .`).
  - `images/agent_mitmproxy/supervisord.conf` — `[supervisord] nodaemon=true`; `[program:mitmweb]` runs `mitmweb --proxyauth "${USER}:${PASS}" --web-host 127.0.0.1 --web-port 8081 --listen-port 8080 --set block_global=false --set confdir=/root/.mitmproxy -s /app/agent_mitmproxy/addons/addon_registry.py`; `[program:admin_api]` runs `uvicorn agent_mitmproxy.fast_api.app:app --host 0.0.0.0 --port 8000`. Both `autorestart=true`; logs to stdout/stderr.
  - `images/agent_mitmproxy/entrypoint.sh` — seeds `/app/current_interceptor.py` from the baked default if absent, then `exec supervisord`.
- `requirements.txt` — `mitmproxy`, `fastapi`, `uvicorn[standard]`, `httpx`, `cryptography`, `osbot-utils`, `osbot-fast-api`.

---

## API surface — 6 endpoints

All API-key-gated via `osbot_fast_api` middleware (`FAST_API__AUTH__API_KEY__{NAME,VALUE}`).

- `GET /health/info`                 — service name + version.
- `GET /health/status`               — `{healthy, checks[], timestamp}`; checks: `ca_cert_exists`, `interceptor_script_exists`.
- `GET /ca/cert`                     — raw PEM (`application/x-pem-file`); 503 when absent.
- `GET /ca/info`                     — PEM metadata (path, size, SHA-256 fingerprint, notBefore / notAfter).
- `GET /config/interceptor`          — current interceptor source (read-only).
- `GET /ui` + `GET /ui/{path:path}`  — reverse-proxy to internal mitmweb UI (`127.0.0.1:8081`).

---

## EC2 spin-up

- `scripts/provision_mitmproxy_ec2.py` — spike helper, mirrors `scripts/provision_ec2.py`. Smaller box: `t3.small`. Two ingress ports: `:8080` (proxy) + `:8000` (admin, app-layer API-key-gated). UserData installs Docker, `aws ecr get-login-password`, `docker pull`, runs the container with `AGENT_MITMPROXY__PROXY_AUTH_{USER,PASS}` + `FAST_API__AUTH__API_KEY__{NAME,VALUE}`. IAM role `agent-mitmproxy-ec2-spike` (attaches `AmazonEC2ContainerRegistryReadOnly` + `AmazonSSMManagedInstanceCore`). SG `agent-mitmproxy-ec2-spike`. `--terminate` tears down by `Name=agent-mitmproxy-ec2-spike` tag.
- Tests: `tests/unit/scripts/test_provision_mitmproxy_ec2.py`.

---

## CI

See [`03__docker-and-ci.md`](03__docker-and-ci.md) for the workflow details.
