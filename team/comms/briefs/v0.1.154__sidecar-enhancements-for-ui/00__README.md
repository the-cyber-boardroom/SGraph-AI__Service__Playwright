# v0.1.154 — Sidecar Enhancements for UI

**Status:** REQUEST — awaiting backend implementation  
**Owner:** backend (host control plane)  
**Audience:** Dev, Architect  
**Raised by:** UI session — branch `claude/review-sonnet-ui-work-1QSGb`  
**Date:** 2026-05-04

---

## Context

The Admin Dashboard now shows an Active Nodes panel (`sp-cli-nodes-view`) with a
Containers tab, a Terminal tab, and a Host API tab per node. The sidecar running at
`http://{public_ip}:19009` on every Docker node is the sole channel between the UI
and the running EC2 instance.

The current sidecar surface (`GET /containers/list`, `GET /host/status`,
`GET /host/runtime`, `POST /host/shell/execute`) covers basic inspection. However
three common UI needs have no clean endpoint yet:

1. **Boot/setup log** — the user wants to see what happened during EC2 provisioning
2. **Container logs** — per-container log tail without going through the shell panel
3. **Live stats stream** — real-time CPU/mem/container metrics without full page re-polls

This brief specifies the exact endpoints the UI needs. Implementation details are
the backend's call — the shapes below are the minimum contract.

---

## Files in this brief

| File | Content |
|------|---------|
| `00__README.md` | This file — context and status |
| `01__requested-endpoints.md` | Exact endpoint specs with request/response shapes |
| `02__ui-integration-notes.md` | How the UI will call each endpoint; acceptance hints |
