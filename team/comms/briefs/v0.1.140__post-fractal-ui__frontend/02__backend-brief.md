# Host Control Plane — Backend / CLI Team Brief

**version** v0.22.20
**date** 02 May 2026
**from** Claude Code (frontend session)
**to** Backend / CLI team (other Claude session)
**type** Dev brief

---

## Objective

Build `sgraph_ai_service_playwright__host` — a FastAPI service that runs on every EC2 instance as the privileged control plane for containers and host shell access. Wire it into the EC2 boot sequence and expose `host_api_url` through the existing `Schema__Ec2__Instance__Info`.

Architecture context: `v0.22.20__reference__host-control-plane-architecture.md` (same folder).

---

## Why This Session Owns It

- All work is Python + `Type_Safe` schemas + FastAPI routes — the existing patterns in `sgraph_ai_service_playwright__cli`
- The SP CLI schema changes (`host_api_url`, `host_api_key_vault_path`) must come from here because the schema files and EC2 service live in the CLI package
- EC2 user-data scripting lives in `scripts/provision_ec2.py`
- No browser code involved

---

## Tasks

### Task 1 — Container Runtime Abstraction

**New files:**

```
sgraph_ai_service_playwright__host/containers/service/Container__Runtime.py
sgraph_ai_service_playwright__host/containers/service/Container__Runtime__Docker.py
sgraph_ai_service_playwright__host/containers/service/Container__Runtime__Podman.py
```

`Container__Runtime` is a `Type_Safe` base defining the interface. Docker and Podman adapters implement it by shelling out to the respective CLI (subprocess, not SDK — keeps the dependency graph minimal).

```python
# Abstract interface (Container__Runtime.py)
class Container__Runtime(Type_Safe):
    def list    (self)                     -> Schema__Container__List
    def start   (self, req)                -> Schema__Container__Start__Response
    def info    (self, name: str)          -> Schema__Container__Info | None
    def logs    (self, name: str, tail=100)-> Schema__Container__Logs__Response
    def stop    (self, name: str)          -> Schema__Container__Stop__Response
    def remove  (self, name: str)          -> Schema__Container__Stop__Response
```

The Docker adapter calls `docker ps --format json`, parses the output, returns typed schemas. Same for Podman (`podman ps --format json`). No docker-py SDK, no podman-py — just subprocess.

A factory function `get_container_runtime() -> Container__Runtime` checks `which docker` / `which podman` and returns the appropriate adapter. Plugins never import Docker or Podman directly.

**Acceptance:** Unit tests that stub the subprocess output (one of the narrow exceptions to no-mocks — the subprocess is the external boundary here). All eight `Container__Runtime` methods covered.

---

### Task 2 — Shell Executor

**New files:**

```
sgraph_ai_service_playwright__host/shell/service/Shell__Executor.py
sgraph_ai_service_playwright__host/shell/schemas/Schema__Shell__Execute__Request.py
sgraph_ai_service_playwright__host/shell/schemas/Schema__Shell__Execute__Response.py
sgraph_ai_service_playwright__host/shell/primitives/Safe_Str__Shell__Command.py
```

`Safe_Str__Shell__Command` validates that the command string starts with one of the entries in `SHELL_COMMAND_ALLOWLIST` (defined in `Shell__Executor`). Deny-all by default — a blank or arbitrary command raises a validation error before the subprocess is ever spawned.

`Shell__Executor.execute(request)` runs the validated command with `subprocess.run`, captures stdout/stderr, enforces the timeout, and returns `Schema__Shell__Execute__Response`.

**Acceptance:** Test that an allowlisted command (`df -h`) executes and returns output. Test that a disallowed command (`rm -rf /`) raises a validation error at the `Safe_Str__Shell__Command` level, never reaching subprocess. Test timeout enforcement.

---

### Task 3 — FastAPI Routes

**New files:**

```
sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Containers.py
sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Shell.py
sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Status.py
sgraph_ai_service_playwright__host/fast_api/Fast_API__Host__Control.py
sgraph_ai_service_playwright__host/fast_api/lambda_handler.py
```

`Fast_API__Host__Control` extends `Serverless__Fast_API`. `config.enable_api_key = True`. Routes follow the exact same pattern as `Routes__Ec2__Playwright` — zero logic, pure delegation to the service layer.

`Routes__Host__Shell` adds one additional endpoint beyond the standard `Fast_API__Routes` helpers: a WebSocket handler for `WS /host/shell/stream`. FastAPI supports WebSockets natively — accept the connection, spawn `asyncio.create_subprocess_shell('/bin/bash')` with stdin/stdout piped to the socket, forward bytes in both directions. The WebSocket endpoint does NOT go through `Safe_Str__Shell__Command` — it is a restricted shell session (use `/bin/rbash` to prevent path manipulation).

`Routes__Host__Status` uses Python's `psutil` (already a transitive dep via some osbot packages, or add it) to fill `Schema__Host__Status`.

**Acceptance:** `TestClient` tests — list containers (empty), start container mock, 404 on info miss, execute allowlisted shell command, 422 on disallowed command, 401 on missing API key. 10+ cases total following `test_Fast_API__SP__CLI.py` pattern.

---

### Task 4 — Schema additions to SP CLI

**Modified files:**

