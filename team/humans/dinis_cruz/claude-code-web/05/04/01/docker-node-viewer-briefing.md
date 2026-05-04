# Docker Node Viewer — State of the World & What We Can Do Next

**Document type:** LLM session briefing  
**Audience:** A new agent session with no access to this codebase  
**Date:** 2026-05-04  
**Context:** This document describes SG/Compute — a cloud compute management
platform — specifically the "Docker node viewer" sub-system. Read this fully
before proposing any changes.

---

## 1. What is SG/Compute?

SG/Compute is an internal admin platform for provisioning and managing EC2
instances ("nodes") that run Docker containers. Think of it as a lightweight
private cloud control plane. Operators launch nodes from a browser-based admin
dashboard, watch them boot, inspect running containers, tail logs, run shell
commands, and stop nodes — all without touching the AWS console or SSH.

The platform has two main layers:

1. **Central management API** — a FastAPI service (the "SP CLI") that handles
   AWS EC2 lifecycle, catalogs available node types, and returns a list of
   active stacks. Operators authenticate to this with an API key.

2. **Per-node sidecar** — a second FastAPI service that runs *on each EC2
   instance* at port 19009. It is the node's own control plane. Operators
   authenticate to it with a separate per-node API key captured at launch.

This document focuses entirely on the per-node sidecar and the browser UI that
talks to it.

---

## 2. Physical Deployment

```
 ┌──────────────────────────────────────────────────────────────┐
 │  Operator's Browser  (localhost:10071 in dev)                │
 │                                                              │
 │   ┌─────────────────────────────────────────────────────┐   │
 │   │  Admin Dashboard (static HTML/JS/CSS)               │   │
 │   │  sp-cli-nodes-view  ◄──── Web Component             │   │
 │   └────────────────┬────────────────────────────────────┘   │
 └────────────────────│────────────────────────────────────────┘
                      │  HTTP + X-API-Key header
                      │  (CORS enabled on sidecar)
                      ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  EC2 Instance  (e.g. 35.179.103.81)                         │
 │                                                              │
 │  ┌─────────────────────────────────────────────────────┐    │
 │  │  sp-host-control  (Docker container)                │    │
 │  │  Fast_API__Host__Control  — port 19009              │    │
 │  │                                                      │    │
 │  │  GET  /host/status          psutil metrics           │    │
 │  │  GET  /host/runtime         docker version           │    │
 │  │  GET  /host/logs/boot       cloud-init tail          │    │
 │  │  GET  /pods/list            all containers           │    │
 │  │  GET  /pods/{name}          single container info    │    │
 │  │  GET  /pods/{name}/logs     container log tail       │    │
 │  │  GET  /pods/{name}/stats    CPU/mem snapshot         │    │
 │  │  POST /pods/{name}/stop     stop container           │    │
 │  │  DELETE /pods/{name}        remove container         │    │
 │  │  POST /host/shell/execute   allowlisted commands     │    │
 │  │  WS   /host/shell/stream    interactive rbash        │    │
 │  │  GET  /docs-auth?apikey=    pre-authed Swagger UI    │    │
 │  └─────────────────────────────────────────────────────┘    │
 │                                                              │
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
 │  │ sp-main      │  │ sp-worker    │  │ sp-proxy     │      │
 │  │ (app pods)   │  │ (app pods)   │  │ (app pods)   │      │
 │  └──────────────┘  └──────────────┘  └──────────────┘      │
 └──────────────────────────────────────────────────────────────┘
```

The sidecar (`sp-host-control`) is itself a Docker container on the same EC2
instance. It has access to the Docker socket (`/var/run/docker.sock`) so it can
inspect and control sibling containers. The API key is generated at EC2 boot
time and stored in a vault; the dashboard also captures it from the launch
response and persists it in localStorage.

---

## 3. What the Sidecar Exposes Today

### 3.1 Host Status  (`GET /host/status`)

```json
{
  "cpu_percent":   12.4,
  "mem_total_mb":  7900,
  "mem_used_mb":   3200,
  "disk_total_gb": 50,
  "disk_used_gb":  18,
  "uptime_seconds": 1140,
  "pod_count":     4
}
```

Populated by `psutil`. Sampled at request time (no polling on the server side).

