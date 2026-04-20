# [EC2 + Lambda] Roadmap

**Runtime applicability:** Priorities 1–6 below are **EC2-only work** (the sidecar architecture). The "Open questions" section also covers Lambda + authenticated-proxy as an explicit scope-out discussion.
**Status:** Living doc — snapshot as of 2026-04-20
**For:** dev team + product planning

---

## What's shipped (v0.1.32) — EC2 track

The `agent_mitmproxy` package landed in the Playwright service repo. Concretely:

- **Docker image** — `agent_mitmproxy` deployable to ECR (`745506449035.dkr.ecr.eu-west-2.amazonaws.com/agent_mitmproxy`), with supervisord running `mitmweb` + `uvicorn` as siblings
- **Bundled addons** — `Default_Interceptor` (correlation IDs, timing headers) + `Audit_Log` (one JSON line per flow to stdout)
- **Admin FastAPI** (`:8000`) — routes for `/health`, `/ca/*` (CA cert fetch), `/config/interceptor` (hot-swap addon), `/ui` (internal mitmweb UI passthrough)
- **`provision_mitmproxy_ec2.py`** — spike-grade helper that spins up a t3.small EC2 with the image pulled, IAM role + SG + SSM access in place
- **CI pipeline** — unit tests for addons, docker helpers, provisioner; wiring into the existing test-gate-before-deploy flow
- **Env var contract** — `AGENT_MITMPROXY__*` for service config, `FAST_API__AUTH__API_KEY__*` shared with Playwright

What's working:
- Image builds + pushes to ECR
- EC2 spike boots cleanly, API reachable, health check green
- `--proxyauth` downstream is functional on the image (though we will *not* use it in the Playwright-paired deployment — see Priority 1 below)
- Addons load and stamp headers correctly (unit tests pass)

---

## What's next — prioritised (🟢 EC2 track)

All items below apply to EC2 deployments. Lambda-specific questions are under "Open questions" further down.

### Priority 1: Upstream-forwarding mode + make downstream `--proxyauth` optional

**What:** two related changes to the `agent_mitmproxy` image:

1. **Upstream forwarding.** Extend the sidecar to run in `--mode upstream:$URL` when `AGENT_MITMPROXY__UPSTREAM_URL` is set, with preemptive auth via `--set upstream_auth=$USER:$PASS`.
2. **Downstream `--proxyauth` becomes optional.** Currently the supervisord config unconditionally passes `--proxyauth $USER:$PASS` to mitmweb. Teach entrypoint.sh to omit the flag when `AGENT_MITMPROXY__PROXY_AUTH_USER` and `_PASS` are unset — the paired-with-Playwright deployment relies on network isolation, not downstream HTTP auth. Keep the flag working when env vars ARE set, for anyone running the image standalone.

**Why (1):** this is what Phase 1.11 validated. It's the deliverable for anyone needing authenticated upstream-proxy support.

**Why (2):** Phase 1.11 proved Playwright can't reliably pass proxy credentials against an authenticated proxy — that's the bug the sidecar exists to work around. The sidecar must NOT require downstream auth when paired with Playwright in the two-container deployment. Security comes from network isolation (Docker network, no host port mapping).

**Size:** one-day PR — env vars added to `consts/env_vars.py`, entrypoint.sh extended to conditionally build the mitmweb command line, healthcheck extended to probe upstream if configured, tests added, version bumped to v0.1.33.

**Validation:** re-run Phase 1.11 tests against the deployed EC2 spike with upstream env vars set. Expected: identical success (235ms Chromium nav, 323ms Firefox nav, all response headers carrying upstream markers).

### Priority 2: Wire into Playwright service's container launch

**What:** teach the Playwright service to launch browsers with `proxy={'server': 'http://agent-mitmproxy:8080'}` — **no username, no password**. Remove the CDP `Proxy__Auth__Binder` workaround (it was never successfully validated and becomes dead code). Remove the `if proxy.auth is not None` branch in `build_proxy_dict` that tried to pass credentials for Firefox/WebKit — same reason.

**Why:** end-to-end integration. Once this lands, every browser spawned by the service automatically routes through the sidecar over the private Docker network. No credentials cross the browser boundary, sidestepping the Phase 1.11 bug entirely.

**Size:** small PR — simplify `Browser__Launcher.build_proxy_dict()` (it becomes a one-liner returning `{'server': SG_PLAYWRIGHT__PROXY_URL}`), delete `Proxy__Auth__Binder.py`, update tests, remove dead branches that handled the auth.username/auth.password path.

**Depends on:** Priority 1 part (2) — the sidecar image must support running without `--proxyauth`. If Priority 1 hasn't landed, Priority 2 still works *if* the sidecar is configured with matching env vars the Playwright service also knows, but that's the fragile path we're trying to leave behind.

### Priority 3: `docker compose` for local development

**What:** top-level `docker-compose.yml` that brings up both containers for local dev. Mounts source code for hot-reload. Binds API on `localhost:<dev-port>`.

**Why:** makes the two-container story real for developers. "Clone the repo, run `docker compose up`, hit `http://localhost:8000/browser/screenshot`" should just work.

**Size:** medium — compose file + `.env.example` + developer docs + making sure the shared Docker network is named explicitly so both containers find each other.

### Priority 4: NLB + ASG CloudFormation / Terraform