```
sgraph_ai_service_playwright__cli/ec2/schemas/Schema__Ec2__Instance__Info.py
sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py
```

Add two fields to `Schema__Ec2__Instance__Info`:

```python
host_api_url            : str  # "http://{public_ip}:9000" — empty string if not yet boot-complete
host_api_key_vault_path : str  # "/ec2/{deploy_name}/host-api-key" — empty string if not provisioned
```

`Ec2__Service.get_instance_info()` populates them: `host_api_url` is constructed from the instance's public IP (already available in the existing instance info dict from `describe_instances`). `host_api_key_vault_path` follows the convention `/ec2/{deploy_name}/host-api-key`.

These two fields are the **only coupling point** with the frontend. The frontend mocks `http://localhost:9000` until EC2 instances are live.

**Acceptance:** Update `test_Fast_API__SP__CLI.py` — the info response for a mock instance includes both new fields. No 422 on missing fields (they default to empty string).

---

### Task 5 — EC2 boot wiring

**Modified file:**

```
scripts/provision_ec2.py
```

Add to the user-data script (the multiline string passed to `run_instances`):

```bash
# ── host control plane ─────────────────────────────────────
pip install sgraph-ai-service-playwright-host --quiet

HOST_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
mkdir -p /opt/host-api && echo "$HOST_API_KEY" > /opt/host-api/api-key.txt
chmod 600 /opt/host-api/api-key.txt

docker run -d \
  --name sp-host-control \
  --restart=unless-stopped \
  --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e FAST_API__AUTH__API_KEY__VALUE="$HOST_API_KEY" \
  -p 9000:8000 \
  sgraph/host-control:latest

# Push key to vault so SP CLI can retrieve it
DEPLOY_NAME="${deploy_name_placeholder}"
aws ssm send-command \
  --instance-ids "$(curl -s http://169.254.169.254/latest/meta-data/instance-id)" \
  --document-name "AWS-RunShellScript" \
  --parameters commands=["sgit vault set /ec2/$DEPLOY_NAME/host-api-key $HOST_API_KEY"] \
  --region "${region}" || true
```

The `|| true` ensures that a vault push failure does not abort the rest of the boot sequence. The frontend will show `host_api_url` as unavailable until the key is in the vault.

Also add port 9000 to the security group ingress rules (TCP, source restricted to the user's IP or the SP CLI Lambda's security group).

**Acceptance:** End-to-end deploy test: create an EC2 instance, wait for running state, call `GET /ec2/playwright/info/{name}`, verify `host_api_url` is non-empty and `GET {host_api_url}/host/status` returns 200 with valid JSON (requires `FAST_API__AUTH__API_KEY__VALUE` from vault).

---

### Task 6 — Docker image for host control plane

**New files:**

```
docker/host-control/Dockerfile
docker/host-control/requirements.txt
```

Small Alpine-based image: Python 3.12, `sgraph-ai-service-playwright-host`, `uvicorn`. Entrypoint starts uvicorn on port 8000. The API key is injected at runtime via the `FAST_API__AUTH__API_KEY__VALUE` env var (not baked into the image).

CI: add a `build-host-control` job to the GitHub Actions workflow that builds and pushes to ECR under `sgraph/host-control:latest`.

---

## Build Order

```
Task 1 (runtime abstraction) → Task 2 (shell executor) → Task 3 (FastAPI routes)
                                                         ↓
Task 4 (schema additions)  ←─────────────────────────── Task 3 (done)
                                                         ↓
Task 5 (EC2 boot wiring)   ←─────────────────────────── Task 4 (done)
Task 6 (Docker image)      ←─────────────────────────── Task 3 (done)
```

Tasks 1 and 2 are independent of each other and can run in parallel.

---

## Constraints

- **No boto3 directly.** Use `osbot-aws` wrappers. Narrow exception: the two-statement Lambda Function URL permission (existing precedent).
- **No mocks for EC2 service tests.** Use `Ec2__Service__In_Memory` subclass pattern already in `tests/unit/`.
- **subprocess for container CLI calls is the one exception** to the no-mocks rule — stub the subprocess output in unit tests. Integration tests run against a real Docker daemon.
- **All classes extend `Type_Safe`.** No plain Python classes, no Pydantic, no Literals.
- **One class per file.** Every schema, primitive, enum in its own file.
- **`═══` 80-char headers** in every file.
- **No docstrings.** Inline comments only, and only where the WHY is non-obvious.

---

## Acceptance Checklist (complete before pushing)

- [ ] `get_container_runtime()` returns Docker adapter on a host with Docker installed
- [ ] `get_container_runtime()` returns Podman adapter on a host with only Podman installed
- [ ] `Container__Runtime.list()` parses `docker ps` JSON output into `Schema__Container__List`
- [ ] `Shell__Executor` rejects disallowed commands at the primitive validation level
- [ ] `Shell__Executor` enforces timeout (test with `sleep 200`)
- [ ] `Fast_API__Host__Control` returns 401 for requests with wrong API key
- [ ] `GET /containers` returns empty list (no error) when no containers running
- [ ] `POST /host/shell/execute` with `df -h` returns stdout with `/dev/` entries
- [ ] `Schema__Ec2__Instance__Info` includes `host_api_url` and `host_api_key_vault_path`
- [ ] All existing SP CLI tests still pass after schema addition
- [ ] Docker image builds and starts without error
