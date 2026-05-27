# user-journey — Proposed (does not exist yet)

**Domain:** `user-journey/proposed/` | **Last updated:** 2026-05-27

Everything here is **PROPOSED — does not exist yet.** The branch (see `../index.md`) delivers the full unit-verifiable platform — journey → worker → suite → conductor → tool-API → cockpit/chat → CLI → Docker runtime → env-JSON delivery — all green in-memory. What remains is the deployment shell (only exercised on real Docker / AWS / CI) plus a few deferred connections.

| ID | Proposed capability | Notes |
|----|---------------------|-------|
| P-1 | Worker + conductor **Docker images** (Dockerfiles) | ⚠ AUTHORED, never built — `docker/worker/` + `docker/conductor/`. Unverified until built on a Docker host. |
| P-2 | **Docker Hub CI** workflow | Build + push the worker/conductor images. Not started. |
| P-3 | EC2 **conductor-host** provisioning + lifecycle | `Ec2__AWS__Client` exists; the user-journey host stack (boot, docker-socket runtime, teardown) is not wired. |
| P-4 | **deploy-via-pytest** + live **load** runs | ⚠ Skeleton AUTHORED, never run — `tests/deploy/` (gated on `SG_UJ__DEPLOY_TEST=1` + Docker). The live high-`count` load run is not built. |
| P-5 | Interactive cockpit / chat screens exercised **live** | The Textual screens + chat launcher are built; only their pure cores are tested. No headless/live screen run yet. |
| P-6 | Vault-stored **suites by id** + a journey store | `Conductor__Client.start_suite_id` posts `{suite_id}`; conductor-side resolution and a journey catalogue are not built. |
| P-7 | mitmproxy **capture_client** wiring | ↔ PARTIAL — `Journey__Local__Runner` (and `sg user-journey run-local`) wire the capture client locally; the worker container `Journey__Worker__Entrypoint.main()` still passes `capture_client=None`. |
| P-8 | Suite **persistence / history** | Conductor state is in-memory; no durable run history or replay. |
| P-9 | One-command **local mitmproxy** launcher | Today `run-local --capture-url` needs a mitmproxy you start yourself (the agent-mitmproxy image/service). |
