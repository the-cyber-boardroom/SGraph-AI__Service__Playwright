# [EC2] Architecture — Agent Mitmproxy as HTTP Gateway

**Runtime:** EC2 / direct-compute only. Lambda/serverless is explicitly out of scope (see *What this architecture does not cover* below).
**Status:** Design, grounded in empirical validation
**Context:** Playwright Service, with v0.1.32 `agent_mitmproxy` deliverable
**Date:** 2026-04-20

---

## TL;DR

**This entire architecture applies to EC2 deployments only.** Every Playwright container is deployed alongside an `agent_mitmproxy` container on the same EC2 instance. **All browser HTTP traffic routes through the sidecar** — there is no "direct" path on EC2. The sidecar:

- Audits every flow (one JSON line per request, stdout → fluent-bit → OpenSearch)
- Stamps correlation IDs and timing onto headers
- Exposes a runtime control plane (hot-swap interceptor addons, fetch CA cert, UI passthrough)
- Optionally forwards traffic through an authenticated upstream proxy

Two containers form one self-contained unit. The unit scales horizontally behind an NLB + ASG, runs locally via `docker compose` for dev, and is packageable as an AMI for AWS Marketplace.

**Lambda deployments do none of this.** On Lambda, Playwright goes direct to the internet with no sidecar, no addon pipeline, and no authenticated-proxy support. See *What this architecture does not cover* at the bottom.

---

## The gateway, not the fix

This document expands the earlier proxy-auth workaround (`02__origin-story.md`) into its final shape.

The proxy-auth investigation established one specific thing: *we need a local sidecar to handle upstream authentication correctly*. But once the sidecar exists, it becomes the natural control plane for every HTTP policy decision — not just an auth fixup. So the sidecar graduates from workaround to gateway.

Proxy auth is now *one use case* of the gateway. Other use cases that fall out of the same architecture for free:

- **Observability** — every request is logged, once, in a uniform format, at a single choke point
- **Correlation IDs** — the `X-Agent-Mitmproxy-Request-Id` header plumbs through every hop
- **Runtime policy updates** — swap an interceptor addon via admin API; the live proxy picks up new rules without a redeploy
- **CA distribution** — browsers (or other tooling) pull the mitmproxy CA over HTTPS and install it for trust
- **Future: rate limiting, content filtering, credential injection, response rewriting** — all addon-shaped, all hot-swappable

---

## Runtime topology — 🟢 EC2 only

The below describes the production target: EC2 deployments. The sidecar pattern is EC2-specific. For Lambda, see *What this architecture does not cover*.

### The two-container unit

```
┌─────────────────────────────────────────────────────────────────────┐
│  EC2 instance                                                       │
│                                                                     │
│  ┌──────────────────────────┐     ┌───────────────────────────────┐ │
│  │ playwright-service       │     │ agent_mitmproxy               │ │
│  │ container                │     │ container                     │ │
│  │                          │     │                               │ │
│  │  ┌────────────────────┐  │     │  ┌─────────────────────────┐ │ │
│  │  │ FastAPI            │  │     │  │ mitmweb                 │ │ │
│  │  │ /browser/screenshot│  │     │  │ :8080 proxy             │ │ │
│  │  │ + lifecycle mgmt   │  │     │  │ :8081 web UI (internal) │ │ │
│  │  └─────────┬──────────┘  │     │  │ (no --proxyauth)        │ │ │
│  │            │ spawns      │     │  │ -s addon_registry.py    │ │ │
│  │            ▼             │     │  └───────────┬─────────────┘ │ │
│  │  ┌────────────────────┐  │     │              │ supervisord   │ │
│  │  │ Playwright         │  │     │  ┌───────────┴─────────────┐ │ │
│  │  │ Chromium/FF/WK     │  │     │  │ uvicorn                 │ │ │
│  │  │ proxy=http://      │──┼─────┼─▶│ :8000 admin API         │ │ │
│  │  │   agent-mitmproxy:8080│ │     │  │ /ca /config /health /ui │ │ │
│  │  └────────────────────┘  │     │  └─────────────────────────┘ │ │
│  │                          │     │                               │ │
│  │ API callers ─────────┐   │     │                               │ │
│  │                      │   │     │                               │ │
│  └──────────────────────┼───┘     └───────────────┬───────────────┘ │
│                         │                         │                 │
└─────────────────────────┼─────────────────────────┼─────────────────┘
                          │                         │
                  :<api-port>                :<proxy-port>
                      (API)                (optional egress)
```

