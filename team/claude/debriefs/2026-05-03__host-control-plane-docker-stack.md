# Debrief: Host Control Plane — sp docker stack end-to-end
**Slice:** sg-compute B4 / B5 + host control plane wiring  
**Branch:** `claude/sg-compute-b4-control-plane-xbI4j`  
**Date:** 2026-05-03  
**Outcome:** Working — `sp docker create --open --wait` provisions an EC2 node with the host control plane container live on port 9000, Docker CLI talking to the host daemon via mounted socket, and the FastAPI docs accessible from the public IP.

---

## What we were trying to do

Wire the `sgraph_ai_service_playwright__host` FastAPI sidecar into every `sp docker create` node so that the host control plane (container list, shell execute, host status) is reachable via HTTP on port 9000, API-key authenticated, and queryable from outside the instance.

---

## What went wrong (root causes, in order discovered)

### 1. `sgraph-ai-service-playwright-host` does not exist on PyPI

The original Dockerfile did `pip install sgraph-ai-service-playwright-host` and the user-data also ran the same command. The package was never published. Silent failure — the pip install just failed with "not found" and the container never started.

**Good failure** — caught immediately when checking the Dockerfile against the actual package structure.

**Fix:** Copy source directly into the image (`COPY sgraph_ai_service_playwright__host/ ./`) and set `PYTHONPATH=/app`.

### 2. No dedicated CI job for the host image

The ECR image `sgraph_ai_service_playwright_host:latest` was referenced in user-data but had no CI pipeline to build or push it.

**Fix:** Created `.github/workflows/ci__host_control.yml` — unit tests, AWS credential check, path-based change detection, build + push to ECR.

### 3. Host control plane CI failed: `No module named pytest`

The CI job installed from `docker/host-control/requirements.txt` (uvicorn, fastapi, psutil — no test tools) then called `python -m pytest`. Immediate exit code 1.

**Good failure** — caught on first CI run.

**Fix:** `pip install -r requirements.txt pytest pytest-timeout` in the install step.

### 4. ECR verify step: `contains()` on null imageTags crashes JMESPath

`imageDetails[?contains(imageTags, \`latest\`)]` crashes when any image in the repo has `imageTags: null` (untagged digest layers). Exit code 255.

**Good failure** — only the verify step failed; build + push were already green.

**Fix:** `--image-ids imageTag=latest` — looks up the specific tag directly, no JMESPath filtering.

### 5. `Fast_API__Host__Control` imported from `sgraph_ai_service_playwright__cli`

`Fast_API__Host__Control.py` imported `register_type_safe_handlers` from the CLI package, which is not copied into the Docker image. Container crashed on startup with `ModuleNotFoundError`.

**Bad failure** — the cross-package import was present from the start and went unnoticed because local tests don't run uvicorn. Only surfaced when the container actually tried to boot.

**Fix:** Copy `exception_handlers.py` into `sgraph_ai_service_playwright__host/fast_api/` and import from local path.

### 6. `sp docker health` with `timeout_sec=0` timed out immediately

`Docker__Health__Checker` used `while time.monotonic() < deadline` where `deadline = now + 0`. The loop never executed. Result: `state=unknown, timed out after 0s`.

**Bad failure** — `sp docker health` (the "quick probe" command) was silently broken from day one.

**Fix:** Changed to `while True: ... if time.monotonic() >= deadline: break` — always makes at least one probe.

### 7. Port 9000 not open in Docker stack security group

`Docker__SG__Helper` only opened ports from `extra_ports`. Port 9000 was never added by default so `curl http://{ip}:9000` hung from outside (SG blocked it).

**Bad failure** — the host control plane was running and reachable from inside the instance, but unreachable from outside. Diagnosis required cross-referencing `sp docker connect` + curl inside vs outside.

**Fix:** Added `HOST_CONTROL_PORT = 9000` constant; always appended to `ports_to_open`.

### 8. `Docker__User_Data__Builder` had no host control plane section

`sp docker create` uses `Docker__User_Data__Builder`, not `provision_ec2.py`'s `USER_DATA_TEMPLATE`. The builder only installed Docker CE — no ECR login, no `docker run sp-host-control`.

**Bad failure** — this was the fundamental gap. The host control plane was fully built and pushed to ECR but `sp docker create` never started it.

**Fix:** Added ECR login + `docker run` block to `USER_DATA_TEMPLATE`; added `registry`, `api_key_name`, `api_key_value` as render params; wired `ecr_registry_host()` + `secrets.token_hex(32)` through `Docker__Service.create_stack`.

### 9. ECR Docker token left on disk after pull

After `docker login + docker run`, `/root/.docker/config.json` holds a temporary ECR credential valid for 12 hours. No reason to leave it on disk once the container is started.

**Fix:** `rm -f /root/.docker/config.json` immediately after `docker run` in both `Docker__User_Data__Builder` and `provision_ec2.py`.

### 10. `docker-cli` not installed in the Alpine image

`Container__Runtime__Docker` shells out to the `docker` binary. `python:3.12-alpine` has no Docker client. The socket was mounted and `--privileged` was set, but the binary was missing. Result: `"no container runtime found: neither docker nor podman is in PATH"`.

**Good failure** — clear error, easy fix.

**Fix:** `RUN apk add --no-cache docker-cli` in the Dockerfile.

### 11. `--open` flag misunderstood

The subagent interpreted `--open` as "open browser to docs URL". The user meant "open the security group to `0.0.0.0/0` instead of caller `/32`".

**Bad failure** — ambiguous flag name; should have asked before implementing.

**Fix:** `--open` now sets `open_to_all=True` in the request → `Docker__SG__Helper` uses `0.0.0.0/0` as CIDR. The create output shows `0.0.0.0/0 (open)` to make it visible.

---

## What actually works (confirmed 2026-05-03)

```
sp docker create --open --wait
```

- Provisions AL2023 EC2 with Docker CE
- ECR-logs in, pulls `sgraph_ai_service_playwright_host:latest`, starts on port 9000
- Deletes ECR token from disk immediately after
- SG opens port 9000 (+ all ports to 0.0.0.0/0 when `--open`)
- `--wait` polls until both `docker_ok` AND `sp-host-control` container is `running`
- Create output shows api-key-name, api-key-value, and DevTools cookie snippet
- `GET /containers/list` → 200, lists `sp-host-control` container
- `POST /host/shell/execute` `{"command": "docker ps"}` → 200, shows running containers

---

## Remaining gaps / follow-up

- **AMI-based launches** (`sp docker create --ami`): `AMI_USER_DATA_TEMPLATE` skips the host control plane block — needs same ECR login + docker run added.
- **Port 9000 commonality**: port 9000 is used by SonarQube and others; worth moving to a less-contested port range (e.g. `19009`).
- **`--wait` polls but doesn't show progress**: user sees nothing during the 2–4 min boot. A progress ticker would help.
- **Vault push missing for docker stacks**: `provision_ec2.py` pushes the host API key to vault via SSM; `Docker__User_Data__Builder` does not (key is shown in create output instead).