**What:** infrastructure-as-code to deploy the full topology described in `01__architecture.md`. Launch template pointing at the AMI, target group health checks, scaling policies, security groups.

**Why:** takes this from "we proved it works on one box" to "we can deploy it to production with a single command." Gates beta rollout.

**Size:** medium — depends on what's already in place for other services. If there's a template library for Playwright-service deploys, adapt it; otherwise start with a standalone CFN/TF module.

**Blocker:** none; can start any time after Priority 2 completes.

### Priority 5: AMI publishing pipeline

**What:** automate the packaging of an AMI containing the two pre-pulled Docker images + `docker compose` + systemd unit for boot. Publish via a private Marketplace-facing account initially; graduate to public Marketplace once we have a few customer deployments.

**Why:** product distribution channel. One-click deploy for customers, no need for them to understand ECR or Docker specifics.

**Size:** large — involves Packer (or similar) builds, AMI-image testing, Marketplace submission process, documentation for subscribers. Multi-week initiative, likely a separate workstream.

### Priority 6: Fluent-bit integration

**What:** stock the AMI with fluent-bit tailing the sidecar's stdout, filtering for JSON lines, shipping to OpenSearch.

**Why:** the `Audit_Log` addon emits JSON to stdout precisely because fluent-bit was the planned transport. Completes the observability story.

**Size:** small-to-medium — fluent-bit config, target OpenSearch endpoint (configurable), tested locally with a docker OpenSearch.

**Depends on:** where OpenSearch lives. If there's a shared central cluster, configure target. If every deployment gets its own, that's more plumbing.

---

## Open questions

### 🟢 Per-request upstream selection (EC2)

Phase 1.12b investigated whether a single sidecar could route different requests to different upstream proxies based on custom `X-Sidecar-Upstream` / `X-Sidecar-Auth` headers. Findings:

- **Routing works** — `flow.server_conn.via` is honored per-flow when sidecar is in upstream mode
- **Auth injection has a wrinkle** — `http_connect_upstream` fires with a newly-created flow, not the original, so per-flow auth must be looked up by address
- **The address-keyed workaround is viable** but has a concurrent-same-upstream-different-creds footgun

**Decision needed:** is per-request upstream an actual requirement?

- If yes: implement Tier 2 of the sidecar design — a pool of sidecars, one per unique `(upstream_url, upstream_auth)` tuple, spawned lazily by the Playwright service. No custom addon, no shared-state concerns, uses the built-in `upstream_auth`.
- If no: skip and re-scope if the need arises later.

My recommendation: **skip for now**, revisit only when we have a concrete customer need. Tier 1 (one boot-time upstream) handles the vast majority of use cases cleanly.

### 🟡 Lambda + authenticated-proxy support

**Current state:** Lambda deployments go direct to the internet. Authenticated-proxy support is not offered on Lambda (the bug from `02__origin-story.md` affects Lambda identically, and the sidecar workaround is EC2-only by construction).

If a Lambda-based authenticated-proxy use case emerges:

- Option A: external sidecar — Lambda Playwright points at an EC2-hosted sidecar reachable over the VPC. Works, but adds a network hop and cross-service latency.
- Option B: accept that Lambda can't proxy-with-auth. Document the limitation.

Again, **skip unless a customer needs it**. Lambda's current "direct-to-internet or direct-to-no-auth-proxy" story covers most Lambda use cases.

### Cert-pinning targets

Some target sites pin certificates (e.g., mobile banking apps that ship cert fingerprints in their Android APKs). mitmproxy's forged cert breaks these. Unlikely to affect the Playwright service's typical use cases (browsers, not native apps) but worth flagging if we ever target apps.

### Cost model for Marketplace

The t3.small baseline is ~$15/month. A warm-ASG floor of two instances is $30/month + NLB (~$18/month) + data transfer. Commercial offering needs margin over this. Pricing conversation is out of scope for this doc but blocks the Marketplace rollout.

---

## Non-goals

These are explicitly not in scope for the next few iterations, to keep the roadmap focused:

- **Multi-tenant isolation inside one container.** Each instance serves one tenant at a time (or mixes them indistinguishably). Tenant isolation is an ASG-level concern — different tenants get different ASGs.
- **Persistent browser sessions across requests.** Each API call is self-contained. No session state.
- **Custom browser builds.** Ship what Playwright's `install` command provides. Don't maintain our own Chromium fork.
- **WAF / DDoS protection at the sidecar.** This is the NLB's job or an external CDN's job. The sidecar is for observability + policy, not edge protection.

---

## Summary table

| Priority | Item | Size | Status |
|---|---|---|---|
| 1 | Upstream-forwarding mode | 1 day | Not started |
| 2 | Playwright service integration | Small | Not started |
| 3 | `docker compose` for dev | Medium | Not started |
| 4 | NLB + ASG IaC | Medium | Not started |
| 5 | AMI publishing pipeline | Large | Not started |
| 6 | Fluent-bit → OpenSearch | Small-medium | Not started |

Priorities 1 and 2 unblock the rest. Everything else can be parallelised once the integration works end-to-end.

---

## References

- `01__architecture.md` — the gateway architecture this roadmap builds toward
- `02__origin-story.md` — the investigation that motivated the sidecar design
- `../debug-session/` — empirical validation for everything claimed in 01 + 02
- `agent_mitmproxy/` — the code that exists today
