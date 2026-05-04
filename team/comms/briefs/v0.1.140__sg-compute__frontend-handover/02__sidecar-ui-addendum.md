# Addendum — Sidecar UI Work (session claude/review-sonnet-ui-work-1QSGb)

**Date:** 2026-05-04
**Adds to:** `README.md` in this directory
**Branch:** `claude/review-sonnet-ui-work-1QSGb` (merged to dev via PRs)

---

## What this session built

This session ran in parallel with the backend B-phases and focused on the
**host-plane sidecar UI** and **DevOps hardening**. It did not touch F1/F2/F5
(those are still unstarted). Here is what changed:

---

### A. New web component — `sp-cli-nodes-view`

`sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-nodes-view/v0/v0.1/v0.1.0/`

A full node-detail panel replacing the simpler `sp-cli-stacks-pane` concept.
Six tabs:

| Tab | What it shows |
|-----|---------------|
| **Overview** | KV pairs: type, state, IPs, instance ID, uptime |
| **Boot Log** | `/host/logs/boot` from sidecar |
| **Pods** | `/containers/list` from sidecar |
| **Terminal** | xterm.js terminal via iframe to `/host/shell/page` |
| **Host API** | Swagger iframe to `/docs-auth?apikey=…` |
| **EC2 Info** | Instance, network, IAM, tags, volumes, security groups — fetched from SP CLI `/catalog/ec2-info` (NOT the sidecar — the node has no IAM) |

**Current field names it reads from the stack object:**

```js
stack.stack_name         // node identifier  — OLD vocab
stack.type_id            // spec identifier  — OLD vocab
stack.state              // 'running' | 'pending' | …  — OLD vocab
stack.public_ip
stack.instance_id
stack.region
stack.host_api_url       // custom field — NOT in Schema__Node__Info
stack.host_api_key       // custom field — NOT in Schema__Node__Info
stack.host_api_key_vault_path  // custom field — NOT in Schema__Node__Info
```

**⚠️ Critical for F2:** When the frontend switches to `GET /api/nodes`,
`host_api_url`, `host_api_key`, and `host_api_key_vault_path` will be absent
from `Schema__Node__Info`. This will silently break the Terminal, Host API,
and Pods tabs. See §C below.

---

### B. New web component — `sp-cli-host-shell`

`sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/`

Drives the Terminal tab. Uses the iframe pattern (not direct xterm.js + WebSocket
from the admin origin) to avoid cross-origin WebSocket auth issues:

- Iframe points at `{host_api_url}/host/shell/page` — served by the sidecar,
  same-origin to the sidecar, so the auth cookie is sent automatically in the
  WS handshake.
- "🔑 Authenticate" button loads `/auth/set-cookie-form` **inside the iframe**
  (not a popup). After the user sets the cookie, the form auto-redirects back
  to `/host/shell/page`.
- Quick Commands panel stays separate — uses `X-API-Key` header via fetch,
  no cookie needed.

---

### C. New sidecar routes (`sg_compute/host_plane/fast_api/`)

| Route | Purpose |
|-------|---------|
| `GET /auth/set-cookie-form` | Styled HTML form to set the API-key cookie |
| `POST /auth/set-auth-cookie` | Sets the cookie; redirects iframe back to shell page |
| `GET /host/shell/page` | Serves xterm.js terminal page (excluded from auth) |
| `GET /docs-auth?apikey=…` | Swagger UI with pre-injected key (excluded from auth) |

Both auth paths are in `_AUTH_FREE_PATHS` and bypass the API-key middleware.

---

### D. CORS fix on `Fast_API__Host__Control`

`sg_compute/host_plane/fast_api/Fast_API__Host__Control.py`

The auth middleware was short-circuiting 401 responses before `CORSMiddleware`
could add headers — browsers saw a CORS error instead of a 401.

Fix (two-layer):
1. `_Middleware.dispatch()` stamps `access-control-allow-origin`,
   `access-control-allow-credentials`, `vary` on every response it produces.