### 3.2 Host Runtime  (`GET /host/runtime`)

```json
{ "runtime": "docker", "version": "24.0.7" }
```

### 3.3 Pod List  (`GET /pods/list`)

```json
{
  "pods": [
    {
      "name":       "sp-host-control",
      "image":      "sgraph/host-control:latest",
      "status":     "running",
      "state":      "Up 19 minutes",
      "ports":      { "8000/tcp": [{ "HostPort": "19009" }] },
      "created_at": "2026-05-04T10:12:00Z",
      "type_id":    "docker"
    }
  ],
  "count": 4
}
```

### 3.4 Pod Stats  (`GET /pods/{name}/stats`)

Single point-in-time snapshot from `docker stats --no-stream`:

```json
{
  "container":      "sp-host-control",
  "cpu_percent":    1.4,
  "mem_usage_mb":   48.2,
  "mem_limit_mb":   1024.0,
  "mem_percent":    4.7,
  "net_rx_mb":      0.12,
  "net_tx_mb":      0.08,
  "block_read_mb":  0.0,
  "block_write_mb": 2.1,
  "pids":           6
}
```

### 3.5 Pod Logs  (`GET /pods/{name}/logs?tail=100&timestamps=false`)

```json
{
  "container": "sp-host-control",
  "lines":     87,
  "content":   "2026-05-04T10:12:03Z INFO  Listening on :19009\n...",
  "truncated": false
}
```

### 3.6 Boot Log  (`GET /host/logs/boot?lines=200`)

```json
{
  "source":    "/var/log/cloud-init-output.log",
  "lines":     142,
  "content":   "Cloud-init v.23.1.2 running...\n...",
  "truncated": false
}
```

### 3.7 Shell Execute  (`POST /host/shell/execute`)

```json
// Request
{ "command": "docker ps", "timeout": 30 }

// Response
{ "stdout": "CONTAINER ID   IMAGE ...", "stderr": "", "exit_code": 0 }
```

**Allowlist** (deny-all by default, these exact prefixes permitted):
- `docker ps`, `docker logs`, `docker stats`, `docker inspect`
- `podman ps`, `podman logs`, `podman stats`, `podman inspect`
- `df -h`, `free -m`, `uptime`, `uname -r`
- `cat /proc/meminfo`, `cat /proc/cpuinfo`
- `systemctl status`

### 3.8 Shell Stream  (`WS /host/shell/stream`)

