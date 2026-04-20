# QA Refactoring — Playwright Service Modes, Sidecar & CI-Simulated Auth Upstream

**version** v0.21.4
**date** 2026-04-20
**from** Architecture session
**to** QA (lead), Dev, DevOps
**supersedes** `v0.21.3__dev-brief__qa-refactoring-playwright-modes-traffic.md`
**type** Dev brief

---

## What changed since v0.21.3

The v0.21.3 brief scoped the workflow. Between then and now, the infrastructure caught up:

- **P1 (agent_mitmproxy upstream forwarding)** shipped — v0.1.33 of the sidecar image
- **P2 (Playwright proxy-API cleanup)** shipped — `Proxy__Auth__Binder` and the proxy-auth schemas are gone; `build_proxy_dict()` now reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` from env (boot-time)
- **P3 (`docker-compose.yml`)** shipped — both containers on a shared `sg-net` bridge, sidecar proxy port Docker-network-only
- **`sg-ec2` CLI** shipped — 17 subcommands including `create`, `smoke`, `screenshot`, `health`, `bake-ami`, `connect`, `exec`, `logs`, `forward`
- **AMI bake pipeline** shipped — GH Actions workflow produces tested, tagged AMIs from the combined two-container topology

The brief below is the v0.21.3 plan updated against what now exists, plus a new piece: **CI-simulated authenticated upstream** so that every Mode 3 test path (including the sidecar → authenticated-upstream chain) runs in GitHub Actions without real credentials.

---

## Recap — the architecture

```
EC2 instance (or AMI — identical artefact)
│
├── Playwright container
│   ├── FastAPI :8000 (browser control API)
│   ├── Chromium / Firefox / WebKit
│   └── All browser traffic routed to http://agent-mitmproxy:8080
│
└── agent_mitmproxy container (sidecar)
    ├── mitmweb :8080 (proxy, Docker-network-only)
    ├── :8081 (web UI, internal)
    ├── uvicorn :8000 (admin API — exposed as :8001 on host)
    ├── Bundled addons: Default_Interceptor + Audit_Log
    └── Optional upstream forwarding via AGENT_MITMPROXY__UPSTREAM_*
```

100% browser traffic visibility. Runtime policy hot-swap. Correlation headers (`X-Agent-Mitmproxy-Request-Id`) through the chain. Single artefact — same image list ships to docker-compose (dev), the `sg-ec2` CLI (ephemeral), and AMI (production / Marketplace).

---

## The four QA workflows

### Workflow A — Local Docker (CI pipeline)

**Use case:** PRs, unit + smoke runs, no authenticated upstream needed.

**How:** `docker compose up` brings up both containers on the shared network. Test runner hits `http://localhost:8000` on the Playwright service; the sidecar is reachable on `http://localhost:8001` for admin / audit-log inspection. No AWS, no Lambda, no ephemeral EC2.

**What the test confirms:**
- Playwright service boots, browsers launch, navigate + screenshot succeed
- Browser traffic does traverse the sidecar (verify via `X-Agent-Mitmproxy-Request-Id` response headers)
- Audit-log lines on the sidecar's stdout match the number of flows

**What's ready today:** `docker-compose.yml` at repo root. `.env.example` documents the env-var contract. `tests/docker/test_Local__Docker__SGraph-AI__Service__Playwright.py` already has lifecycle helpers — QA wraps this.

**What QA writes:** a Python client that drives the REST API (POST `/browser/navigate`, `/browser/screenshot`, `/browser/get-content`, etc.) and a suite of test cases that exercise the standard flows. First batch of tests is the smoke suite; grows over time.

### Workflow B — Lambda (tests from Claude Code)

**Use case:** running test suites from Claude Code sessions against the deployed Lambda. Lower-friction than standing up EC2 for every test run; high-fidelity to what real customers hit.

**How:** Test runner posts to the Lambda's Function URL with the API-key header. Same REST API as Workflow A.

