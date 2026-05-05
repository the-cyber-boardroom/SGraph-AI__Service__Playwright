# Bug Batch 1 — Sidecar Auth and Terminal Failures

**Date:** 2026-05-05
**Branch:** `claude/sgcompute-frontend-v0.2-5sjIO`
**Reporter:** Dinis Cruz (via screenshots)
**Status:** Analysis complete; fixes tracked per-bug below

---

## Overview

Five runtime bugs observed in the sg-compute admin dashboard after the v0.2.1 hotfix phase. All bugs surface when a node was launched via CLI (`sp docker create`) rather than via the dashboard Launch flow. Root cause: the CLI path never populates `_hostApiKeys` in localStorage → every direct sidecar API call fails with 401.

---

## Bug 1 — Boot log returns 401 / not working

**Screenshot:** pic1 — boot log panel shows error
**Component:** `sg-compute-nodes-view` → `_fetchBootLog()`
**Root cause:**
`_fetchBootLog()` reads `s.host_api_key` from the stack object passed to `setStacks()`.
```js
const key = s?.host_api_key || ''
const resp = await fetch(`${base}/host/logs/boot?lines=300`, {
    headers: key ? { 'X-API-Key': key } : {},
})
```
`host_api_key` is populated only when the node was launched via the dashboard (captured from the `sp-cli:node.launched` event and stored in `_hostApiKeys`). CLI-launched nodes have no entry → `key = ''` → no `X-API-Key` header → 401.

**Fix:** Blocked on Bug 4. Once the EC2 tag approach lands and `GET /api/nodes` returns `host_api_key` in the node payload, the boot log will automatically receive the key.

**Owner:** Backend (Bug 4 backend brief: `BV__host-api-key-via-ec2-tag.md`)

---

## Bug 2 — Pods tab returns 500

**Screenshot:** pic2 — pods view shows 500 error response
**Component:** `Routes__Compute__Pods` → `list_pods()`
**Root cause:**
```python
def list_pods(self, node_id: str) -> dict:
    return self.manager.list_pods(node_id).json()
```
No try/except. `Pod__Manager._resolve_api_key()` fetches from SSM. If SSM is inaccessible (no credentials, wrong region, key absent), it raises an unhandled exception → FastAPI returns 500.

Secondary: for CLI-launched nodes the host API key was never stored in SSM via the dashboard flow. SSM lookup hits a missing path → also raises.

**Fix:** Wrap `Routes__Compute__Pods.list_pods()` in try/except; return a structured 503 `{ error: "sidecar unreachable", detail: str(e) }` instead of propagating the raw exception.

**Owner:** Backend — brief filed at `BV__pods-500-error-handling.md`

---

## Bug 3 — Terminal shows rbash error

**Screenshot:** pic3 — WebSocket terminal panel shows shell error
**Component:** Sidecar host-shell WebSocket handler (on EC2 instance)
**Root cause:**
The sidecar terminal handler spawns `/bin/rbash`. Standard Ubuntu EC2 AMIs do not ship with `rbash` — the binary does not exist at that path. The exec call fails immediately.

**Fix:** Change sidecar shell handler to spawn `/bin/bash` instead of `/bin/rbash`. The sidecar already runs on a node that requires AWS credentials to reach; `/bin/rbash` adds no meaningful security boundary given that context.

**Owner:** Backend sidecar (EC2 user-data / sidecar binary) — brief filed at `BV__sidecar-rbash-fix.md`

---

## Bug 4 — Host API key not captured when node launched via CLI

**Screenshot:** pic4 — `sp docker create` succeeds but subsequent dashboard interactions fail
**Component:** `Schema__Node__Info` / `Routes__Compute__Nodes` / CLI flow
**Root cause:**
The dashboard captures the host API key only from the `sp-cli:node.launched` event, which fires when the Launch Panel completes. CLI launches (`sp docker create`) bypass the dashboard entirely. `Schema__Node__Info` returns `host_api_key_ssm_path` (the SSM path) but NOT the actual key value. The frontend has no way to retrieve the key.

```python
# Schema__Node__Info (current)
host_api_key_ssm_path: Safe_Str__SSM__Path = Safe_Str__SSM__Path()
# host_api_key field: ABSENT
```

**Agreed interim fix (acceptable risk — per Dinis Cruz 2026-05-05):**
During EC2 node creation, tag the instance with the host API key:
```
Tag key:   sg-compute:host-api-key
Tag value: <key_value>
```

- **Security posture:** Tag is visible to any IAM identity with `ec2:DescribeTags` on the instance. This is acceptable because: (a) reaching the node at all already requires AWS credentials; (b) the key is valid only for the lifecycle of the instance; (c) a PKI-based solution will replace this when the platform matures.
- **Better long-term solution:** PKI / mTLS — deferred.

Backend change: tag the instance in `Node__Creator.create_node()` (or equivalent), then expose the key in `GET /api/nodes` response (`Schema__Node__Info.host_api_key` field).

Frontend change: `admin.js` `_populatePanes()` already does:
```js
host_api_key: _hostApiKeys[s.node_id] || s.host_api_key || ''
```
So once the backend returns `host_api_key` in the node payload the frontend will use it automatically — no frontend code change needed.

**Owner:** Backend — brief filed at `BV__host-api-key-via-ec2-tag.md`

---

## Bug 5 — Terminal "Authentication failed" / weird layout

**Screenshot:** pic5 — quick commands panel shows "Authentication failed" and layout is unusual
**Component:** `sg-compute-host-shell` → quick-commands section
**Root cause:**
Direct consequence of Bug 4. `sg-compute-host-shell` reads the host API key from vault:
```js
vault.read(vaultPath).then(k => { this._hostApiKey = k || '' })
```
For CLI-launched nodes the vault path was never written → key is empty → every POST to `/host/shell/execute` receives:
```
Authentication failed — host API key may have changed.
```

The "weird layout" (terminal iframe above, commands below) is the correct layout for when the shell iframe is loaded. The iframe itself shows the rbash error (Bug 3).

**Fix:** Resolved by Bug 4 (key available) + Bug 3 (rbash→bash). No separate frontend change needed once the key flows through.

**Owner:** Backend (Bugs 3 + 4)

---

## Fix Dependency Graph

```
Bug 4 (EC2 tag → key in GET /api/nodes)
  └── fixes Bug 1 (boot log auth)
  └── fixes Bug 5 (quick commands auth)

Bug 3 (rbash → bash)
  └── fixes Bug 5 (iframe terminal usable)

Bug 2 (pods 500 → structured error)
  └── independent fix; improves UX even before Bug 4 lands
```

---

## Backend Briefs Filed

| Brief | Bug | Description |
|-------|-----|-------------|
| `BV__host-api-key-via-ec2-tag.md` | 4 | Tag EC2 instance + expose key in GET /api/nodes |
| `BV__pods-500-error-handling.md` | 2 | Wrap pods route in try/except; return 503 |
| `BV__sidecar-rbash-fix.md` | 3 | Change sidecar shell from rbash to bash |

---

## Frontend Changes Required

None for Bugs 1–5 once backend fixes land. The frontend code is already correct:
- `_populatePanes()` in `admin.js` uses `s.host_api_key || ''` as fallback
- `_fetchBootLog()` sends `X-API-Key` when key is non-empty
- `sg-compute-host-shell` sends `X-API-Key` when key is non-empty

**One verification needed:** Confirm `GET /api/nodes` response nodes include `host_api_key` field after Bug 4 backend fix ships.