WebSocket wrapping `/bin/rbash`. Bypasses the allowlist (rbash is the security
boundary). Auth via `?api_key=` query param (browser WS can't send headers).
**Not yet wired to the UI** — the infrastructure exists but no xterm.js client.

### 3.9 Authenticated Swagger  (`GET /docs-auth?apikey={key}`)

Returns a custom HTML page that loads SwaggerUIBundle from CDN and pre-injects
the API key via `requestInterceptor`. The admin dashboard loads this in an
iframe so Swagger runs from the sidecar's own origin (same-origin, no CORS
needed for Swagger's own fetches).

---

## 4. Browser UI — What Exists Today

The "Docker Node Viewer" is a single Web Component (`sp-cli-nodes-view`).
It lives inside the Admin Dashboard as the "Active Nodes" tab.

### 4.1 Layout

```
 ┌──────────────────────────────────────────────────────────────────┐
 │ Admin Dashboard                                                  │
 │ ┌──────┐  ┌───────────────────────────────────────────────────┐ │
 │ │ Nav  │  │ Active Nodes  (sg-layout managed pane)            │ │
 │ │      │  │                                                   │ │
 │ │ COM  │  │ ┌──────────────────┬──────────────────────────┐  │ │
 │ │ PUTE │  │ │◀ ACTIVE NODES(1)↺│ 🐳 SWIFT-LOVELACE       │  │ │
 │ │      │  │ ├──────────────────│ Overview Boot Log Pods   │  │ │
 │ │ NODE │  │ │ 🐳 swift...      │ Terminal  Host API      │  │ │
 │ │  S   │  │ │   RUNNING        ├──────────────────────────┤  │ │
 │ │      │  │ │   13.40.49.210   │ [detail panel content]   │  │ │
 │ │ STAC │  │ │   19m            │                          │  │ │
 │ │  KS  │  │ └──────────────────┴──────────────────────────┘  │ │
 │ │      │  │   ↑ drag to resize / ◀ collapse                  │ │
 │ │ SETT │  └───────────────────────────────────────────────────┘ │
 │ │  G   │                                                        │
 │ │  API │  ┌── Diagnostics (toggled ──────────────────────────┐  │
 │ └──────┘  │  Events Log / Vault Status / Cost Tracker /      │  │
 │           │  Active Sessions / Storage Viewer                │  │
 └───────────┴──────────────────────────────────────────────────┘
```

The nodes list is **resizable** (drag handle between list and detail) and
**collapsible** (◀ button shrinks list to a 36px icon strip).

### 4.2 Node List Row

Each row shows:
- Plugin type icon (🐳 docker, 🦭 podman, 🔍 elastic, 🖥 vnc, …)
- Stack name (truncated)
- Status pill: `● RUNNING` (green) / `● STOPPED` (red) / `● PENDING` (yellow)
- Public IP
- Uptime

### 4.3 Detail Panel — Five Tabs

```
[ Overview ] [ Boot Log ] [ Pods ] [ Terminal ] [ Host API ]
```

**Overview tab:**
```
 Type        docker
 State       running
 Instance    t3.medium
 Region      eu-west-2
 Public IP   35.179.103.81
 Host API    http://35.179.103.81:19009
 Node ID     swift-lovelace
 Uptime      19m
 API Key     abc12345••••••••  👁 ⎘
 
 ┌──────────────────────────────┐
 │  ⏹  Stop Node               │  ← red danger button
 └──────────────────────────────┘
```
- API Key masked by default, 👁 reveals, ⎘ copies to clipboard
- Stop triggers a confirm card: "⚠ Stop swift-lovelace? [Cancel] [Confirm Stop]"

**Boot Log tab:**
- Fetched on tab open, ↺ refresh button
- Header shows source file path + line count
- `<pre>` scrolled to bottom (most recent lines visible)
- Shows "Unreachable — node may still be booting" while sidecar starts

**Pods tab:**
```
 CPU 12.4%  MEM 3200/7900 MB  DISK 18/50 GB  UPTIME 19m     ↺
 ─────────────────────────────────────────────────────────────
 sp-host-control   ● running   sgraph/host-control  CPU 1.4%  MEM 48MB  📋
 sp-main           ● running   sgraph/app:v2.1       CPU 0.8%  MEM 120MB 📋
 sp-worker         ● exited    sgraph/app:v2.1                            📋
 ─────────────────────────────────────────────────────────────
 [Log drawer — shown when 📋 clicked]
 sp-main ──────────────────────────────────────────── ✕
 2026-05-04T10:12:03Z INFO  Server started on :8080
 2026-05-04T10:12:04Z INFO  Connected to database
 ...
```
- Host stats bar populated from `/host/status`
- Pod rows: name, status pill, image, inline CPU%/MEM from `/pods/{name}/stats`
  (fetched in parallel with `Promise.allSettled`, failures are silent)
- 📋 opens a log drawer (bottom panel) showing `/pods/{name}/logs?tail=200`

**Terminal tab** (`sp-cli-host-shell` sub-component):
- Dropdown of quick commands (allowlisted: docker ps, docker stats, df -h, etc.)
- Run button → `POST /host/shell/execute`
- Output appended to a scrollable `<pre>` with `$ {cmd}` prompt line
- 401 and 422 handled explicitly with user-readable messages

**Host API tab** (`sp-cli-host-api-panel` sub-component):
- `<iframe>` pointing to `{host_url}/docs-auth?apikey={key}`
- Swagger UI loads from sidecar's own origin — same-origin, no CORS issue
- API key pre-injected via `requestInterceptor` — every Execute is already authed
- Status bar shows `🔑 Authenticated` / `⚠ No API key`

---

## 5. Data Flow Diagrams

### 5.1 Node Selected → Overview

```
User clicks node row
        │
        ▼
_openDetail(stack)
        │
        ├─ render info KV (sync, from stack object already in memory)
        ├─ _renderApiKeyRow(stack)  — masked key + reveal/copy buttons
        ├─ stopBtn.setStack(stack)
        ├─ hostShell.open(stack)    — sets URL + key, shows panel
        ├─ hostApiPanel.open(stack) — sets iframe src
        └─ activateTab('overview')
```

### 5.2 Pods Tab — Parallel Fetch

```
User clicks Pods tab
        │
        ▼
_fetchContainers()
        │
        ├─ fetch /pods/list          ─┐  Promise.all (sequential dep)
        └─ fetch /host/status         ┘
                │
                ▼
        _renderContainers(ct, st)
                │
                ├─ render host stats bar (CPU/MEM/DISK from /host/status)
                ├─ for each pod:
                │    render row (name, status, image)
                │    fetch /pods/{name}/stats  ─┐  Promise.allSettled
                │                               ┘  (non-blocking, best-effort)
                │    when resolves → update inline stats span
                └─ 📋 click → _fetchPodLogs(name) → /pods/{name}/logs?tail=200
```

### 5.3 Auth Flow

```
Node Launch
    │
    ▼
SP CLI API returns { api_key_value, stack_info }
    │
    ├─ admin.js captures api_key_value
    ├─ persists to localStorage: sp-cli:host-api-keys { stack_name: key }
    └─ augments stack objects in _populatePanes()

Node selected in UI
    │
    ▼
stack.host_api_key is populated from localStorage
    │
    ├─ X-API-Key header on all direct fetch calls
    └─ ?apikey= query param on iframe /docs-auth URL
```

### 5.4 Shell Execute Flow

```
User selects command from dropdown → clicks Run
        │
        ▼
POST /host/shell/execute
{ "command": "docker ps", "timeout": 30 }
        │
        ├─ Safe_Str__Shell__Command validates against allowlist → 422 if blocked
        ├─ Shell__Executor.execute() runs subprocess
        └─ { stdout, stderr, exit_code }
                │
                ▼
        _appendOutput(cmd, stdout+stderr, ok)
        → <div class="output-block">
            <span class="output-prompt">$ docker ps</span>
            <pre class="output-text">CONTAINER ID ...</pre>
          </div>
```

---

## 6. Key Technical Facts for Any Agent Working on This

| Fact | Detail |
|------|--------|
| Sidecar port | 19009 (host port), mapped from container port 8000 |
| Auth header | `X-API-Key: {key}` on all requests (except `/docs-auth`) |
| CORS | Fully open (`allow_origins=["*"]`) — sidecar trusts the API key |
| All UIs are Web Components | Shadow DOM, own CSS, `SgComponent` base class |
| No framework | Vanilla JS ES modules only (no React, Vue, etc.) |
| Design tokens | `ec2-tokens.css` must be in `sharedCssPaths` to resolve CSS vars in shadow roots |
| Pod vs Container | The sidecar uses "pod" terminology for Docker containers |
| WS shell stream | Exists on backend (`/host/shell/stream`, rbash), NOT yet wired to any UI |
| API key in localStorage | Key: `sp-cli:host-api-keys`, value: `{ stack_name: key }` |
| SP CLI API key | Separate key; key: `sg_api_key` in localStorage |

---

## 7. What We Could Do Next

Roughly prioritised. Items in the same group are roughly equal priority.

### Group A — High value, low effort (sidecar already capable)

**A1. Live-tail log streaming (xterm-style)**
The WS `/host/shell/stream` endpoint is deployed and serves `/bin/rbash`. An
xterm.js terminal component in the Terminal tab would replace the current
dropdown → static output pattern with a real interactive shell. The backend
already handles stdin/stdout piping; the UI just needs an xterm.js instance.
This is the single highest-impact improvement for developer experience.

**A2. Per-pod log streaming**
Currently `/pods/{name}/logs` returns a static snapshot. A streaming variant
(`GET /pods/{name}/logs/stream` with chunked transfer or WebSocket) would let
the log drawer auto-update in real time — vital for watching an app start up.

**A3. Auto-polling health indicator on node rows**
Poll `/host/status` every 10–30s while the Pods tab or Overview is open.
Show a live sparkline or "last seen" timestamp on each node row. Also: detect
when a node just launched (state = `pending` → `running`) and auto-open the
Boot Log tab with a progress indicator.

**A4. Port forwarding / link buttons**
`Schema__Pod__Info.ports` already contains the port mapping. For each exposed
port, render a clickable link in the pod row: `→ :8080`. This opens the
service directly in a new tab. For known service types (Kibana on 5601,
Prometheus on 9090, Grafana on 3000) show a labeled icon.

### Group B — Medium effort, high visibility

**B1. Node health timeline / boot status indicator**
Show a visual boot progress bar on newly-launched nodes:
```
EC2 booting  ──██████────  Sidecar up  ──████────  Pods ready
```
Implementation: poll `/host/status` until sidecar responds (EC2+Sidecar stage),
then check `/pods/list` until expected pods reach `running` (Pods ready stage).
Surface this as a status row under each node in the list.

**B2. Resource history sparklines**
Currently `/host/status` and `/pods/{name}/stats` are point-in-time. Add a
client-side ring buffer: poll every 10s, keep the last N samples, render a
mini sparkline (SVG or canvas) in the Overview tab. No backend change needed.

**B3. Pod start / restart**
`POST /pods` already exists (start a new pod from an image). Adding a
`POST /pods/{name}/restart` endpoint and a restart button in the pod row would
complete the pod lifecycle UI. Useful when an app pod crashes or needs config
reload.

**B4. File browser / artefact download**
Add `GET /host/files?path=/app/logs` to the sidecar that lists files in a
directory, plus `GET /host/files/download?path=...` to stream a file.
Surface as a "Files" tab in the node detail panel. Particularly useful for
downloading log files, config dumps, or test artefacts from the node.

**B5. Node cost tracker integration**
The existing `sp-cli-cost-tracker` component in the Diagnostics panel shows
running cost. The node detail Overview tab could show a per-node cost estimate
(uptime × instance type hourly rate). All data is already available: instance
type in `Schema__Stack__Summary`, uptime from `/host/status`.

### Group C — Larger changes, high strategic value

**C1. xterm.js interactive terminal**
Full xterm.js integration with the existing WS `/host/shell/stream` endpoint.
Would replace the current `sp-cli-host-shell` component entirely. Requires:
loading xterm.js from CDN into the shadow DOM, sizing the terminal to the panel,
passing the API key via `?api_key=` query param on the WebSocket URL.

**C2. Metrics dashboard (Prometheus)**
Add a Prometheus exporter to the sidecar (`GET /metrics`). The existing
Prometheus plugin on the platform already knows how to scrape. Add a "Metrics"
tab to the node detail panel that either: (a) renders a mini chart using
Chart.js/D3 from the metrics endpoint, or (b) embeds a Grafana iframe if a
Grafana pod is running on the node.

**C3. Multi-node aggregate view**
A new dashboard view (above the per-node detail) that shows all nodes in a
grid/table with their live `/host/status` data. Think: a fleet overview with
CPU, MEM, pod count, and health for all nodes at a glance. Needs parallel fetch
to all node sidecars.

**C4. Node provisioning progress view**
When a node is first launched (state = `pending`), automatically open a
"Provisioning" panel that polls the boot log in real time and parses known
cloud-init markers to show a step-by-step progress checklist:
```
✓ EC2 running
✓ Docker installed
✓ Control plane container started
◌ App containers pulling…
```

**C5. Node-to-node network map**
If multiple nodes are running, visualise which nodes can reach each other
(via the VPC or public internet). Would require a new `/host/network/peers`
endpoint on the sidecar, or a top-level management API query.

---

## 8. Current Gaps / Known Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| WS shell stream not in UI | Interactive terminal not available | Implement xterm.js (Group C1) |
| No live refresh on Pods tab | Stats go stale | Auto-poll every 30s (Group A3) |
| API key not captured on old nodes | `host_api_key` shows "not captured" | Requires re-launch or vault lookup |
| Boot Log not auto-opened on new nodes | Operator must find it manually | Poll sidecar until up, then auto-navigate (Group A3/B1) |
| `/host/status` has no network stats | Can't see bandwidth usage | Add `net_bytes_sent/recv` via psutil to the schema |
| Pod ports not shown as links | Exposed services not clickable | Group A4 |

---

## 9. File Map (for any agent implementing changes)

```
Admin Dashboard (served as static files)
├── admin/
│   ├── index.html           ← script tags for all components
│   ├── admin.js             ← page controller, event bus, layout
│   └── admin.css            ← root layout CSS
│
├── shared/
│   ├── api-client.js        ← SP CLI management API client
│   ├── settings-bus.js      ← feature toggles, defaults, localStorage
│   └── ec2-tokens.css       ← design tokens (MUST be in sharedCssPaths)
│
└── components/sp-cli/
    ├── sp-cli-nodes-view/   ← THE main node viewer component
    │   └── v0/v0.1/v0.1.0/
    │       ├── sp-cli-nodes-view.js    ← all logic
    │       ├── sp-cli-nodes-view.html  ← template (5 tabs)
    │       └── sp-cli-nodes-view.css   ← styles
    │
    └── _shared/
        ├── sp-cli-host-shell/       ← Terminal tab component
        │   └── v0/v0.1/v0.1.0/
        │       ├── sp-cli-host-shell.js
        │       ├── sp-cli-host-shell.html
        │       └── sp-cli-host-shell.css
        │
        └── sp-cli-host-api-panel/   ← Host API tab (iframe to /docs-auth)
            └── v0/v0.1/v0.1.0/
                ├── sp-cli-host-api-panel.js
                ├── sp-cli-host-api-panel.html
                └── sp-cli-host-api-panel.css

Sidecar (Python/FastAPI, runs on each EC2 node)
└── sg_compute/host_plane/
    ├── fast_api/
    │   ├── Fast_API__Host__Control.py  ← app setup, CORS, middleware
    │   └── routes/
    │       ├── Routes__Host__Status.py ← GET /host/status, /host/runtime
    │       ├── Routes__Host__Logs.py   ← GET /host/logs/boot
    │       ├── Routes__Host__Pods.py   ← CRUD on /pods/*
    │       ├── Routes__Host__Shell.py  ← POST /host/shell/execute, WS stream
    │       └── Routes__Host__Docs.py   ← GET /docs-auth?apikey=
    │
    ├── host/schemas/
    │   ├── Schema__Host__Status.py
    │   ├── Schema__Host__Runtime.py
    │   └── Schema__Host__Boot__Log.py
    │
    ├── pods/schemas/
    │   ├── Schema__Pod__Info.py
    │   ├── Schema__Pod__List.py
    │   ├── Schema__Pod__Logs__Response.py
    │   └── Schema__Pod__Stats.py
    │
    ├── pods/service/
    │   ├── Pod__Runtime.py           ← abstract base
    │   ├── Pod__Runtime__Docker.py   ← docker CLI adapter
    │   ├── Pod__Runtime__Podman.py   ← podman CLI adapter
    │   └── Pod__Runtime__Factory.py  ← get_pod_runtime() selector
    │
    └── shell/
        ├── shell_command_allowlist.py ← SHELL_COMMAND_ALLOWLIST
        ├── schemas/Schema__Shell__Execute__Request.py
        └── service/Shell__Executor.py
```

---

## 10. Rules Any Agent Must Follow

These are non-negotiable conventions in this codebase:

1. **No Pydantic, no Literals** — all schemas extend `Type_Safe` from `osbot-utils`
2. **All UI is shadow-DOM Web Components** — three files per component: `.js`,
   `.html`, `.css`; JS class extends `SgComponent`
3. **`ec2-tokens.css` must be loaded inside every shadow root** that uses the
   design tokens — add it to `sharedCssPaths` via
   `new URL('../../../shared/ec2-tokens.css', import.meta.url).href`
4. **No raw boto3** — AWS operations go via `osbot-aws`
5. **No mocks in tests** — use real in-memory stacks
6. **Design tokens** — use `--bg-*`, `--text-*`, `--border-*`, `--bad`,
   `--good`, `--warn`, `--accent` etc. from `ec2-tokens.css`; never hardcode
   colours
7. **Events are document-level** — all cross-component communication uses
   `document.dispatchEvent(new CustomEvent(..., { bubbles: true, composed: true }))`
8. **One class per file** — Python side; every schema, enum, collection in its
   own file named exactly after the class
