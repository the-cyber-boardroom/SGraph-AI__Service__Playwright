---
title: SG/Edge — solution overview
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
related:
  - sg-edge__02-edge-fleet.md
  - sg-edge__03-targets.md
  - sg-edge__04-commercial-angles.md
  - sg-edge__05-mvp-test-and-acceptance.md
prior:
  - v0_27_45__strategy-brief__sg-compute-as-serverless-environment.md
---

# What this is

The cert-strategy brief landed on a deeper problem: the per-vault TLS provisioning model is a holdover from when each vault was an island. As `sg-compute` becomes a serverless environment hosting many ephemeral workloads, we need a single edge layer that terminates TLS centrally, routes by slug, and scales independently of any one vault. This document sketches that edge — `SG/Edge` — sibling to SG/Vault, SG/Send, SG/API and SG/Tools.

# The shape, at a glance

```
                            +-------------------------+
                            |       The Browser       |
                            |  alice.cv.sgraph.ai     |
                            +-------------------------+
                                       |
                                       | HTTPS (TLS to *.cv.sgraph.ai
                                       |        wildcard ACM cert)
                                       v
                            +-------------------------+
                            |       CloudFront        |
                            |  + viewer-request fn    |   <-- TLS terminates here
                            |  + origin group         |       key never leaves AWS
                            +-------------------------+
                                       |
                          primary      |       secondary
                  (proxies up)         |       (cold-cold fallback)
                                       v
                +----------------------+-------------------+
                |                                          |
                v                                          v
       +----------------+    provisions           +----------------+
       |  SG/Edge fleet | <-----------------------|   Edge Waker   |
       |  N x EC2 +     |                         |  (Lambda Fn    |
       |  OpenResty     |                         |   URL)         |
       +----------------+                         +----------------+
              |                                           |
              | slug -> backend                           | also invokes
              | via DNS lookup                            | Vault Waker
              |                                           | (in parallel)
              v                                           v
       +----------------+                         +----------------+
       |  vault target  |  <----------------------|   Vault Waker  |
       |  EC2 or        |       provisions        |  (existing,    |
       |  Fargate task  |                         |   sg va / vp)  |
       +----------------+                         +----------------+
```

Four layers, two wakers. Browser sees only the CloudFront edge. Vault targets are the same EC2 / Fargate compute that exists today. The two new pieces are the SG/Edge proxy fleet (scale-to-zero) and the Edge Waker (cold-cold bootstrap).

# How traffic reaches SG/Edge — the wildcard

A single wildcard alias at the zone — `*.cv.sgraph.ai → CloudFront` — is set once at edge setup and never written per-slug. The browser resolves any subdomain (provisioned or not, real or typed-by-mistake) to CloudFront. CloudFront terminates TLS with the wildcard ACM cert and forwards to the proxy fleet.

This has two consequences worth being explicit about:

1. **No per-slug DNS write is needed for traffic to reach the proxy.** Whatever a user types under the parent domain, OpenResty receives it. Routing decisions (does this slug exist? is the backend up?) happen *inside* the proxy based on additional DNS records, not from whether the request arrives.

2. **The proxy is responsible for handling unrecognised slugs.** `random123.cv.sgraph.ai` will reach OpenResty exactly as `alice.cv.sgraph.ai` does. The proxy serves a "slug not recognised" page in that case (see Phase 2 flow below).

This shape is especially well-suited to the agentic-workload future where slug count and churn rates would make per-slug DNS A-record writes operationally painful. The architecture handles thousands of short-lived slugs without DNS-zone churn.

# The two DNS records per slug

Each provisioned slug has two records, with distinct purposes and lifecycles:

```
+------------------------------------------------------------------------+
|  Record                          |  Owned by    |  Lifetime           |
+------------------------------------------------------------------------+
|  alice.cv.sgraph.ai          A   |  Vault Waker |  Slug ownership     |
|    -> CloudFront                 |  (control)   |  (long-lived)       |
|                                                                        |
|  _sg.alice.cv.sgraph.ai      TXT |  Vault Waker |  Backend runtime    |
|    "v=1;ip=10.0.1.5;port=8080;   |  (data)      |  (ephemeral)        |
|     type=ec2;launched=..."       |              |                     |
+------------------------------------------------------------------------+
```