2. `CORSMiddleware` switched from `allow_origins=["*"]` + `allow_credentials=False`
   to `allow_origin_regex=r".*"` + `allow_credentials=True`.

`["*"]` + credentials is silently broken in browsers; the regex pattern reflects
any origin correctly. `samesite='lax'` on the cookie prevents CSRF from third-party
pages sending cross-origin credentialed requests.

---

### E. EC2 Info endpoint moved to correct service

`sgraph_ai_service_playwright__cli/catalog/fast_api/routes/Routes__Stack__Catalog.py`

`GET /catalog/ec2-info?instance_id=&region=` calls `describe_instances`,
`describe_volumes`, `describe_security_groups` via boto3. Correctly placed in
the SP CLI service (which has IAM). The sidecar running on EC2 nodes has no
IAM role.

---

### F. Auto-polling removed for running nodes

`sp-cli-nodes-view.js` no longer polls `GET /host/status` every 15s once a
node is running. The background timer only fires for non-running nodes (5s, SP
CLI backend, same-origin) to detect the boot→running transition. Once running,
the timer is cleared and not restarted.

---

### G. CI pipeline refactoring

`ci-pipeline.yml` now:
- Detects `sg_compute/**` changes and runs a `build-and-push-host-image` job
  in parallel with the Playwright image job.
- `increment-tag` syncs `sg_compute/version` and `sg_compute/pyproject.toml`
  after bumping `sgraph_ai_service_playwright/version`.

`ci-pipeline__dev.yml` and `ci-pipeline__main.yml`:
- Added `sgraph_ai_service_playwright/version` and `sg_compute/version` to
  `paths-ignore` to prevent the version-bump commit from re-triggering CI.

`ci__host_control.yml`:
- Now `workflow_dispatch`-only (emergency manual rebuilds).
- Automatic builds handled by the main pipeline.

---

## Corrections to the main brief

### Taxonomy table update

Add this row to §3:

| Old value | New value | Notes |
|-----------|-----------|-------|
| `state: 'running'` | `state: 'ready'` | `sp-cli-nodes-view` checks `=== 'running'` everywhere — must be updated in F2 |
| `state: 'pending'` | `state: 'BOOTING'` | Confirm casing with backend |

### F8 status update

F8 ("host-plane `/containers/` → `/pods/` URL update") is **half done**:
`Routes__Host__Containers` is wired in the new sidecar. The frontend
`sp-cli-nodes-view` still fetches `/containers/list` — update to `/pods/list`
when that route exists on the sidecar.

### `sp-cli-nodes-view` vs `sp-cli-stacks-pane`

The brief mentions `sp-cli-stacks-pane` as the active-nodes list component.
`sp-cli-nodes-view` is a newer component that supersedes it for the node-detail
flow. Clarify ownership before F2 — likely `sp-cli-stacks-pane` becomes the
list sidebar and `sp-cli-nodes-view` is the detail panel.

---

## Critical risk for F2

`Schema__Node__Info` (returned by `GET /api/nodes`) does **not** include
`host_api_url`, `host_api_key`, or `host_api_key_vault_path`. These fields are
currently returned by the SP CLI's `/catalog/stacks` endpoint and drive the
Terminal, Host API, and Pods tabs in `sp-cli-nodes-view`.

When F2 switches the data source to `/api/nodes`, those tabs will silently stop
working.

**Resolution options (choose one before starting F2):**

1. **Extend `Schema__Node__Info`** with `host_api_url` (derived from `public_ip`
   + port 19009) and `host_api_key` (looked up from vault at list time).
2. **Secondary fetch**: after loading nodes from `/api/nodes`, do a parallel
   `/catalog/stacks` call for the host-plane extras and merge by `node_id`.
3. **Derive on the frontend**: compute `host_api_url` from `public_ip` directly
   in `sp-cli-nodes-view` (`http://{public_ip}:19009`). For `host_api_key`,
   fall back to vault lookup via `currentVault()` (already coded as fallback).

Option 3 is lowest-friction — `host_api_url` can always be derived from
`public_ip`, and the vault fallback for the key is already implemented.