Both containers share the instance's Docker network. The Playwright container references the sidecar by its Docker-network name (e.g. `agent-mitmproxy`), not `localhost` — each container has its own loopback. Port exposure on the host:
- The Playwright container's API port (whatever the service binds) is what the NLB terminates.
- The sidecar's ports (`:8080` proxy, `:8000` admin) are NOT exposed to the public network. `:8000` is reachable internally for ops tooling. `:8080` is only consumed by the co-located Playwright container.

The **API request** from an outside caller never touches the sidecar. The **browser egress** always does. These are separate flows:

```
Caller  ─(API call)─▶  playwright-service  ─(spawns browser)─┐
                                                             │
                                                             ▼
                                    ┌──────────────────────────┐
                                    │  Browser egress ALWAYS  │
                                    │  routes through sidecar │
                                    └──────────────────────────┘
```

### Configuration surface

Two env var sets govern runtime behaviour.

**For `playwright-service`:**
```
SG_PLAYWRIGHT__PROXY_URL   = http://agent-mitmproxy:8080
```

That's it. **No proxy username/password.** This is deliberate — Phase 1.11 proved that passing proxy credentials from Playwright to the browser is exactly what fails against authenticated proxies. The sidecar is reachable over the private Docker network only, never exposed to the host or the outside world, so downstream auth on the sidecar is unnecessary defense-in-depth that would break things.

Security of the sidecar endpoint comes from network isolation, not from HTTP-level auth:
- The sidecar's `:8080` port is bound to the Docker network; it has no host-port mapping
- Only the co-located Playwright container can reach it (same Docker network, resolved via service name `agent-mitmproxy`)
- Nothing outside the EC2 instance can reach `:8080` — the EC2 security group ingress rules don't open that port externally

**For `agent_mitmproxy` sidecar:**
```
# Optional — only if traffic should go out via an authenticated upstream
AGENT_MITMPROXY__UPSTREAM_URL       = http://upstream:8080
AGENT_MITMPROXY__UPSTREAM_USER      = <upstream account>
AGENT_MITMPROXY__UPSTREAM_PASS      = <upstream secret>

# Shared API key for the admin API on :8000
FAST_API__AUTH__API_KEY__NAME       = X-API-Key
FAST_API__AUTH__API_KEY__VALUE      = <secret>
```

> **On the `AGENT_MITMPROXY__PROXY_AUTH_USER/_PASS` env vars in the current v0.1.32 image.** The image presently launches `mitmweb --proxyauth $USER:$PASS`, enforcing downstream HTTP basic auth on the proxy port. For the sidecar-paired-with-Playwright deployment this document describes, these should be left **unset** — the container detects the absence and omits `--proxyauth` from the mitmweb command line. This is a small change in `entrypoint.sh` / `supervisord.conf` and is part of Priority 1 in `03__roadmap.md`. Until that lands, the workaround is to set them to a known throwaway value that nothing outside the instance can see — but the proper fix is to make the flag conditional.

### Two modes, one image

The sidecar image is identical whether it forwards direct or forwards upstream. The switch is one set of env vars:

**Direct-forward mode** (no `AGENT_MITMPROXY__UPSTREAM_*` set):
```
Playwright ─▶ sidecar :8080 ─▶ TLS-terminates + logs + intercepts ─▶ Internet
```
All the addon-pipeline benefits, no authenticated upstream. Good for development, for direct-to-internet EC2 deployments, and for the AMI default.

**Upstream-forward mode** (`AGENT_MITMPROXY__UPSTREAM_URL` set):
```
Playwright ─▶ sidecar :8080 ─▶ [addons run] ─▶ upstream (with --upstream_auth) ─▶ Internet
```
Everything direct mode does, plus traffic tunnels through an authenticated upstream. This is the bug-fix case (`02__origin-story.md`) and the enterprise-deployment case.

The decision is per-container at boot time. Not per-request. If a caller needs per-request upstream selection, that's a future extension discussed in `03__roadmap.md`.

---

## Request flow

### Browser egress (direct mode)

