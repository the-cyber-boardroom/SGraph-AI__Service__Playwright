# Host Control Plane — Architecture Reference

**version** v0.22.20
**date** 02 May 2026
**from** Claude Code (frontend session)
**to** All teams (backend, frontend, architect)
**type** Reference / Architecture

---

## What This Document Is

A shared contract that both the backend CLI team and the frontend team can build against independently. It defines the package boundary, the full API surface, the security model, and the data flow so both sides can progress in parallel without stepping on each other.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (Admin Dashboard UI)                                   │
│  sp-cli-host-terminal  +  host-api iframe (/docs)              │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTPS + WS  (X-API-Key header)
                     │ host_api_url from stack info
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  EC2 Instance                                                   │
│                                                                 │
│  ┌───────────────────────────────┐  port 9000                  │
│  │  Fast_API__Host__Control      │  ← privileged container     │
│  │  (sgraph_ai_service_          │    (Docker/Podman socket    │
│  │   playwright__host package)   │     + host shell access)    │
│  └───────────────────────────────┘                             │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Playwright│  │ Firefox  │  │ Elastic  │  │  ...     │      │
│  │ container │  │ container│  │ container│  │  plugin  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │ EC2 lifecycle (create / delete / info)
         │ X-API-Key (SP CLI management key, separate from host key)
