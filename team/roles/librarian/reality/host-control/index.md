# host-control — Reality Index

**Domain:** `host-control/` | **Last updated:** 2026-05-02 | **Maintained by:** Librarian (daily run)

The Host Control Plane is a small FastAPI service that runs **inside each ephemeral EC2 instance**. It exposes a uniform HTTP surface for managing the containers, shell access, and OS-level metrics on that host — the SP CLI control plane (`Fast_API__SP__CLI`) and the dashboard talk to this service over the network.

Package: `sgraph_ai_service_playwright__host/`. Image: `docker/host-control/`. Listens on port 8000 inside the container; mapped to host port **9000**.

---

## EXISTS (code-verified)

### HTTP surface — 9 endpoints

`Fast_API__Host__Control` (`sgraph_ai_service_playwright__host/fast_api/Fast_API__Host__Control.py:17-20`) wires three route classes:

#### Containers (`/containers/*`) — 6 endpoints

| Method | Path | What it does | Source |
|--------|------|---------------|--------|
| GET | `/containers/list` | List containers on the host. | `Routes__Host__Containers.list_containers` |
| POST | `/containers` | Start a container. Body: `Schema__Container__Start__Request`. | `Routes__Host__Containers.start_container` |
| GET | `/containers/{name}` | Container info. 404 on miss. | `Routes__Host__Containers.get_container` |
| GET | `/containers/{name}/logs` | Tail logs (default 100 lines). | `Routes__Host__Containers.get_logs` |
| POST | `/containers/{name}/stop` | Stop a container. | `Routes__Host__Containers.stop_container` |
| DELETE | `/containers/{name}` | Remove a container. | `Routes__Host__Containers.remove_container` |

All endpoints are **pure delegation** to the runtime returned by `get_container_runtime()`. Routes have no logic.

File: `sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Containers.py:23-58`.

#### Shell (`/shell/*`) — 2 endpoints

| Method | Path | What it does | Source |
|--------|------|---------------|--------|
| POST | `/shell/execute` | Execute one command. Allowlist-gated at schema level via `Safe_Str__Shell__Command`. | `Routes__Host__Shell.execute` |
| WS | `/shell/stream` | Interactive PTY over WebSocket. Spawns `/bin/rbash` (the security boundary) and streams bytes both ways. | `Routes__Host__Shell.shell_stream` |

The WebSocket path bypasses the allowlist because `rbash` itself is the boundary.

File: `sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Shell.py:23-66`.

#### Status (`/host/*`) — 2 endpoints

| Method | Path | What it does | Source |
|--------|------|---------------|--------|
| GET | `/host/status` | CPU %, RAM (MB used/total), disk (GB used/total), uptime, container count. Falls back to zeros if `psutil` is unavailable. | `Routes__Host__Status.status` |
| GET | `/host/runtime` | Detected runtime: `'docker'` \| `'podman'` \| `'none'` plus the version string. Picks docker first, then podman. | `Routes__Host__Status.runtime` |

File: `sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Status.py:18-66`.

### Service classes

| Class | File | Role |
|-------|------|------|
| `Container__Runtime` | `containers/service/Container__Runtime.py` | Abstract base: `list / start / info / logs / stop / remove`. |
| `Container__Runtime__Docker` | `containers/service/Container__Runtime__Docker.py` | `subprocess` adapter over the `docker` CLI. |
| `Container__Runtime__Podman` | `containers/service/Container__Runtime__Podman.py` | `subprocess` adapter over the `podman` CLI. |
| `Container__Runtime__Factory` | `containers/service/Container__Runtime__Factory.py` | `get_container_runtime()` — picks docker > podman via `shutil.which`. |
| `Shell__Executor` | `shell/service/Shell__Executor.py` | Timeout-enforced subprocess wrapper for `/shell/execute`. Double-checks the allowlist at execution time. |

### Schemas

