# UI Integration Notes

How `sp-cli-nodes-view` will use each new endpoint once the backend ships.
Included so the backend session can validate the contract from the caller's side.

---

## Boot log — `GET /host/logs/boot`

**Where:** New "Boot Log" sub-section in the Overview tab, or a dedicated 5th tab
"Boot" visible only while `state !== 'running'` (TBD by UI session once endpoint exists).

**Call pattern:** Fetched once on `_openDetail(stack)`. Refresh button re-fetches.

```javascript
const resp  = await fetch(`${hostUrl}/host/logs/boot?lines=300`, { headers: { 'X-API-Key': key } })
const data  = await resp.json()   // { source, lines, content, truncated }
pre.textContent = data.content
```

**Error handling:** If `fetch` throws (node not yet reachable), show a
`"Sidecar not yet reachable — node may still be booting"` message with a retry
button. This is the primary use case: the user launches a node and immediately
opens it; the sidecar may not be up yet.

---

## Container logs — `GET /containers/{name}/logs`

**Where:** Each row in the Containers tab gets a `Logs` button. Clicking opens a
log drawer below that row (or replaces the row with an expanded block).

**Call pattern:** On button click; `lines=200` default, user can expand to 500/1000.

```javascript
const resp = await fetch(`${hostUrl}/containers/${encodeURIComponent(name)}/logs?lines=200`, {
    headers: { 'X-API-Key': key }
})
const data = await resp.json()   // { container, lines, content, truncated }
pre.textContent = data.content
```

**Note on container name encoding:** Container names from `/containers/list` are
plain alphanumeric + hyphens; `encodeURIComponent` is a safety measure only.

---

## Container stats — `GET /containers/{name}/stats`

**Where:** Shown inline in each Containers tab row as a second line:
`CPU 1.4%  MEM 48 MB / 1024 MB  PIDs 6`

**Call pattern:** Fetched for all containers in parallel after the list loads,
using `Promise.allSettled` so one failure doesn't block the others.

```javascript
const statResults = await Promise.allSettled(
    containers.map(c =>
        fetch(`${hostUrl}/containers/${encodeURIComponent(c.name)}/stats`, { headers })
            .then(r => r.ok ? r.json() : null)
    )
)
```

Failed stats (404 / network error) silently omit the stats line rather than showing
an error — the container list itself is already visible.

---

## WebSocket log stream — `WS /host/logs/stream`

**Where:** "Live Tail" mode toggle in the Terminal tab (and optionally in the
container log drawer).

**Call pattern:**

```javascript
const ws = new WebSocket(`ws://${host}:19009/host/logs/stream?source=${name}&api_key=${key}`)
ws.onmessage = (e) => {
    const { ts, line } = JSON.parse(e.data)
    appendLine(ts, line)
}
ws.onclose = (e) => {
    if (e.code === 4001) showError('Authentication failed')
    else showInfo('Stream closed')
}
```

**Note:** The UI session will not build this until after P1+P2 are shipped and
tested. Documenting the expected shape now so the WS auth convention (`?api_key=`)
can be settled before implementation.

---

## What the UI does NOT need from this slice

- Metrics export / Prometheus scraping — out of scope
- Container restart / exec commands — the shell panel (`POST /host/shell/execute`)
  already handles `docker restart {name}` and `docker exec` via the allowlist
- Multi-host aggregation — each node's sidecar is called independently; no
  aggregation layer is needed at this stage
