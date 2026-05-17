# Proposed — What Does NOT Exist Yet (v0.1.31 / v0.1.32)

See [README.md](README.md) for the index and split rationale.

**Rule:** every item on this page must be labelled as "PROPOSED — does not exist yet" when referenced in briefs, reviews, or external comms. Moving an item off this list requires a matching entry on one of the `01__playwright-service.md` / `02__agent-mitmproxy-sibling.md` / `03__docker-and-ci.md` / `04__tests.md` pages.

---

## Playwright (carried forward)

- `AGENTIC_ADMIN_MODE=full` with `POST /admin/reload` — deferred (needs auth).
- Per-layer SKILL files for `agentic_fastapi` and `agentic_fastapi_aws` — deferred.
- Lockdown layers / declared narrowing — deferred (`declared_narrowing = []`).
- Repo split into `api/` + `container/` packages — deferred.
- PyPI publishing of `agentic_fastapi` / `agentic_fastapi_aws` — deferred.
- Docker Hub publishing of base images — deferred.
- Sidecar enforcement layer — deferred.
- Two-track CI pipeline split — deferred.
- **v0.1.24 items still open:** 10 deferred `Step__Executor` action handlers, real vault HTTP client, `osbot-aws` S3 adapter for `Artefact__Writer`, CI mitmproxy sidecar for proxy-auth coverage (see note below), warm-browser pool, `__to__main` / `__to__prod` deploy tests, client registration helpers, per-route API-key scoping, `POST /browser/batch`.

---

## agent_mitmproxy (v0.1.32 — phase 1 ships the scaffolding only)

- `POST /config/interceptor` — upload / replace the live interceptor script. Read-only endpoint landed; write-side + reload is phase 2.
- `Build__Docker__Agent_Mitmproxy` helper class (the Playwright equivalent stages the build context and shells the SDK directly). Today the CI workflow shells `docker build` directly with repo-root context; no staging class exists.
- `tests/docker/test_Build__Docker__Agent_Mitmproxy.py` + `test_ECR__Docker__Agent_Mitmproxy.py` deploy-via-pytest harness — the Playwright pipeline has these; the mitmproxy one drives the build + push inline in the workflow step.
- `tests/integration/` for the mitmproxy container — no container-level smoke test yet. CI builds + pushes the image but does not pull it back and exercise the admin API.
- End-to-end proxy-auth CI test — requested in the v0.1.24 deferred list. The mitmproxy image is now the obvious vehicle for this sidecar but no wiring exists yet.
- EC2 deploy via CI — intentionally out of scope for phase 1. `scripts/provision_mitmproxy_ec2.py` runs on-demand from an operator laptop; no `workflow_dispatch` hook calls it yet.
- Auth-protected mitmweb UI — today `Routes__Web` exposes the UI through the API-key-gated admin API, but the Basic `--proxyauth` that mitmweb itself enforces is independent. No SSO / federated auth; spike-grade creds only.
- Addon registry hot-reload — the mitmweb process is restarted by supervisord on crash, but the addon list is not reloadable at runtime (would need a SIGHUP handler or a management endpoint).
- Prometheus scrape of app metrics from Playwright/mitmproxy via Prometheus — auth bridge needed (`X-API-Key` vs Prometheus `authorization` mismatch). Infrastructure metrics (cadvisor, node-exporter) already scraped. App metrics accessible manually via `sg-ec2 metrics`.