The **A record** is the "this slug is registered to a customer" signal. Written when a slug is allocated; removed when a slug is offboarded. It is *not* required for traffic to arrive at SG/Edge (the wildcard handles that), but it is the proxy's source of truth for "is this a known slug?". Without an A record the proxy returns "slug not recognised."

The **TXT record** at `_sg.<slug>.<parent>` carries the runtime routing data. Written when a vault target starts (with its current IP and port); updated when the target's IP changes (e.g. EC2 stop/start); removed when the target terminates. The TXT record being absent means "this slug is registered but has no active backend right now" — the proxy triggers the Vault Waker and serves a loading page.

The four scenarios where A exists but TXT doesn't:

1. New slug just registered, no vault has been provisioned yet
2. Slug exists but has never been opened by anyone
3. Vault's EC2/Fargate instance has terminated
4. Vault Reaper detected a stale TXT (instance gone, TXT not cleaned up) and removed it

All four are observably identical from the proxy's perspective: same signal, same handling — trigger the Vault Waker, serve a loading page. The waker is the layer with the operational intelligence to figure out *which kind* of wake is needed.

# State model

There is no DynamoDB. There is no S3 lock. State lives in DNS records and (transiently) in the OpenResty `shared_dict` cache.

```
+---------------------------------------------------------------+
|                    Where state lives                          |
+---------------------------------------------------------------+
|                                                               |
|  Per-parent wildcard alias (one-time setup):                  |
|     *.cv.sgraph.ai            A     -> CloudFront             |
|                                                               |
|  Per-slug, registered status:                                 |
|     alice.cv.sgraph.ai        A     -> CloudFront             |
|       (value is the same as the wildcard - what matters       |
|        is that the record exists explicitly)                  |
|                                                               |
|  Per-slug, runtime backend:                                   |
|     _sg.alice.cv.sgraph.ai    TXT   -> "v=1;ip=10.0.1.5;..."  |
|                                                               |
|  Per-proxy, fleet membership:                                 |
|     proxies.cv.sgraph.ai      A     -> 1.2.3.4                |
|     proxies.cv.sgraph.ai      A     -> 1.2.3.5                |
|     (multiple A records, written by Edge Waker on boot)       |
|                                                               |
|  Per-parent, Edge Waker counter (zero_streak for teardown):   |
|     _state.cv.sgraph.ai       TXT   -> "zero_streak=2;..."    |
|                                                               |
|  Transient (in-process):                                      |
|     OpenResty shared_dict cache (A / TXT / health / slug_seen)|
+---------------------------------------------------------------+
```

The architectural payoff of DNS-as-registry:

- **Single source of truth.** DNS is the registry. No drift between "the system says it exists" and "DNS resolves to nothing." The proxy reads DNS directly.
- **Portable.** Every cloud has DNS. Moving the whole thing to Hetzner + Cloudflare DNS is configuration, not rewrite.
- **No coordination service.** No DynamoDB, no S3 lock, no SSM Parameter Store. Every piece of Edge Waker state lives in DNS records; every proxy↔waker handshake is direct HTTP. The Edge Waker is idempotent and convergent — see below.

# No coordination service — why

An earlier sketch of this architecture used an S3 conditional-write lock to prevent two Edge Waker invocations from both booting the proxy fleet simultaneously during a cold-cold event. On reflection, the lock is solving a problem that doesn't exist at the traffic shapes scale-to-zero is *for*.

The traffic profile that triggers cold-cold is, by definition, low: the fleet was at zero because traffic was idle. The first user kicks off provisioning; a handful of concurrent users in the same 20-30s boot window might also trigger the Edge Waker. If two Edge Wakers both call `RunInstances`, the worst outcome is one extra `t4g.small` for a few minutes before idle teardown catches it. That's not damage — it's a rounding error, and the architecture's production-recommended state is N>=2 anyway.

