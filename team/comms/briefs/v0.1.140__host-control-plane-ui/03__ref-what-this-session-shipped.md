# Reference — What This Session Shipped

**date** 02 May 2026  
**branch** `claude/continue-playwright-refactor-xbI4j`  
**commits** 11c2a08 (host package) · 592dbc8 (caller_ip fix)

This is the canonical "what exists today" reference for the UI session. Cross-check against the reality doc before assuming anything.

---

## New package: `sgraph_ai_service_playwright__host`

Installed on each EC2 host. NOT deployed to Lambda. NOT imported by the SP CLI management plane.

### Container schemas (all in `containers/schemas/`)

| Schema | Key fields |
|--------|-----------|
| `Schema__Container__Info` | `name, image, status, state, ports, created_at, type_id` |
| `Schema__Container__List` | `containers: List__Schema__Container__Info, count: int` |
| `Schema__Container__Start__Request` | `name, image, ports, env, type_id` |
| `Schema__Container__Start__Response` | `name, container_id, started: bool, error` |
| `Schema__Container__Logs__Response` | `name, logs, tail` |
| `Schema__Container__Stop__Response` | `name, stopped: bool, removed: bool, error` |

### Shell (in `shell/`)

| File | What it does |
|------|-------------|
| `shell_command_allowlist.py` | `SHELL_COMMAND_ALLOWLIST` constant — 15 allowed prefixes |
| `primitives/Safe_Str__Shell__Command` | Validates against allowlist at construction time; allow_empty=True for Type_Safe defaults, validated at execute time |
| `schemas/Schema__Shell__Execute__Request` | `command: Safe_Str__Shell__Command, timeout: int = 30, working_dir: str` |
| `schemas/Schema__Shell__Execute__Response` | `stdout, stderr, exit_code, duration, timed_out` |
| `service/Shell__Executor` | Runs command via `subprocess.run`, enforces max 120s timeout |

### Host schemas (in `host/schemas/`)

| Schema | Key fields |
|--------|-----------|
| `Schema__Host__Status` | `cpu_percent, mem_total_mb, mem_used_mb, disk_total_gb, disk_used_gb, uptime_seconds, container_count` |
| `Schema__Host__Runtime` | `runtime: str (docker\|podman), version: str` |

### Container runtime (in `containers/service/`)

| Class | What it does |
|-------|-------------|
| `Container__Runtime` | Abstract base |
| `Container__Runtime__Docker` | subprocess `docker` CLI adapter |
| `Container__Runtime__Podman` | subprocess `podman` CLI adapter |
| `Container__Runtime__Factory` | `get_container_runtime()` — picks Docker > Podman via `shutil.which` |

### FastAPI (in `fast_api/`)

| Class | What it does |
|-------|-------------|
| `Routes__Host__Containers` | tag=`containers`; GET /containers/list, POST /containers, GET/DELETE /containers/{name}, GET /containers/{name}/logs, POST /containers/{name}/stop |
| `Routes__Host__Shell` | tag=`host`; POST /host/shell/execute, WS /host/shell/stream |
| `Routes__Host__Status` | tag=`host`; GET /host/status, GET /host/runtime |
| `Fast_API__Host__Control` | Serverless__Fast_API subclass, wires all three route sets |
| `lambda_handler.py` | `_app` export for uvicorn; Mangum wrapper optional |

---

## SP CLI changes

### `Schema__Ec2__Instance__Info` (gained 2 fields)

```python
host_api_url            : Safe_Str__Text   # "http://{public_ip}:9000" — empty until boot
host_api_key_vault_path : Safe_Str__Text   # "/ec2/{deploy_name}/host-api-key"
```

### `Ec2__Service.build_instance_info()` (populates both new fields)

```python
host_api_url            = f'http://{ip}:9000'                                  if ip else '',
host_api_key_vault_path = f'/ec2/{instance_deploy_name(details)}/host-api-key' if deploy_name else '',
```

### **NOT YET DONE: `Schema__Stack__Summary`**

`Schema__Stack__Summary` (returned by `/catalog/stacks`, carried by `sp-cli:stack.selected`) does **not** yet have these fields. The UI session should do this as Task 0 (see `02__ui-tasks.md`).

---

## EC2 boot wiring

`scripts/provision_ec2.py` `USER_DATA_TEMPLATE` now includes:

```bash
pip install sgraph-ai-service-playwright-host --quiet || true

HOST_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
mkdir -p /opt/host-api && echo "$HOST_API_KEY" > /opt/host-api/api-key.txt

docker run -d --name sp-host-control --restart=unless-stopped --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e FAST_API__AUTH__API_KEY__VALUE="$HOST_API_KEY" \
  -p 9000:8000 sgraph/host-control:latest || true

aws ssm send-command ... "sgit vault set /ec2/{deploy_name}/host-api-key $HOST_API_KEY" || true
```

---

## Docker image

```
docker/host-control/Dockerfile       # Python 3.12 Alpine + uvicorn
docker/host-control/requirements.txt # sgraph-ai-service-playwright-host, uvicorn, fastapi, psutil
```

---

## Bug fix shipped: `caller_ip` auto-detection

`ephemeral_ec2/helpers/networking/Caller__IP__Detector.py` was sequential (3 × 8s = 24s timeout). Fixed:
- All probe URLs tried in parallel via `ThreadPoolExecutor`
- Plain HTTP probes tried first (avoids Python venv TLS cert issues)
- HTTPS probes use `ssl.CERT_NONE` context (data is non-sensitive: public IP only)
- `Open_Design__Service` and `Ollama__Service` now raise a clear, actionable error before any AWS call if detection fails

---

## Tests

| Test file | Count | Notes |
|-----------|-------|-------|
| `tests/unit/sgraph_ai_service_playwright__host/containers/test_Container__Runtime__Docker.py` | 9 | subprocess stubbed (narrow mock exception) |
| `tests/unit/sgraph_ai_service_playwright__host/shell/test_Shell__Executor.py` | 13 | Real subprocess; allowlist validation + executor |
| `tests/unit/sgraph_ai_service_playwright__host/fast_api/test_Fast_API__Host__Control.py` | 9 (skip) | Skipped when `osbot_fast_api_serverless` not installed |

1653 non-FastAPI unit tests pass on the branch.
