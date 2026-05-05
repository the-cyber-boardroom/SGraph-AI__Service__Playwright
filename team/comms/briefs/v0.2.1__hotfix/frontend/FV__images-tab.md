# FV — Images Tab on Node Detail Panel

**Date:** 2026-05-05
**Branch:** `claude/sgcompute-frontend-v0.2-5sjIO`
**Status:** IMPLEMENTED (same session)
**Backend prerequisite:** `Routes__Host__Images` landed in dev (`f9361cc`, `b32f5a2`)

---

## What Was Added

The backend shipped a first-class `/images` resource group on the host control
plane sidecar. Six endpoints now exist without needing `--enable-shell`:

| Method | Path | Action |
|--------|------|--------|
| GET | `/images` | List all local images |
| GET | `/images/{name}` | Inspect one image |
| POST | `/images/load/from/local-path` | Load from host path |
| POST | `/images/load/from/s3` | Pull from S3 via node IAM role |
| POST | `/images/load/from/upload` | Multipart tar upload (up to 20 GiB) |
| DELETE | `/images/delete/{name}` | `docker rmi` |

---

## Frontend Changes

### New shared component: `sg-compute-images-panel`

Path: `components/sg-compute/_shared/sg-compute-images-panel/v0/v0.1/v0.1.0/`

Capabilities:
- Lists all images on the node (`GET /images`) — id, tags, size_mb, created_at
- Per-image Delete button (`DELETE /images/delete/{name}`)
- "Load from S3" form — bucket + key fields → `POST /images/load/from/s3`
- Refresh button; loading + error states

Calls the sidecar directly (same pattern as `sg-compute-host-api-panel`):
```js
const url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
const key = stack.host_api_key || ''
```
Auth header: `'X-API-Key': key` (empty key → 401; resolved when Bug 4 lands).

### Modified: `sg-compute-docker-detail`

Added "Images" tab (4th tab) to the Info / Terminal / Host API trio.
Import added for `sg-compute-images-panel`.

### Modified: `admin/index.html`

Added `<script type="module">` tag for the new shared component.

---

## Acceptance criteria

1. Images tab renders on docker detail panel.
2. With a live node + valid API key: image list populates.
3. Delete button removes image and refreshes the list.
4. Load from S3 form submits correctly (bucket + key required).
5. No API key → shows "No API key — calls require authentication" banner (resolved by Bug 4 fix).