**What the test confirms:**
- Deployed Lambda responds to the full API surface
- Direct-to-internet browsing works (no sidecar on Lambda — that's the deliberate architectural choice)
- Smoke tests against real targets (example.com, sgraph.ai) succeed

**What's ready today:** two Lambdas deployed per stage (`sg-playwright-<stage>` agentic, `sg-playwright-baseline-<stage>` fallback). Public Function URL with the IAM two-statement auth fix. API-key middleware enforced.

**What QA writes:** same client as Workflow A, configured to hit the Function URL instead of `localhost`. Test suite mostly overlaps with A — the differences are small (no `agent_mitmproxy` audit log to cross-check on Lambda, no sidecar response headers).

### Workflow C — Lambda (final QA + scheduled smoke tests)

**Use case:** pre-release QA + regular synthetic traffic against production. This is the "heartbeat" the v0.21.3 brief called out.

**How:** Same Lambda path as Workflow B; difference is scope. Runs on a CloudWatch schedule (hourly), hits the production deployment, writes results to the observability pipeline.

**What the test confirms:** production is alive, the end-to-end workflows work, response times stay in range, visual regressions caught via screenshot diffs.

**What's ready today:** the Lambda; the CLI's `screenshot` command gives a template for the per-run capture.

**What QA writes:**
1. Test cases that exercise a full product workflow — e.g. create an SG/Send transfer, download it, create a vault, open the vault in the browser, screenshot
2. A dispatcher (CloudWatch Events → Lambda invocation or GitHub Actions scheduled workflow) that runs the suite on the schedule
3. Observability wiring — results → OpenSearch / dashboards for files-accessed-per-hour, vaults-created-per-hour, response-times, error-rates

### Workflow D — Ephemeral EC2 via `sg-ec2` (full capability including sidecar)

**Use case:** test the complete architecture including the sidecar. This is the only path that exercises the two-container unit.

**How:** the `sg-ec2` CLI lifecycle:

```bash
# Spin up a fresh instance (takes ~2-3 min total: launch + boot + docker pull + healthy)
sg-ec2 create --stage qa-ephemeral-$(date +%s)

# Quick confirmation it's live
sg-ec2 health qa-ephemeral-XXX

# Smoke suite — 3 requests per URL, cold+warm timing, screenshot per URL, mitmproxy flow count
sg-ec2 smoke qa-ephemeral-XXX

# Run QA-specific tests (pointed at the EC2 public URL)
QA_TARGET_URL=$(sg-ec2 info qa-ephemeral-XXX --json | jq -r .public_url)
pytest tests/qa/ -v

# Always clean up
sg-ec2 delete qa-ephemeral-XXX
```

**What the test confirms:** the full two-container unit works end-to-end — browser → sidecar → internet, audit log populated, correlation headers plumbed through, sidecar admin API responsive.

**What's ready today:** the CLI. All commands above exist and are tested.

**What QA writes:** the `tests/qa/` suite (see below), plus a wrapper (shell or pytest fixtures) that manages the `sg-ec2 create` / `sg-ec2 delete` lifecycle with proper cleanup on failure. The CLI's existing `smoke` command is a template for what these tests look like.

### Workflow E (new) — CI-simulated authenticated upstream

**Use case:** prove the sidecar's upstream-forwarding mode works without needing real `akeia` credentials in the GitHub Actions environment.

**The trick.** Stand up a **second** `agent_mitmproxy` (or vanilla mitmproxy) **inside the GH runner** configured with `--proxyauth user:pass`. Point our real sidecar at it as its upstream. This reproduces the Phase 1.11 chain using only runner-local infrastructure.

```
GH Actions runner
│
├── Playwright container ─────────▶ sidecar :8080 ──────▶ fake upstream :9090
│                                   (no auth)              (--proxyauth qa:qa-pass)
│                                   AGENT_MITMPROXY__       │
│                                   UPSTREAM_URL=           ▼
│                                   http://fake-upstream    Internet
│                                   :9090                   (via the auth chain)
│
└── Browser requests exercise the full authenticated-upstream path that
    production uses against the real akeia proxy — but fully containerised
    and credential-free from the repo's perspective.
```

**Why this works.** The sidecar image already has upstream mode (`AGENT_MITMPROXY__UPSTREAM_{URL,USER,PASS}`). The fake upstream is a second mitmproxy container running in forward-proxy mode with `--proxyauth`. Our sidecar talks to it with preemptive auth (same pattern Phase 1.11 validated). The fake upstream accepts the auth and forwards to the target.

**What the test confirms:**
- Sidecar's upstream-mode actually forwards with the auth header
- Browser traffic successfully traverses the two-hop chain
- Response headers carry both sidecar markers (`X-Agent-Mitmproxy-*`) and target-reachability proof
- The fake upstream's access log shows `Proxy-Authorization: Basic <creds>` on every CONNECT

**What's ready today:** the sidecar image's upstream mode (v0.1.33). The Phase 1.11 scripts in `79ryx84c/debug-session/phase-1_11__upstream-mode/scripts/` are almost exactly the template — they start a local mitmdump as the "remote", and a second one in upstream mode as the sidecar. QA adapts those to GH Actions services.

**What QA writes:**
- A GH Actions workflow that spins up three services (or `docker compose -f docker-compose.test.yml`): Playwright, sidecar (in upstream mode), fake upstream
- A test suite that navigates to targets and asserts end-to-end traversal via response-header markers
- Ideally: add this as a job in `ci__agent_mitmproxy.yml` so it runs on every sidecar PR

### One abstraction layer for all five

All five workflows hit the same REST API surface. A single Python client handles dispatch:

```python
# QA code (same in every mode)
client = PlaywrightClient.from_env()      # reads QA_MODE env var: local | lambda | ec2
resp   = client.navigate("https://example.com", wait_until="load")
png    = client.screenshot()
audit  = client.get_audit_log() if client.has_sidecar() else None   # only Workflows A, D, E
```

The client is **new code QA owns** — it doesn't exist in the service repo. Suggested location: a small `sg-playwright-qa` repo (or a `tests/qa/client/` folder here). The existing `Local__Docker__SGraph_AI__Service__Playwright` and `sg-ec2` CLI's HTTP-call patterns are good templates to lift from.

---

## Current API surface (verified against dev branch, commit `f1edc54`)

The v0.21.3 brief showed `/session/*` endpoints. Current reality:

```
POST /browser/navigate          — navigate to URL, return final_url + duration_ms
POST /browser/click             — click a selector
POST /browser/fill              — fill a form field
POST /browser/get-content       — HTML body of current page
POST /browser/get-url           — current URL
POST /browser/screenshot        — PNG bytes, viewport shorthand supported
POST /sequence/execute          — multi-step workflow in one call (declarative)
GET  /health/info               — service name + version
GET  /health/status              — liveness checks
GET  /health/capabilities        — what this service can do
```

**Every call is self-contained.** No session to start or close. If you need multi-step flows where state must persist across calls, use `POST /sequence/execute` with the whole workflow in one payload. This is the stateless model the architecture explicitly endorses — it's what lets the service run behind NLB + ASG without stickiness.

**Auth:** every request requires `X-API-Key: <value>` (name and value are per-deployment via env vars `FAST_API__AUTH__API_KEY__NAME` and `FAST_API__AUTH__API_KEY__VALUE`).

---

## Acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| 1 | **Workflow A** — QA tests pass against the local-docker-compose unit | `docker compose up` + `pytest tests/qa/` succeeds |
| 2 | **Workflow A** — sidecar audit-log shows one entry per browser HTTP flow | Run test suite, `docker compose logs agent-mitmproxy | grep '\{' | wc -l` > 0 and correlates with flow count |
| 3 | **Workflow B** — QA tests pass against the deployed Lambda from a Claude Code session | Function URL + API key + suite green |
| 4 | **Workflow C** — scheduled test runs against production Lambda at a fixed interval | CloudWatch Events (or GH scheduled workflow) triggers the suite; results appear in observability pipeline |
| 5 | **Workflow C** — observability dashboards show synthetic traffic metrics | Files-accessed/hour, vaults-created/hour, response times visible |
| 6 | **Workflow D** — `sg-ec2 create → smoke → delete` cycle completes green | Exit code 0, screenshots captured, sidecar audit-log non-empty |
| 7 | **Workflow D** — full cycle wall-clock under 5 minutes | Timed in CI |
| 8 | **Workflow E** — CI-simulated authenticated upstream chain proves sidecar upstream mode works | GH Actions job: spin up the 3-container stack, run a navigation test, assert the target response + fake-upstream access log shows `Proxy-Authorization` on every CONNECT |
| 9 | **Workflow E** — auth creds live only in GH Actions secrets / runner env, never in the repo | Audit the workflow YAML and fake-upstream config |
| 10 | Single `PlaywrightClient` abstraction drives all five workflows | Same test code; mode dispatched via `QA_MODE` env |
| 11 | No ad-hoc Playwright setups remain in QA codebase | `grep -r 'playwright.sync_api\|playwright.async_api' tests/ qa/` returns only the PlaywrightClient implementation |
| 12 | P1 screenshot suite against a stable target set produces visual baseline | Golden images committed; diff check in CI catches regressions |

---

## What was in v0.21.3 but not in this update

- **The `/session/*` API shape** — replaced with the actual `/browser/*` + `/sequence/*` surface
- **The `PlaywrightClient(mode=...)` code snippet as if it exists** — corrected to "QA writes this; here are the templates to lift from"
- **Three modes** — now five, because Workflow E is a genuinely distinct case that warrants its own test shape, and splitting Lambda into B (interactive from Claude Code) and C (scheduled synthetic traffic) matches how they'll actually run

---

## Unblocked by recent work

| Piece | Before | Now |
|---|---|---|
| `docker-compose.yml` | Didn't exist | Shipped — P3 |
| `Proxy__Auth__Binder` dead code | Still in repo | Deleted — P2 |
| `proxy.auth` in API schemas | Still live | Deleted — P2 |
| Combined paired-container EC2 | Two separate spike scripts | Unified in `sg-ec2 create` (UserData renders compose + brings up both) |
| AMI publishing pipeline | Not started | Shipped — GH Actions + CLI commands |
| Smoke test template | Only `/health/status` ping | `sg-ec2 smoke` — cold/warm timing, mitmproxy flow counts, screenshot per URL |
| CI integration-test job | Gated `if: false` | Available to turn on for Workflows A + E |

---

## Still to ship before this can land fully

1. **`PlaywrightClient` Python library** — QA writes; ~1-2 days
2. **Workflow E docker-compose-for-CI** (three-service stack: Playwright + sidecar + fake upstream) — ~half day
3. **The GH Actions job** that runs Workflow E — ~half day
4. **Scheduled Workflow C wiring** (CloudWatch Events + observability pipeline) — ~1-2 days depending on dashboard scope
5. **QA test suite content** — open-ended; first batch is whatever product-critical flows matter most

Recommended order: 1 → 2 → 3 → 4. Items 1 and 5 can run in parallel to the others.

---

## Related docs

- `team/humans/dinis_cruz/briefs/04/19/revised-ec2-architecture/` — the architecture this workflow exercises
- `team/comms/plans/v0.1.33__proxy-gateway-p1-and-p2.md` — P1 + P2 implementation plan (both shipped)
- `team/claude/debriefs/2026-04-20__proxy-gateway-p1-p2.md` — debrief of the P1/P2 session
- `team/humans/dinis_cruz/claude-code-web/04/20/10/ec2-ecr-deployment-guide.md` — operator guide for the `sg-ec2` flow
- `team/humans/dinis_cruz/claude-code-web/04/20/10/devops-sre-observability-brief.md` — observability pipeline context for Workflow C
- vault `79ryx84c/debug-session/phase-1_11__upstream-mode/` — source of truth for the Workflow E pattern

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