At the traffic shapes where coordination *would* matter (genuinely thousands of concurrent users arriving in a true cold-cold window), you've already opted into always-on proxies, which sidesteps the coordination problem from the other direction: proxies don't keep cold-starting if they never cold-start at all.

This is the architectural elegance worth naming: most "scale to zero" stories have a coordination problem buried somewhere that breaks at higher scale, forcing a rewrite when the customer succeeds. Here the inverse is true. The coordination problem only *could* exist at higher scale, but by that point you've already opted into always-on infrastructure where the problem is moot. The architecture is correct at both ends of the traffic spectrum with a graceful interpolation between them.

Reconciliation, not locking, is the model. The Edge Waker periodically reads DNS (count of healthy `proxies.<parent>` A records) and reconciles toward the target count. If two invocations both decide to add a proxy, one extra proxy boots. Idle teardown catches the surplus within minutes. Idempotent operations everywhere — `route53:ChangeResourceRecordSets` with `UPSERT`, `TerminateInstances` on the same ID twice — make this safe.

# The two wakers

The single most important architectural decision here is keeping the wakers separate. They share `sg-compute` primitives for launching EC2 / Fargate, but their responsibilities, lifecycles, and IAM scopes are different.

```
+-----------------------------------------+    +-----------------------------------------+
|              Vault Waker                |    |              Edge Waker                 |
|         (existing, sg va / vp)          |    |               (new)                     |
+-----------------------------------------+    +-----------------------------------------+
| TRIGGER:                                |    | TRIGGER:                                |
|   user-facing CLI / API call            |    |   CloudFront origin-group failover      |
|   "create / wake a vault"               |    |   (i.e. proxy fleet is down/cold)       |
|                                         |    |                                         |
| FREQUENCY:                              |    | FREQUENCY:                              |
|   100s-1000s/day, one per user vault    |    |   10-50/day with aggressive teardown;   |
|                                         |    |   no upper limit, no per-cycle cost     |
|                                         |    |                                         |
| OUTPUTS:                                |    | OUTPUTS:                                |
|   - EC2 / Fargate vault backend         |    |   - EC2 OpenResty proxy instances       |
|   - per-slug TXT record (runtime)       |    |   - proxies.<parent> A records          |
|   - per-slug A record (registration,    |    |                                         |
|     only on first allocation)           |    |                                         |
|                                         |    |                                         |
| IAM SCOPE:                              |    | IAM SCOPE:                              |
|   - ec2:RunInstances (vault profile)    |    |   - ec2:RunInstances (edge profile)     |
|   - ecs:RunTask (vault task-def)        |    |   - route53:Change (proxies.* only)     |
|   - route53:Change (slug zones)         |    |                                         |
|                                         |    |                                         |
| HOLDS UX FOR:                           |    | HOLDS UX FOR:                           |
|   ~30s-2min (compute boot)              |    |   ~30-90s (proxy boot) ON FIRST USER    |
|                                         |    |   ONLY; everyone after hits warm fleet  |
+-----------------------------------------+    +-----------------------------------------+
```

The frequency numbers matter: the Edge Waker is *cycle-tolerant*. There's no architectural cost to invoking it 10-50 times per day (or more) with aggressive teardown. A given parent domain can hibernate overnight, wake on first request, scale up during the day, scale down in the evening, and tear down at night, all without any per-cycle penalty. This is what enables the scale-to-zero economics in `sg-edge__04-commercial-angles.md`.

# Warm path — the common case

```
User                CloudFront         OpenResty proxy       Vault target
 |                        |                    |                    |
 |--alice.cv.sgraph.ai--->|                    |                    |
 |    (HTTPS, TLS         |                    |                    |
 |     terminates at CF)  |                    |                    |
 |                        |                    |                    |
 |                        |--HTTP (plain)----->|                    |
 |                        |   Host preserved   |                    |
 |                        |   X-SG-Slug=alice  |                    |
 |                        |                    |                    |
 |                        |                    | shared_dict cache  |
 |                        |                    | (A + TXT + health) |
 |                        |                    |                    |
 |                        |                    |--HTTP (plain)----->|
 |                        |                    |   :8080            |
 |                        |                    |                    |
 |                        |                    |<--response---------|
 |                        |<-------------------|                    |
 |<-----------------------|                    |                    |
```

