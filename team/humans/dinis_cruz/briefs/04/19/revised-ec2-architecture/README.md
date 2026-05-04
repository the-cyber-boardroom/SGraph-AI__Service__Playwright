# Proposed Solution

Architecture for agent-controlled HTTP gateway.

**Runtime applicability at a glance:**
- **EC2 / direct compute** — full sidecar gateway design. Recommended production path.
- **Lambda / serverless** — out of scope for the sidecar. Lambda retains its current "Playwright goes direct to the internet" topology with no authenticated-proxy support. Detail in `01__architecture.md`.

## Docs in this folder

| File | Runtime | Purpose | Audience |
|---|---|---|---|
| `00__at-a-glance.md` | 🟢 EC2 (with 🟡 Lambda note) | One-page summary with topology diagrams | Everyone — channel-paste, standups |
| `01__architecture.md` | 🟢 EC2 only | The main architecture: sidecar as HTTP gateway, runtime topologies, packaging, security | Dev team — spec to build from |
| `02__origin-story.md` | 🟢 EC2 (investigation context) | The bug investigation that produced this architecture | Anyone who wants to verify the architecture is empirically grounded |
| `03__roadmap.md` | 🟢 EC2 (+ Lambda scope-out discussion) | What's shipped (v0.1.32), what's next, open questions | Product + dev planning |

🟢 EC2 = primary focus | 🟡 Lambda = noted / scoped out | 🔴 Not supported

## Reading order

- **First time looking:** `00__at-a-glance.md` → `01__architecture.md`
- **Need to challenge the design:** `02__origin-story.md` + the `../debug-session/` phases it links to
- **Planning next sprint:** `03__roadmap.md`

## Status

The design rests on empirically validated behaviour (Phases 1.6 → 1.12c in `../debug-session/`). The first piece of code — the `agent_mitmproxy` container image and admin FastAPI — landed in v0.1.32. Priorities 1 and 2 in the roadmap unblock the rest of the rollout.