```
Playwright-launched browser                agent_mitmproxy :8080               Target origin
       │                                          │                                 │
       │  CONNECT target.com:443                  │                                 │
       │  (no auth — private Docker network)      │                                 │
       │─────────────────────────────────────────▶│                                 │
       │                                          │                                 │
       │                                          │  TLS handshake with target      │
       │                                          │  using forged cert              │
       │                                          │                                 │
       │  200 Connection established              │                                 │
       │◀─────────────────────────────────────────│                                 │
       │                                          │                                 │
       │          ─ ─ ─ TLS handshake (browser ↔ sidecar, forged cert) ─ ─ ─        │
       │                                          │                                 │
       │                                          │      ─ ─ ─ TLS handshake to target ─ ─ ─
       │                                          │                                 │
       │  GET /                                   │                                 │
       │──────────────────────────────────────────┼────▶  [Default_Interceptor fires]
       │                                          │              stamps X-Agent-Mitmproxy-Request-Id
       │                                          │              stamps X-Agent-Mitmproxy-Request-Ts
       │                                          │                                 │
       │                                          │    GET / (with stamped headers) │
       │                                          │────────────────────────────────▶│
       │                                          │                                 │
       │                                          │           200 OK + body         │
       │                                          │◀────────────────────────────────│
       │                                          │                                 │
       │                                          │    [Default_Interceptor fires]  │
       │                                          │         stamps X-Agent-Mitmproxy-Elapsed-Ms
       │                                          │         stamps X-Agent-Mitmproxy-Version
       │                                          │                                 │
       │                                          │    [Audit_Log fires]            │
       │                                          │         JSON line → stdout      │
       │                                          │                                 │
       │  200 OK + body (stamped)                 │                                 │
       │◀─────────────────────────────────────────│                                 │
```

The addon pipeline is the critical bit. Every response gets correlation headers that plumb all the way back to the API caller, making cross-service debugging trivial. The audit log gives one JSON line per flow for centralised observability.

### Browser egress (upstream mode)

```
Playwright-launched browser    agent_mitmproxy :8080          Upstream proxy               Target
       │                              │                              │                       │
       │  CONNECT target.com:443      │                              │                       │
       │─────────────────────────────▶│                              │                       │
       │                              │  [Default_Interceptor fires] │                       │
       │                              │                              │                       │
       │                              │  CONNECT target.com:443      │                       │
       │                              │  Proxy-Authorization: Basic  │                       │
       │                              │   (preemptive, always)       │                       │
       │                              │─────────────────────────────▶│                       │
       │                              │                              │                       │
       │                              │  200 Connection established  │                       │
       │                              │◀─────────────────────────────│                       │
       │  200 Connection established  │                              │                       │
       │◀─────────────────────────────│                              │                       │
       │                              │                              │                       │
       │          ─ ─ ─ TLS handshake (browser ↔ sidecar, forged cert) ─ ─ ─                 │
       │                              │                              │                       │
       │  GET /                       │  forward GET /               │   GET /               │
       │─────────────────────────────▶│─────────────────────────────▶│──────────────────────▶│
       │                              │                              │                       │
       │  200 + body (stamped)        │        200 + body            │      200 + body       │
       │◀─────────────────────────────│◀─────────────────────────────│◀──────────────────────│
```

Two important properties from the Phase 1 investigation (see `02__origin-story.md`):

1. **Preemptive auth on every forward** — the sidecar adds `Proxy-Authorization` on the very first CONNECT to upstream, exactly like curl does. This sidesteps the retry-pattern bug that breaks Playwright browsers when they hit authenticated proxies directly.
2. **Per-flow isolation** — each browser flow has its own tunnel; concurrent flows don't contaminate each other's upstream connections.

---

## Scaling topology — NLB + ASG

Each EC2 instance is a self-contained two-container unit. No shared state, no cross-instance coordination, no session affinity required.

```
                          ┌──────────────────────────────────┐
                          │  Network Load Balancer           │
                          │  TLS termination on API port     │
                          └──────────────┬───────────────────┘
                                         │
                            ┌────────────┼────────────┐
                            │            │            │
                    ┌───────▼─────┐ ┌───▼─────────┐ ┌─▼───────────┐
                    │  EC2 #1     │ │  EC2 #2     │ │  EC2 #N     │
                    │             │ │             │ │             │
                    │ playwright  │ │ playwright  │ │ playwright  │
                    │ + sidecar   │ │ + sidecar   │ │ + sidecar   │
                    │             │ │             │ │             │
                    └─────────────┘ └─────────────┘ └─────────────┘
                            ▲            ▲            ▲
                            └────────────┼────────────┘
                                         │
                          ┌──────────────┴───────────────────┐
                          │  Auto Scaling Group              │
                          │  min/max/desired + health checks │
                          │  launch template: custom AMI     │
                          └──────────────────────────────────┘
```

### Why this works cleanly here

Every API call is fully self-contained. The caller posts to `/browser/screenshot` with a URL; the service launches a fresh browser, navigates, returns a PNG, closes the browser. The entire lifecycle fits inside one NLB-balanced request. **No session stickiness is needed** — the next call from the same caller can land on any instance.

