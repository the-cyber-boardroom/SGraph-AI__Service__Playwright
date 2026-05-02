# v0.1.140 — Host Control Plane UI

**Status:** READY TO BUILD  
**Owner:** frontend session (this agent)  
**Audience:** dev, architect  
**Backend shipped:** branch `claude/continue-playwright-refactor-xbI4j` (commit 11c2a08)

---

## Goal

Add two new tabs to every plugin detail panel in the Admin Dashboard:

- **Terminal tab** — run allowlisted shell commands on the EC2 host via `POST /host/shell/execute`
- **Host API tab** — Swagger iframe for the instance's own FastAPI control plane at `{host_api_url}/docs`

This makes each running stack self-describing: you can inspect containers, check disk/memory, and browse the full host API surface without SSH or the AWS console.

---

## What the Backend Shipped

The backend session built and pushed:

| What | Where | Notes |
|------|-------|-------|
| `sgraph_ai_service_playwright__host` package | repo root | FastAPI on port 9000 per EC2 host |
| `GET /host/status` | host API | CPU, mem, disk, uptime, container count |
| `GET /host/runtime` | host API | docker\|podman + version |
| `POST /host/shell/execute` | host API | allowlisted commands only |
| `WS /host/shell/stream` | host API | interactive rbash (Phase 2) |
| `GET /containers/list` | host API | all containers on the host |
| `Schema__Ec2__Instance__Info` | SP CLI | gained `host_api_url` + `host_api_key_vault_path` |

**The host API key** is generated at EC2 boot and stored in the vault at `host_api_key_vault_path`. It is a different key from the SP CLI management API key. The detail components must read it from vault-bus on `open(stack)`.

---

## The gap you need to close first (Task 0)

`Schema__Stack__Summary` (what `/catalog/stacks` returns and what `sp-cli:stack.selected` carries) does **not** yet have `host_api_url` or `host_api_key_vault_path`. Those fields exist only on `Schema__Ec2__Instance__Info`.

You have two options — pick whichever fits the session:

**Option A (preferred):** Add both fields to `Schema__Stack__Summary` and `Stack__Catalog__Service.list_all_stacks()`. Each plugin's info schema already has `public_ip`; derive the URL from it:
```python
# in Stack__Catalog__Service.list_all_stacks()
host_api_url            = f'http://{info.public_ip}:9000' if str(info.public_ip) else '',
host_api_key_vault_path = f'/ec2/{info.stack_name}/host-api-key',
```

**Option B:** Derive both fields client-side in the shared widget:
```javascript
const host_api_url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
const vault_path   = stack.host_api_key_vault_path || `/ec2/${stack.stack_name}/host-api-key`
```

Option B requires no backend change and unblocks all UI tasks immediately. Option A is cleaner long-term.

---

## Files in this brief

| File | Content |
|------|---------|
| `00__README.md` | This file — status, context, task map |
| `01__what-backend-shipped.md` | Exact API surface, schemas, and auth contract your widgets must talk to |
| `02__ui-tasks.md` | 6 UI tasks with component specs, code patterns, and acceptance criteria |

Read `01__what-backend-shipped.md` before writing any code — it specifies every endpoint, the request/response shape, and exactly how the API key flows from vault-bus to the `X-API-Key` header.

---

## Out of scope for this slice

- Interactive xterm.js terminal (`WS /host/shell/stream`) — implement Phase 1 (command panel) first; the terminal is Task 2 in `02__ui-tasks.md` and can ship in a follow-on
- WebSocket API key auth backend wiring — the host FastAPI currently only validates `X-API-Key` header; WS needs a `?api_key=` query-param fallback (browser WS doesn't support custom headers); flag this to the backend session when ready
- `/metrics` Prometheus scraping into cost tracker — future slice