| File | Class | Used by |
|------|-------|---------|
| `containers/schemas/Schema__Container__Info.py` | `Schema__Container__Info` | GET `/containers/{name}` |
| `containers/schemas/Schema__Container__List.py` | `Schema__Container__List` | GET `/containers/list` |
| `containers/schemas/Schema__Container__Logs__Response.py` | `Schema__Container__Logs__Response` | GET `/containers/{name}/logs` |
| `containers/schemas/Schema__Container__Start__Request.py` | `Schema__Container__Start__Request` | POST `/containers` |
| `containers/schemas/Schema__Container__Start__Response.py` | `Schema__Container__Start__Response` | POST `/containers` (response) |
| `containers/schemas/Schema__Container__Stop__Response.py` | `Schema__Container__Stop__Response` | POST `/containers/{name}/stop`, DELETE `/containers/{name}` |
| `shell/schemas/Schema__Shell__Execute__Request.py` | `Schema__Shell__Execute__Request` | POST `/shell/execute` |
| `shell/schemas/Schema__Shell__Execute__Response.py` | `Schema__Shell__Execute__Response` | POST `/shell/execute` (response) |
| `host/schemas/Schema__Host__Status.py` | `Schema__Host__Status` | GET `/host/status` |
| `host/schemas/Schema__Host__Runtime.py` | `Schema__Host__Runtime` | GET `/host/runtime` |

### Primitives

| File | Class | Purpose |
|------|-------|---------|
| `shell/primitives/Safe_Str__Shell__Command.py` | `Safe_Str__Shell__Command` | Allowlist-gated command primitive. Rejects anything not in `SHELL_COMMAND_ALLOWLIST`. |

### Allowlist

`shell/shell_command_allowlist.py` — `SHELL_COMMAND_ALLOWLIST: list[str]` (deny-all default):

```
docker ps, docker logs, docker stats, docker inspect,
podman ps, podman logs, podman stats, podman inspect,
df -h, free -m, uptime, uname -r,
cat /proc/meminfo, cat /proc/cpuinfo,
systemctl status
```

The allowlist is **shared** between `Safe_Str__Shell__Command` (schema-level rejection) and `Shell__Executor` (runtime double-check). New entries widen the gate — Architect / AppSec sign-off required.

### Boot wiring (consumed by SP CLI)

`Schema__Ec2__Instance__Info` (in `sgraph_ai_service_playwright__cli/ec2/schemas/Schema__Ec2__Instance__Info.py:36-37`) carries:

- `host_api_url` — `http://{public_ip}:9000` (empty until boot completes)
- `host_api_key_vault_path` — `/ec2/{deploy_name}/host-api-key` (empty until provisioned)

`Ec2__Service.build_instance_info()` (`sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py:145-146`) populates both fields from the instance's public IP and deploy name.

`Ec2__Service.USER_DATA_TEMPLATE` includes a host-control plane install + run block that pulls the host-control image and runs it on `:9000` with the API key injected via env var.

### Image

`docker/host-control/Dockerfile` — Python 3.12 Alpine + `uvicorn`. Entrypoint: `uvicorn sgraph_ai_service_playwright__host.fast_api.lambda_handler:_app --host 0.0.0.0 --port 8000`. The `lambda_handler.py` carries a Mangum wrapper for local-test parity even though the host service does not actually run on Lambda.

`docker/host-control/requirements.txt` — minimal: FastAPI, uvicorn, osbot-utils, osbot-fast-api, optional psutil. No Chromium, no Playwright, no AWS SDK.

### Tests

| File | Test count |
|------|-----------|
| `tests/unit/sgraph_ai_service_playwright__host/containers/test_Container__Runtime__Docker.py` | (subset of 31) |
| `tests/unit/sgraph_ai_service_playwright__host/shell/test_Shell__Executor.py` | (subset of 31) |
| `tests/unit/sgraph_ai_service_playwright__host/fast_api/test_Fast_API__Host__Control.py` | (subset of 31) — 9 FastAPI integration tests skip when `osbot_fast_api_serverless` is absent |

Total host-control test functions: **31** (verified by `grep -c "def test_"`). Full suite at the introducing commit: **1653 unit tests pass**.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## Cross-references

- **Source brief:** [`team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__container-runtime-abstraction.md`](../../../humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__container-runtime-abstraction.md)
- **Introducing commit:** `11c2a08` — `feat: add sgraph_ai_service_playwright__host — Host Control Plane (Tasks 1–6)` (2026-05-02)
- **CLI counterpart (consumer):** [`cli/index.md`](../cli/index.md) — `Ec2__Service` populates `host_api_url` / `host_api_key_vault_path` for every EC2 instance.
- **Infra counterpart:** [`infra/index.md`](../infra/index.md) — `docker/host-control/` Dockerfile + EC2 USER_DATA template.
- **Security counterpart:** [`security/index.md`](../security/index.md) — `SHELL_COMMAND_ALLOWLIST` lives here in spirit, alongside the JS allowlist for `Step__Executor`.
- **UI counterpart (PROPOSED):** [`ui/index.md`](../ui/index.md) — the dashboard's `sp-cli-host-control` family is not yet built.
