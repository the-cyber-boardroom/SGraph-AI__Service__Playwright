# v0.1.140 — Post-Fractal UI: Host Control Plane + Terminal

**Status:** PROPOSED
**Owner:** frontend team (this Claude session) + backend/CLI team (separate session)
**Audience:** dev, architect
**Source brief:** `team/humans/dinis_cruz/briefs/05/02/` (human memo, 02 May 2026)

---

## Goal

Every running EC2 stack in the Admin Dashboard gets a **control plane** — a
FastAPI service running on the instance itself that exposes container
management, host metrics, and a shell. The Admin Dashboard surfaces this
through two new tabs on every detail panel: a **Terminal** tab (command
execution, progressing to an interactive xterm.js shell) and a **Host API**
tab (Swagger iframe for the instance's own `/docs` page).

This is the first step toward treating each EC2 instance as a self-describing
service rather than an opaque box.

---

## Background

The human brief (`v0.22.19__dev-brief__container-runtime-abstraction.md`)
identified the "Host FastAPI Control Plane" section as the next build target.
This brief operationalises that section for both teams.

---

## Files in this brief

| File | Audience | Content |
|------|----------|---------|
| `01__architecture-reference.md` | Both teams | Shared contract: API surface, schemas, security model, key flow, parallel build strategy |
| `02__backend-brief.md`          | CLI/backend team | 6 tasks: runtime abstraction → shell executor → FastAPI routes → schema additions → EC2 boot wiring → Docker image |
| `03__frontend-brief.md`         | Frontend team (this session) | 6 tasks: sp-cli-host-shell → sp-cli-host-terminal → detail tab wiring → sp-cli-host-api-panel → index.html → tests |

Read `01__architecture-reference.md` first — it defines the coupling point
(`host_api_url` + `host_api_key_vault_path` on the stack object) that lets
both teams build in parallel.

---

## Coupling point (only dependency between teams)

`Schema__Ec2__Instance__Info` gains two new fields (backend adds them):

```
host_api_url            : str   # "http://3.8.x.x:9000" — empty until boot complete
host_api_key_vault_path : str   # "/ec2/grand-wien/host-api-key"
```

Frontend mocks `http://localhost:9000` until backend is live.

---

## Out of scope (this slice)

- Kubernetes / minikube runtime adapter (future)
- Sidecar attach/detach API (`POST /containers/{name}/sidecars`)
- Prometheus `/metrics` scraping integration into the dashboard cost tracker
- AMI bake flow (covered in `v0.22.19__dev-brief__ephemeral-infra-next-phase.md`)