Plain HTTP everywhere inside AWS — CloudFront-to-proxy and proxy-to-target both. The wildcard ACM cert lives in CloudFront's managed TLS terminator and never leaves it. No certificate management on the proxy or the target.

Why this is safe to claim:

1. **Payloads are already encrypted.** SG/Vault and SG/Send encrypt all file content client-side in the browser before any HTTP request leaves. CF and OpenResty see ciphertext — the TLS termination at CF doesn't change what anyone in the path can read, because they already can't read the meaningful content.
2. **Traffic inside AWS is on AWS's private network.** CF->proxy and proxy->target are in-region, AWS-managed connectivity. The threat model that requires defense-in-depth here is "AWS itself is hostile or compromised", which is well outside our model — if that's true, we have far bigger problems than plaintext on internal hops.
3. **Centralised TLS termination is the standard pattern.** Cloudflare, Fastly, every major CDN. The trust boundary is well-established.

The combined story: TLS terminates at the edge for ops/observability gain (centralised logging, one place to manage cert renewals), while the actual payload is encrypted anyway, while client-identifying metadata (IPs in particular) is dropped from logs at source, matching the practice already in production at `*.aws.sg-labs.app`. Zero-knowledge holds end-to-end.

# Cold-cold path — first user after fleet teardown

When the proxy fleet is at zero (no traffic for a sustained period, fleet torn down by Edge Waker), the first user arrives via CloudFront's origin-group failover to the Edge Waker Function URL. The waker bootstraps the fleet *and* (in parallel) the requested vault target.

```
User           CloudFront      Edge Waker             EC2 API     Route 53
 |                  |               |                    |           |
 |---req----------->|               |                    |           |
 |                  |--try primary->X (no IPs)           |           |
 |                  |  (~1s conn timeout)                |           |
 |                  |                                    |           |
 |                  |---failover to secondary----------->|           |
 |                  |                  |                 |           |
 |                  |                  |--- TRACK A: proxy fleet --->|
 |                  |                  |    RunInstances             |
 |                  |                  |                              |
 |                  |                  |--- TRACK B: vault target -->|
 |                  |                  |    RunInstances/RunTask     |
 |                  |                  |    (parallel, not sequential)
 |                  |                  |                              |
 |<--loading page---|<-----------------|                              |
 |                  |                                                 |
 |   (client polls /edge-status; both tracks proceed in parallel)    |
 |                  |                                                 |
 |       ...max(track A, track B) ~30-90s, dominated by EC2 boot...  |
 |                  |                                                 |
 |                  |                  |<-- proxy ready              |
 |                  |                  |--add proxies.<parent> A---->|
 |                  |                  |                              |
 |                  |                  |<-- target ready              |
 |                  |                  |--write _sg.<slug> TXT------>|
 |                  |                                                 |
 |  ...CF DNS-cache refresh at POP (~10-30s)...                       |
 |                  |                                                 |
 |<------ (client reload -> warm path) ----------------->|           |
```

The parallel-boot optimization halves the worst-case cold-cold time. Track A (proxy fleet) and track B (vault target) are independent — neither needs the other to be ready before starting. The user pays one boot time, not two.

Total cold-cold time: ~30-90s typical (dominated by `max(proxy boot, target boot)`), ~120s worst case. Subsequent users hit the warm path with ~50ms in-region overhead.

# Why this works at small AND large scale

The same codebase serves both modes — scale-to-zero and always-on are runtime states, not architectural variants. As traffic grows, the fleet stays warm; as traffic dies, it tears down. The Edge Waker's idle-teardown threshold is the only knob:

```
+--------------------------------------------------------------------+
|  Traffic shape       |  System mode      |  Customer experience    |
+--------------------------------------------------------------------+
|  No traffic for days |  Hibernation:     |  $0/mo per parent       |
|  (idle customer)     |  no proxies,      |  fleet (Route 53 zone   |
|                      |  no targets       |  is the only fixed cost)|
|                      |                                              |
|  Bursty: hours-on,   |  Cycles:          |  First user pays cold-  |
|  hours-off           |  edge waker fires |  cold (~60s); rest pay  |
|  (dev environment,   |  10-50/day        |  warm path. Cost tracks |
|   office-hours app)  |                   |  usage.                 |
|                      |                                              |
|  Steady moderate     |  Warm fleet,      |  All requests warm path |
|  traffic             |  proxy fleet      |  (~50ms in-region).     |
|                      |  stays N>=1       |                         |
|                      |                                              |
|  High steady traffic |  Always-on,       |  Same warm path, larger |
|                      |  N=many           |  proxy fleet            |
+--------------------------------------------------------------------+
```

No architectural transitions, no migrations, no different deployment patterns — just the same system in different runtime states, controlled by the idle-teardown threshold. A customer can evolve through these modes during the course of a single day if their usage pattern justifies it.

# What's AWS-specific vs portable

| Component | AWS choice | Portable replacement |
|---|---|---|
| CDN / TLS terminator | CloudFront + ACM | Cloudflare, Fastly, Bunny + their managed certs (or LE wildcard via DNS-01) |
| DNS | Route 53 | Cloudflare DNS, NS1, any |
| Edge fleet compute | EC2 | Any VM provider; OpenResty config unchanged |
| Target compute | EC2 / Fargate | Any VM / container service |
| Wakers | Lambda Function URLs | Any FaaS, or a small Go service |

There is no longer any AWS-specific coordination service in the design (the S3 lock is gone). The Vault Waker is the most cloud-coupled component because it calls `RunInstances` / `RunTask` APIs, but every cloud has equivalents. Everything else is commodity.

For completeness — the CF + Lambda dependency at the top of the stack can also be removed in a future evolution by replacing CloudFront with always-on OpenResty proxies that hold the wildcard cert and do the cold-cold bootstrap themselves. Not needed now, but a known evolution path if AWS-specific risks become unacceptable for a customer segment.

# Centralised logging — the security framing

The architecture has a property worth naming explicitly because security-sensitive customers will ask: TLS terminates at CloudFront, which sounds like it weakens the zero-knowledge story, but doesn't.

Three layers of defense:

1. **Encrypted payloads.** SG/Vault and SG/Send encrypt all file content client-side in the browser before any HTTP request leaves. CF and OpenResty see ciphertext bodies. Centralised TLS termination doesn't change what CF can read; the answer is still "nothing meaningful."

2. **Metadata stripping in logs.** Client-identifying data (IP addresses in particular) is dropped from logs before persistence, matching the practice already in production at `*.aws.sg-labs.app`. In the MVP this happens in the proxy's nginx access log config (omit `$remote_addr` from the log_format directive); in production it can be tightened further by a log-shipping pipeline.

3. **Wildcard key boundary.** The private key for the wildcard cert lives inside CloudFront's AWS-managed TLS terminator. It's never written to disk on any proxy, never exposed in any vault target, never accessible to any IAM role we own. No certificate exists on the proxy or the target — the simplification removes an entire class of key-management concern.

```
+-----------------------------------------------------------------+
|              What each layer can see                            |
+-----------------------------------------------------------------+
|  Layer            |  What's visible                            |
+-----------------------------------------------------------------+
|  CloudFront       |  URL path, response codes, byte counts.    |
|                   |  Client IP (then stripped from logs).      |
|                   |  Cannot decrypt vault payloads —           |
|                   |  they were already ciphertext.             |
|                                                                 |
|  OpenResty proxy  |  Same as CF plus request timing per        |
|                   |  upstream. Client IP omitted from logs.    |
|                                                                 |
|  Vault target     |  Plain HTTP request bodies — but these     |
|                   |  are already ciphertext produced by        |
|                   |  browser-side AES-GCM.                     |
+-----------------------------------------------------------------+
```