┌─────────────────────────────────────────────────────────────────┐
│  Fast_API__SP__CLI  (management plane — today's SP CLI)        │
│  Routes__Ec2__Playwright  /  Routes__Docker__Stack  / ...      │
└─────────────────────────────────────────────────────────────────┘
```

Two separate FastAPI services, two separate API keys, two separate roles:

| Service | Where it runs | Role | API key source |
|---------|--------------|------|----------------|
| `Fast_API__SP__CLI` | Lambda / laptop | **Management plane** — EC2 lifecycle, plugin routes, catalog | GH Actions secret / `.env` |
| `Fast_API__Host__Control` | EC2 instance | **Control plane** — container ops, shell, host metrics | Generated at EC2 boot, stored in vault |

---

## Package Boundary

New package: **`sgraph_ai_service_playwright__host`**

Lives at the repo root alongside `sgraph_ai_service_playwright__cli`. It is installed on the EC2 instance only — not deployed to Lambda, not imported by the SP CLI management plane.

```
sgraph_ai_service_playwright__host/
├── fast_api/
│   ├── Fast_API__Host__Control.py        ← Serverless__Fast_API subclass; api_key ON
│   ├── lambda_handler.py                 ← Mangum wrapper (for local testing only)
│   └── routes/
│       ├── Routes__Host__Containers.py   ← /containers/* CRUD
│       ├── Routes__Host__Shell.py        ← /host/shell/execute + WS /host/shell/stream
│       └── Routes__Host__Status.py       ← /host/status, /host/runtime
├── containers/
│   ├── service/
│   │   ├── Container__Runtime.py         ← abstract base (Type_Safe)
│   │   ├── Container__Runtime__Docker.py ← subprocess docker CLI adapter
│   │   └── Container__Runtime__Podman.py ← subprocess podman CLI adapter
│   └── schemas/
│       ├── Schema__Container__Info.py
│       ├── Schema__Container__List.py
│       ├── Schema__Container__Start__Request.py
│       ├── Schema__Container__Start__Response.py
│       ├── Schema__Container__Logs__Response.py
│       └── Schema__Container__Stop__Response.py
├── shell/
│   ├── service/Shell__Executor.py        ← allowlist-gated command execution
│   └── schemas/
│       ├── Schema__Shell__Execute__Request.py
│       └── Schema__Shell__Execute__Response.py
└── host/
    └── schemas/
        ├── Schema__Host__Status.py
        └── Schema__Host__Runtime.py
```

---

## Full API Surface

### Container Management

```
GET    /containers                     → Schema__Container__List
POST   /containers                     → Schema__Container__Start__Response
GET    /containers/{name}              → Schema__Container__Info          (404 on miss)
GET    /containers/{name}/logs         → Schema__Container__Logs__Response
POST   /containers/{name}/stop         → Schema__Container__Stop__Response
DELETE /containers/{name}              → Schema__Container__Stop__Response
```

### Host Information

```
GET    /host/status                    → Schema__Host__Status   (CPU, mem, disk, net)
GET    /host/runtime                   → Schema__Host__Runtime  (docker|podman, version)
```

### Shell

```
POST   /host/shell/execute             → Schema__Shell__Execute__Response
WS     /host/shell/stream              ← interactive pty (xterm.js client)
```

### Metrics

```
GET    /metrics                        → Prometheus text format (host + container stats)
```

---

## Key Schemas (contract for both teams)

### `Schema__Container__Info`

```python
class Schema__Container__Info(Type_Safe):
    name       : str   # container name
    image      : str
    status     : str   # running | exited | created | ...
    state      : str   # Up 2 hours | Exited (0) 3 minutes ago
    ports      : dict  # { "8080/tcp": [{"HostPort": "8080"}] }
    created_at : str   # ISO-8601
    type_id    : str   # plugin type: docker | firefox | elastic | ...
```

### `Schema__Shell__Execute__Request`

```python
class Schema__Shell__Execute__Request(Type_Safe):
    command    : Safe_Str__Shell__Command  # allowlist-gated
    timeout    : Safe_UInt__Timeout_Sec   # default 30, max 120
    working_dir: str                       # default ''
```

### `Schema__Shell__Execute__Response`

```python
class Schema__Shell__Execute__Response(Type_Safe):
    stdout    : str
    stderr    : str
    exit_code : int
    duration  : float
    timed_out : bool
```

### `Schema__Host__Status`

```python
class Schema__Host__Status(Type_Safe):
    cpu_percent    : float
    mem_total_mb   : int
    mem_used_mb    : int
    disk_total_gb  : int
    disk_used_gb   : int
    uptime_seconds : int
    container_count: int
```

---

## Security Model

### Privilege model

Only the host control plane container runs privileged. All plugin workload containers are unprivileged.

| Container | Privileged | Why |
|-----------|-----------|-----|
| `Fast_API__Host__Control` | **Yes** | Docker/Podman socket + host shell |
| Playwright | No | Isolated |
| Firefox | No | Isolated |
| Elastic/Kibana | No | Isolated |
| Any plugin workload | No | Isolated |

### Shell allowlist

`POST /host/shell/execute` is **deny-all by default**. Permitted command prefixes (analogous to `JS__Expression__Allowlist`):

```python
SHELL_COMMAND_ALLOWLIST = [
    'docker ps', 'docker logs', 'docker stats', 'docker inspect',
    'podman ps', 'podman logs', 'podman stats', 'podman inspect',
    'df -h', 'free -m', 'uptime', 'uname -r',
    'cat /proc/meminfo', 'cat /proc/cpuinfo',
    'systemctl status',
]
```

`WS /host/shell/stream` uses a restricted shell (`/bin/rbash` or a container-namespaced exec) — never a root shell.

### API key flow

```
EC2 boot (user-data)
  → secrets.token_hex(32) → /opt/host-api/api-key.txt
  → vault store: /ec2/{deploy_name}/host-api-key   (via SSM exec)

SP CLI (Fast_API__SP__CLI)
  → GET /ec2/playwright/info/{name}
  → response includes: host_api_url, host_api_key_vault_path

Browser (admin dashboard)
  → reads host_api_key from vault-bus
  → adds X-API-Key header to all host API calls
```

---

## EC2 Boot Integration

The user-data script additions (in `scripts/provision_ec2.py`):

```bash
# Install host control plane
pip install sgraph-ai-service-playwright-host

# Generate API key
HOST_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "$HOST_API_KEY" > /opt/host-api/api-key.txt
chmod 600 /opt/host-api/api-key.txt

# Start on port 9000 (privileged container, Docker socket mounted)
docker run -d \
  --name sp-host-control \
  --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e FAST_API__AUTH__API_KEY__VALUE="$HOST_API_KEY" \
  -p 9000:8000 \
  sgraph/host-control:latest

# Push API key to vault (deploy_name is passed in as user-data parameter)
aws ssm send-command ... "sgit vault set /ec2/${DEPLOY_NAME}/host-api-key $HOST_API_KEY"
```

---

## SP CLI Schema Additions

`Schema__Ec2__Instance__Info` gains two new fields (added by the backend team):

```python
host_api_url           : str  # e.g. "http://3.8.x.x:9000"  — empty until boot complete
host_api_key_vault_path: str  # e.g. "/ec2/grand-wien/host-api-key"
```

These are the only two fields the frontend needs to connect to the host API.

---

## Parallel Build Strategy

Both teams can start immediately. The coupling point is the two `Schema__Ec2__Instance__Info` fields above.

**Frontend** can mock `host_api_url` as a local dev server until the backend wires it.
**Backend** can test all routes with `TestClient` before any EC2 instance exists.

The mock URL convention for local dev: `http://localhost:9000`

---

## Relationship to Previous Briefs

| Date | Document | Relationship |
|------|----------|-------------|
| 01 May 2026 | `v0.22.19__dev-brief__container-runtime-abstraction.md` | **Parent brief.** This document implements the "Host FastAPI Control Plane" section. |
| 01 May 2026 | `v0.22.19__dev-brief__ephemeral-infra-next-phase.md` | AMI bake / fast-boot flow. The host API's container list feeds the instance detail pane. |
| 01 May 2026 | `v0.22.19__dev-brief__firefox-browser-plugin.md` | Firefox is a plugin workload. It starts as an unprivileged container managed by the host API. |
| 28 Apr 2026 | `v0.22.19__arch-brief__backend-plugin-architecture.md` | Plugin isolation model. Container-type plugins use the runtime abstraction, not Docker directly. |
