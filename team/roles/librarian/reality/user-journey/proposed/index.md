# user-journey — Proposed (does not exist yet)

**Domain:** `user-journey/proposed/` | **Last updated:** 2026-05-27

Everything here is **PROPOSED — does not exist yet.** The branch (see `../index.md`) delivers the full unit-verifiable platform — journey → worker → suite → conductor → tool-API → cockpit/chat → CLI → Docker runtime → env-JSON delivery — all green in-memory. What remains is the deployment shell (only exercised on real Docker / AWS / CI) plus a few deferred connections.

| ID | Proposed capability | Notes |
|----|---------------------|-------|
| P-1 | Worker + conductor **Docker images** (Dockerfiles) | One image per role, built on the `mcr.microsoft.com/playwright/python` base; pure authoring, no local build. |
| P-2 | **Docker Hub CI** workflow | Build + push the worker/conductor images. |
| P-3 | EC2 **conductor-host** provisioning + lifecycle | `Ec2__AWS__Client` exists; the user-journey host stack (boot, docker-socket runtime, teardown) is not wired. |
| P-4 | **deploy-via-pytest** + live **load** runs | Numbered deploy tests (`test_1__…`) + a gated high-`count` load run. |
| P-5 | Interactive cockpit / chat screens exercised **live** | The Textual screens + chat launcher are built; only their pure cores are tested. No headless/live screen run yet. |
| P-6 | Vault-stored **suites by id** + a journey store | `Conductor__Client.start_suite_id` posts `{suite_id}`; conductor-side resolution and a journey catalogue are not built. |
| P-7 | mitmproxy **capture_client** wiring in the worker entrypoint / launcher | Network assertions degrade to an empty log until wired. |
| P-8 | Suite **persistence / history** | Conductor state is in-memory; no durable run history or replay. |