# MVP phasing

The order is determined by *where the unknowns live*. The Vault Waker pattern is already proven in production (`*.aws.sg-labs.app` uses DNS-driven backend lookup at scale). The OpenResty hot path is mechanically straightforward. The genuinely unproven piece is the **Edge Waker + cold-cold bootstrap dance** — CF origin-group failover under real load, EC2 boot variance, DNS-propagation behavior at CF POPs when proxy IPs change, idle-teardown stability. That's where the curve balls live. Build that first, in isolation.

**Phase 1 — prove the edge tier in isolation.** The target is *not* a vault. It's a static site served directly by OpenResty itself — a small HTML page that responds with the proxy's instance ID, current timestamp, and diagnostic headers. The slug routing is short-circuited: any host arriving at the proxy is served the static page locally. This lets us hammer the edge tier without a target backend in the loop at all.

In scope for Phase 1:

- One CloudFront distribution with wildcard ACM cert
- CloudFront Function (Host preservation, slug extraction)
- CF origin group: primary = `proxies.<parent>`, secondary = Edge Waker Function URL
- Edge Waker Lambda — full implementation: EC2 RunInstances, Route 53 A-record writes for `proxies.<parent>`, scale-up, idle teardown
- OpenResty serving a static diagnostic site directly (no upstream proxying)
- **No sidecars.** No Vector, no CloudWatch agent, no Edge Heartbeat. Logging via plain stdout / nginx default access log. Observability comes later — Phase 1's job is to prove the mechanics, not to be production-ready.
- **No cert on proxy.** Plain HTTP CF->proxy. The configuration is just `listen 80;` in nginx.
- Test rig (`sg edge_bench`) covering all primitive scenarios (see `sg-edge__05-mvp-test-and-acceptance.md`)

**Phase 1 also runs fully offline / locally.** Every component in scope above has a local equivalent already proven in the repo: OpenResty runs in Docker, the Edge Waker is just a FastAPI service (the same pattern we use for our other Lambda Function URLs in dev), vault targets already run locally, and CloudFront's behavior (TLS termination + origin failover) can be simulated with a thin local nginx in front of the proxy. DNS-as-registry becomes a local resolver (CoreDNS in a container, or even `/etc/hosts` plus a small file-backed mock for the TXT records). A complete local Phase 1 environment can be brought up with `docker compose` and exercised by the same `sg edge_bench` CLI — local scenarios run in seconds rather than minutes, AWS API quirks are absent, and the AWS-only scenarios (CF DNS-cache refresh, Route 53 propagation, real EC2 boot variance) are the ones that still need a real bench environment. This is the right development loop: 90% of correctness work happens locally, the bench env catches AWS-specific behavior.

**Phase 2 — wire in Vault Waker integration.** Once Phase 1 has validated the edge tier mechanics, swap the static-site short-circuit for the real routing.

Phase 2 scope is deliberately tight:

- Vault Waker extended to write A record on slug registration (one-time per slug) and TXT record on each vault provision
- Vault Waker extended to remove TXT on termination, remove A on slug offboarding
- OpenResty Lua hot path (the flow below)
- "Slug not recognised" page (text-only HTML, no information leak between scenarios)
- Loading page for cold-vault wake (HTML + JS poll, served locally from OpenResty)
- Waker invocation via `ngx.timer.at` for async fire-and-forget
- Basic rate limiting on the "slug not recognised" path to prevent enumeration / DoS

**The Phase 2 Lua hot path** (~60-80 lines total):

```
1. Parse slug from Host header
2. Look up A record for <slug>.<parent> (cached, see TTL table below)
   - NXDOMAIN -> "slug not recognised" page; rate-limited
   - Found    -> continue
3. Look up TXT record for _sg.<slug>.<parent> (cached, see TTL table below)
   - NXDOMAIN -> trigger Vault Waker (async); serve loading page
   - Found    -> parse v=1;ip=...;port=...
4. Check shared_dict health cache for this slug
   - Healthy (fresh)   -> proxy_pass to ip:port (no probe)
   - Unhealthy (fresh) -> trigger Vault Waker (async); serve loading page
   - Unknown           -> proxy_pass optimistically
5. On proxy result:
   - Success -> mark slug healthy in cache
   - Failure -> mark slug unhealthy, fall through to waker path on next request
```

