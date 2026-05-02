# What the Backend Shipped — Reference for UI

**version** v0.1.140  
**date** 02 May 2026  
**branch** `claude/continue-playwright-refactor-xbI4j` (commit 11c2a08)

---

## Package

`sgraph_ai_service_playwright__host` — a standalone FastAPI service deployed on every EC2 host. It runs as a privileged Docker container named `sp-host-control`, mapped to host port **9000** (container port 8000).

---

## Base URL

```
http://{public_ip}:9000
```

Populated in `Schema__Ec2__Instance__Info.host_api_url`. If the host is booting or provisioning failed, the field is an empty string. **Always check for empty before making requests.**

---

## Authentication

Every request requires the header:

```
X-API-Key: {host_api_key}
```

The key is **not** the same as the SP CLI management API key. It is generated at EC2 boot and stored in vault at:

```
{host_api_key_vault_path}   # e.g. /ec2/grand-wien/host-api-key
```

`host_api_key_vault_path` is now a field on `Schema__Ec2__Instance__Info` (and will be on `Schema__Stack__Summary` after Task 0).

**Reading the key in a component:**

```javascript
import { currentVault } from '../../../../../shared/vault-bus.js'

open(stack) {
    const vaultPath = stack.host_api_key_vault_path
                   || `/ec2/${stack.stack_name}/host-api-key`  // fallback convention
    const vault = currentVault()
    if (vault && vaultPath) {
        vault.read(vaultPath).then(key => { this._hostApiKey = key })
    }
    this._hostApiUrl = stack.host_api_url
                    || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
}
```

`apiClient` (the singleton for SP CLI calls) must **not** be used for host API calls — it has a different base URL and a different key.

---

## Endpoints

### `GET /host/status`

```json
{
  "cpu_percent":     12.5,
  "mem_total_mb":    7887,
  "mem_used_mb":     3210,
  "disk_total_gb":   50,
  "disk_used_gb":    12,
  "uptime_seconds":  3720,
  "container_count": 4
}
```

### `GET /host/runtime`

```json
{
  "runtime": "docker",
  "version": "24.0.7"
}
```

### `POST /host/shell/execute`

Request body:
```json
{
  "command": "df -h",
  "timeout": 30,
  "working_dir": ""
}
```

Response:
```json
{
  "stdout":    "Filesystem      Size  Used Avail Use% Mounted on\n/dev/xvda1   50G   12G   38G  24% /\n",
  "stderr":    "",
  "exit_code": 0,
  "duration":  0.043,
  "timed_out": false
}
```

**Command allowlist** (only these prefixes are accepted — anything else returns 422):
```javascript
const QUICK_COMMANDS = [
    { label: 'List containers',      cmd: 'docker ps'           },
    { label: 'Container logs (sp-host-control)', cmd: 'docker logs sp-host-control' },
    { label: 'Disk usage',           cmd: 'df -h'               },
    { label: 'Memory',               cmd: 'free -m'             },
    { label: 'Uptime',               cmd: 'uptime'              },
    { label: 'Kernel version',       cmd: 'uname -r'            },
    { label: 'CPU info',             cmd: 'cat /proc/cpuinfo'   },
    { label: 'Memory info',          cmd: 'cat /proc/meminfo'   },
]
```

### `GET /containers/list`

```json
{
  "containers": [
    {
      "name":       "sp-playwright",
      "image":      "sgraph/playwright:latest",
      "status":     "running",
      "state":      "Up 2 hours",
      "ports":      { "8000/tcp": [{ "HostPort": "8000" }] },
      "created_at": "2026-05-02T09:00:00Z",
      "type_id":    "playwright"
    }
  ],
  "count": 4
}
```

### `GET /containers/{name}` → 404 on miss

Same shape as one item from `/containers/list`.

### `GET /host/shell/stream` (WebSocket — Phase 2)

Interactive rbash session. **Note:** browsers cannot send custom headers on WebSocket connections. The backend will need a `?api_key=` query-param fallback for WS auth — this is not yet implemented. Build Phase 1 (command panel) first; flag this to the backend session when ready for Phase 2.

### `GET /docs`

Swagger UI for the full host API. This is what `sp-cli-host-api-panel` shows in its iframe.

---

## How `/docs` and the iframe work

`sp-cli-api-view` does exactly this for the SP CLI management API:

```javascript
// sp-cli-api-view.js
onReady() {
    this._frame = this.$('.docs-frame')
    if (this._frame) this._frame.src = `${window.location.origin}/docs`
}
```

`sp-cli-host-api-panel` does the same thing but points at `host_api_url`:

```javascript
open(stack) {
    const url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
    if (!url) { this._showUnavailable(); return }
    this.$('.api-frame').src = `${url}/docs`
}
```

The Swagger page loads in an iframe — no auth header needed for the docs page itself (the SP CLI docs are also unauthenticated). Individual "Try it out" calls from within the iframe will need the key, but that's the user's problem; we just load the docs URL.

---

## Error handling

| Scenario | Behaviour |
|----------|-----------|
| `host_api_url` is empty | Show "Host API not yet available" message, no fetch |
| 401 from host API | Show "Authentication failed — host API key may have changed" |
| Network error / timeout | Show "Host unreachable" with the URL so the user can debug |
| 422 from `/host/shell/execute` | Command not in allowlist — show the raw error.detail from the response |

---

## Reproducing locally

```bash
# Start the host control plane locally (after installing the package):
FAST_API__AUTH__API_KEY__VALUE=dev-key python3 -m uvicorn \
    sgraph_ai_service_playwright__host.fast_api.lambda_handler:_app \
    --port 9000 --reload

# Test from browser console:
fetch('http://localhost:9000/host/status', { headers: { 'X-API-Key': 'dev-key' } })
    .then(r => r.json()).then(console.log)
```

Then trigger the detail panel with:
```javascript
document.querySelector('sp-cli-docker-detail').open({
    stack_name:              'test-stack',
    type_id:                 'docker',
    public_ip:               'localhost',
    host_api_url:            'http://localhost:9000',
    host_api_key_vault_path: '/ec2/test-stack/host-api-key',
})
```