This is what makes horizontal scaling trivial. The ASG picks instances by load (CPU, request count, or queue depth depending on the scaling policy). Unhealthy instances get terminated and replaced. No state migrates, because there was never any state to migrate.

### Health check

Two independent health signals per instance:
- **Shallow** (ELB target-group level): `GET /health` on the playwright-service API returns 200 when the service is up. Fast, runs every few seconds.
- **Deep** (inside the playwright-service's `/health`): includes a probe that verifies the sidecar is reachable on its Docker-network address (`http://agent-mitmproxy:8000/health`). If the sidecar is dead or unreachable, the instance reports unhealthy and the ASG terminates it.

This couples the two containers' fates without needing docker-compose-level orchestration — the playwright-service is the liveness authority for the pair.

### Scaling triggers

The service is deterministic enough that simple policies work well:
- **CPU-based** (Chromium is CPU-heavy) — scale up when sustained CPU > 70%
- **Queue-depth-based** if the service grows a request queue — scale up when depth exceeds N
- **Request count** via CloudWatch — scale up when RPS exceeds instance capacity threshold

AWS Predictive Scaling adds a forecast-based floor for peak periods if usage patterns are predictable.

### Cold-start cost

A fresh EC2 instance takes roughly 60-90 seconds from ASG launch to serving-traffic:
- ~30s EC2 boot + cloud-init
- ~15s docker pull (if layer-cached in the AMI, 3-5s)
- ~10s Playwright + sidecar boot
- ~5s health check passing

Mitigations:
- **AMI-baked images** — build AMIs with both container images pre-pulled so `docker run` is near-instant.
- **Warm ASG floor** — `min_size` keeps some instances always running. Cost knob vs responsiveness knob.
- **Predictive scaling** for anticipated peaks.

---

## Packaging as a self-contained unit

The two-container design is deliberately portable. Three deployment modes all use the same artefacts:

### Local development

```
docker compose up
```

`docker-compose.yml` brings up both containers on a local Docker network. Env vars come from `.env`. API exposed on `localhost:<port>`. Identical behaviour to EC2 except the ports bind to `127.0.0.1` rather than the instance's private IP.

### EC2 (production)

The AMI baked from this unit has both Docker images pre-pulled and starts them via `docker compose` or `systemd` units invoked from cloud-init UserData. Env vars are injected via the ASG's launch template UserData script. Instance boots, compose comes up, NLB target group adds it.

### AMI on AWS Marketplace

Same AMI as the production deployment. Packaged for Marketplace subscribers with:
- Metered billing on hourly/per-instance/per-million-requests (pick one)
- Default env var config that makes it work out of the box (no upstream, audit log on, default API key that the subscriber MUST change on first boot)
- Launch-page documentation explaining the env var contract
- Upgrade path: new AMI versions replace old ones via Marketplace subscription rotation

The open-source core is the codebase. The Marketplace offering is the packaged, supported AMI. These are not mutually exclusive — they're the same artefact with different distribution channels.

---

## Security surface

### Authentication

| Surface | Mechanism |
|---|---|
| API caller → playwright-service API | `X-API-Key` header, value from `FAST_API__AUTH__API_KEY__VALUE` |
| playwright-service → sidecar (browser proxy on :8080) | **Network isolation** — private Docker network only, no HTTP auth. `:8080` has no host port mapping. |
| External → sidecar admin API (`:8000`) | `X-API-Key` (shared-secret convention across services) |
| Sidecar → upstream proxy (optional) | `Proxy-Authorization: Basic <u:p>` preemptive (in upstream-forward mode) |
| External → sidecar UI (`:8081`) | NOT exposed. Internal only, reverse-proxied via `:8000/ui` behind API key |

**Why no HTTP auth on browser → sidecar:** Phase 1.11 proved that Playwright cannot reliably pass proxy credentials to its browsers against authenticated proxies — that's the bug the sidecar exists to work around. Re-introducing proxy auth on the browser-side of the sidecar would reintroduce the failure mode. Since the sidecar is only reachable over a private Docker network inside a single EC2 instance (never exposed on the host or to the outside), network isolation is the correct security boundary.

### TLS interception

The sidecar terminates TLS, which means it sees plaintext HTTP bodies. This is the point — it enables introspection and policy — but it carries non-trivial security responsibility:

- **CA cert is sensitive.** Anyone with the sidecar's CA can sign certs for any domain and get MITM status in systems that trust the CA. `/ca/mitmproxy-ca.pem` (via `/ca/*`) must be API-key-gated. It already is in the current implementation.
- **Audit log contains URLs.** The `Audit_Log` addon writes `host + path` to stdout. If the paths contain sensitive data (query string tokens, session IDs), the log is sensitive. Log-line handling should match the sensitivity class of the audit data.
- **Don't expose proxy port externally.** `:8080` must only be reachable inside the Docker network. The EC2 security group should not allow `:8080` ingress from outside the instance.

### Secret distribution

The env var contract keeps secrets out of images:
- `PROXY_AUTH_PASS`, `UPSTREAM_PASS`, `API_KEY_VALUE` are injected via launch-template UserData (ASG) or Marketplace subscriber config.
- No secret is ever baked into the Docker image.
- The admin `/config/interceptor` endpoint accepts Python code uploads at runtime — this is a powerful foot-gun; the endpoint is API-key-gated and the code runs inside the sidecar container (not the host).

---

## What this architecture does *not* cover

Honest scope boundaries:

### 🟡 Lambda / serverless (explicitly out of scope)

The sidecar architecture does not apply to Lambda deployments. The pattern assumes a persistent second process alongside Playwright, and Lambda's execution model (single-container-per-invocation, Firecracker resource constraints, cold-start cost amortised per invocation) makes that awkward.

**What Lambda deployments look like (unchanged by this document):**

| Feature | EC2 (this doc) | Lambda |
|---|---|---|
| Browser traffic path | Always via sidecar | Direct to internet |
| Audit logging | JSON-line pipeline via sidecar stdout | CloudWatch Logs (existing) |
| Correlation IDs | Stamped by sidecar | None via this mechanism |
| CA distribution | Sidecar `/ca/*` | N/A (no TLS interception) |
| Runtime addon updates | Sidecar `/config/interceptor` | N/A |
| No-auth upstream proxy | Works (via sidecar) | Works (Playwright native `proxy={'server'}`) |
| **Authenticated upstream proxy** | **Works (via sidecar)** | **Does not work — same bug documented in `02__origin-story.md`** |
| Packaging | Two-container AMI | Existing Lambda container image |

**Recommended Lambda deployment:** Playwright goes direct to the internet. No sidecar. No authenticated upstream. Existing CloudWatch-based observability.

If a future use case needs authenticated-proxy browsing in Lambda, one option is an **external** sidecar — the Playwright Lambda points its proxy config at an EC2-hosted sidecar reachable over the VPC. That preserves the sidecar benefits without trying to run mitmproxy inside the Lambda runtime itself. Not a priority for now; see `03__roadmap.md`.

### Per-request upstream selection

Current design: upstream is configured per-container at boot. If you need multiple upstreams served by one container, see `03__roadmap.md` — the Phase 1.12b investigation explored this and found a viable-with-caveats approach.

### Non-HTTP traffic

The sidecar intercepts HTTP and HTTPS. Browser traffic that uses other protocols (WebTransport, QUIC, raw TCP) is not covered. Chromium does try to upgrade connections, but if a site forces WebSocket-over-QUIC or similar, that flow bypasses inspection. Deal with it if/when it matters.

### DDoS / heavy-load protection

The sidecar is a single process inside one container. Under sustained heavy load (thousands of concurrent browser connections), the sidecar itself becomes the bottleneck for that instance. Horizontal scaling handles this at the ASG level — more instances = more sidecars — but there's no in-instance sharding.

---

## Why this framing

Three gains over the narrower "sidecar fixes proxy auth" framing:

1. **Unified story.** One architectural concept (every EC2 instance is a paired browser+gateway unit) subsumes proxy-auth, observability, policy control, and certificate distribution. Easier to reason about, easier to explain, easier to extend.
2. **Productisable.** The two-container unit is a product. AMI. Marketplace. Sellable. The narrower framing was a bug fix.
3. **Honest about Lambda.** Documenting "Lambda does direct-to-internet, EC2 does gatewayed" is clearer than pretending one pattern fits both. The Lambda path is still supported, just with narrower guarantees.

---

## References

- `02__origin-story.md` — the proxy-auth bug and investigation that produced this architecture
- `03__roadmap.md` — what's shipped, what's next, open questions
- `../debug-session/phase-1_11__upstream-mode/` — empirical validation of the upstream-forward pattern
- `../debug-session/phase-1_12c__upstream-header-verification/` — proof that browsers traverse the full chain end-to-end
- `agent_mitmproxy/` in the repo (v0.1.32) — the actual sidecar implementation
