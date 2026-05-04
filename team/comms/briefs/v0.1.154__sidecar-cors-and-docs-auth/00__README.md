# v0.1.154 — Sidecar: CORS Middleware + `/docs-auth` Endpoint

**Status:** REQUEST — blocking UI features  
**Owner:** backend (host control plane — `sg_compute/host_plane/`)  
**Audience:** Dev  
**Raised by:** UI session — branch `claude/review-sonnet-ui-work-1QSGb`  
**Date:** 2026-05-04

---

## Problem

The sidecar (`Fast_API__Host__Control`, port 19009) has no CORS headers.
The Admin Dashboard is served from `http://localhost:10071` (dev) or a different
origin in prod. Every direct fetch from the UI to the sidecar is blocked by the
browser:

```
Fetch error: Failed to fetch http://13.40.49.210:19009/openapi.json
Possible cross-origin (CORS) issue? The URL origin (http://13.40.49.210:19009)
does not match the page (http://localhost:10071).
```

**Affected UI features:**
- `sp-cli-host-api-panel` — Swagger UI cannot load `/openapi.json`
- `sp-cli-nodes-view` Pods tab — `/pods/list`, `/host/status` fetches blocked
- Pods stats (`/pods/{name}/stats`) and logs (`/pods/{name}/logs`) blocked
- Host shell (`/host/shell/execute`) blocked
- Boot log (`/host/logs/boot`) blocked

In short: **everything** that makes a fetch call from the admin page to the sidecar
is broken. The iframe-based Swagger `/docs` view works because it runs from the
sidecar's own origin.

---

## Two changes needed

| # | What | Why |
|---|------|-----|
| 1 | Add CORS middleware to `Fast_API__Host__Control` | Unblocks all direct fetch calls (Pods, Terminal, stats, logs) |
| 2 | Add `GET /docs-auth?apikey=` endpoint | Serves Swagger UI with key pre-injected; iframe loads same-origin so no CORS needed for Swagger itself |

---

## Files in this brief

| File | Content |
|------|---------|
| `00__README.md` | This file |
| `01__cors-middleware.md` | CORS config spec — exact middleware call needed |
| `02__docs-auth-endpoint.md` | `/docs-auth` endpoint spec with HTML template |
