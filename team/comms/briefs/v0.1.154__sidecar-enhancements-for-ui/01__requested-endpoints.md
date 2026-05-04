# Requested Sidecar Endpoints

All endpoints run on the host sidecar at `http://{public_ip}:19009`.  
All require `X-API-Key: {host_api_key}` header — same auth as existing endpoints.  
All return `Content-Type: application/json`.

---

## 1. `GET /host/logs/boot`

Return the tail of the EC2 boot / cloud-init log so the UI can show setup progress
for a newly-launched node.

**Source:** `/var/log/cloud-init-output.log` (preferred) or `/var/log/cloud-init.log`

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `lines` | int | `200` | Max lines to return (cap at 2000) |

**Response:**

```json
{
  "source":    "/var/log/cloud-init-output.log",
  "lines":     142,
  "content":   "Cloud-init v. 23.1.2 running...\n...",
  "truncated": false
}
```

`content` is a single newline-joined string (not an array) so the UI can drop it
straight into a `<pre>`. `truncated: true` when the file was longer than `lines`.

---

## 2. `GET /containers/{name}/logs`

Return the tail of a container's stdout+stderr. Avoids the shell panel for routine
log inspection.

**Path param:** `name` — container name (as returned by `/containers/list`)

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `lines` | int | `100` | Max lines (cap at 1000) |
| `timestamps` | bool | `false` | Prepend Docker timestamps |

**Response:**

```json
{
  "container": "sp-host-control",
  "lines":     87,
  "content":   "2026-05-04T10:12:03Z INFO  Listening on :19009\n...",
  "truncated": false
}
```

Return `404` with `{"detail": "container not found"}` if the name doesn't exist.  
Return `404` with `{"detail": "container not running"}` if the container is stopped
and has no log history (implementation's discretion; stopped containers often still
have logs, so returning them is preferred).

---

## 3. `GET /containers/{name}/stats`

Return a single point-in-time snapshot of resource usage for one container.
`docker stats --no-stream` style — no streaming, just one sample.

**Path param:** `name` — container name

**Response:**

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

`mem_limit_mb` is the container memory limit (or host total if unconstrained).  
All `_mb` fields are floats, rounded to 1 decimal.

Return `404` if container not found.

---

## 4. `WS /host/logs/stream` (Phase 2 — lower priority)

WebSocket endpoint that streams new log lines from a container or host journal in
real time. Useful for the Terminal tab's "live tail" mode.

**Query params:**

| Param | Type | Notes |
|-------|------|-------|
| `source` | string | `host` (journald) or a container name |
| `api_key` | string | Auth — browser WS cannot send custom headers |

**Message format (server → client):**

```json
{ "ts": "2026-05-04T10:15:00Z", "line": "INFO  heartbeat ok" }
```

Close the WS with code `4001` if `api_key` is invalid.

**Note:** The existing `WS /host/shell/stream` has the same auth challenge.
Coordinate the `?api_key=` query-param convention across both endpoints.

---

## Priority order

| Priority | Endpoint | Reason |
|----------|----------|--------|
| P1 | `GET /host/logs/boot` | Answers "why is my node not ready yet?" — most-asked question during demos |
| P1 | `GET /containers/{name}/logs` | Enables log inspection without typing in the shell panel |
| P2 | `GET /containers/{name}/stats` | Nice-to-have detail in the Containers tab |
| P3 | `WS /host/logs/stream` | Full live-tail; can ship independently after P1+P2 |