Cache TTLs need different settings for A vs TXT because their lifecycles are different:

```
+--------------------------------------------------------------------+
|  Cache type          |  TTL    |  Reasoning                        |
+--------------------------------------------------------------------+
|  A NXDOMAIN          |  60s    |  Unknown slugs don't materialize  |
|                      |         |  spontaneously; long cache OK     |
|  A found             |  300s   |  Slug registration is stable      |
|  TXT NXDOMAIN        |  5s     |  Waker might be writing it RIGHT  |
|                      |         |  NOW; need to discover quickly    |
|  TXT found           |  30s    |  Backend IP/port is stable while  |
|                      |         |  the vault is running             |
|  health (per slug)   |  10s    |  Backend liveness is volatile     |
+--------------------------------------------------------------------+
```

The asymmetric TXT cache TTL (long for found, short for NXDOMAIN) is the subtle bit. If we negative-cache "TXT missing" too aggressively, a user who triggers the waker has to wait for the negative cache to expire before the proxy notices the freshly-written TXT — adding 30-60s of avoidable delay to cold vault start.

Explicitly out of scope for Phase 2:
- Sidecars (Vector, CloudWatch agent) — deferred to Phase 3
- HTTPS between proxy and target — plain HTTP is fine
- Migrating existing vaults off `letsencrypt-hostname` — old vaults drain naturally; new ones use SG/Edge from day one
- WebSocket support (vault doesn't use WS today; add when needed)
- Agentic operating mode (see below)

**Phase 3 — production hardening.** Multi-AZ, multi-region, scaling tuning, the sidecar suite for observability, scaling thresholds based on real traffic patterns.

# Future operating modes — agentic workloads

The current design assumes one customer / one slug / one vault — the human-customer case where the A record acts as a registration receipt. For agentic workloads where slugs are themselves ephemeral (lifetime measured in seconds or minutes), per-slug A records become churn (thousands written/removed per day per customer).

Two future operating modes to support this, in addition to the human-customer mode above:

1. **A-less mode:** skip A records entirely for agentic edges. The proxy treats "TXT exists" as authoritative for "this slug routes somewhere"; ownership / authorization is enforced earlier (when slugs are allocated to an account) rather than via DNS existence.

2. **Pooled-A mode:** one long-lived A record per agent pool (e.g. `agent-pool-123.cv.sgraph.ai`), with the TXT extra fields routing to per-agent containers (path-based or via a small registry the proxy reads). One A record covers many ephemeral agents.

These are Phase 3+ concerns. They share the same edge code with a configuration switch on a per-parent-domain basis. Not built for MVP but worth knowing the architecture handles them without rework.

# Decisions (formerly open questions)

1. **Loading page UX when TXT was just written.** Not a concern — the loading page polling is driven by the Edge Waker's UX, which controls the reload moment based on TXT availability. The user never needs to hit refresh manually, so the brief window where the proxy's negative cache is stale doesn't surface to the user. The polling client waits until status flips to ready, then triggers the reload itself.
2. **Where does the CloudFront Function live in code?** New module `sg_compute_specs/sg_edge/cloudfront_function/` — same repo as the rest of SG/Edge. The module path uses `sg_edge` (matching the SG/Edge product name and sibling pattern with `vault_app`, `vault_publish` etc.), not `edge`.
3. **Scale-up trigger for proxy fleet.** Deferred. MVP starts with a predefined number of proxy instances (configurable but static). Auto-scale logic needs real load-test data to choose the right metric (active vault count vs RPS vs CPU); we'll add it in Phase 3 once we have measurements from the bench environment.
4. **"Slug not recognised" page content.** Simple 404 message for MVP — brandable later. No sign-up CTA, no integration with wider SG/Compute pages. Just a plain HTML page that says the slug isn't registered.
