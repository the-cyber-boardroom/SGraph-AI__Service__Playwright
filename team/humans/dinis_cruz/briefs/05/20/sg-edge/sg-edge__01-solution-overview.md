---
title: SG/Edge — solution overview
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
related:
  - sg-edge__02-edge-fleet.md
  - sg-edge__03-targets.md
prior:
  - v0_27_45__strategy-brief__sg-compute-as-serverless-environment.md
---

# What this is

The cert-strategy brief landed on a deeper problem: the per-vault TLS provisioning model is a holdover from when each vault was an island. As `sg-compute` becomes a serverless environment hosting many ephemeral workloads, we need a single edge layer that terminates TLS centrally, routes by slug, and scales independently of any one vault. This document sketches that edge — `SG/Edge` — and how it fits with the existing vault provisioning.

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
       +----------------+                         +----------------+
       |  SG/Edge fleet |                         |   Edge Waker   |
       |  N x EC2 +     |                         |  (Lambda Fn    |
       |  OpenResty     |                         |   URL)         |
       |  + sidecars    |                         +----------------+
       +----------------+                                 |
              |                                           | provisions
              | slug -> backend                           v
              | via DNS TXT lookup                  (SG/Edge fleet)
              v
       +----------------+
       |  vault target  |
       |  EC2 or        |
       |  Fargate task  |
       +----------------+
              ^
              | provisioned by
              |
       +----------------+
       |   Vault Waker  |
       |  (existing,    |
       |   sg va / vp)  |
       +----------------+
```

Four layers, two wakers. The browser sees only the CloudFront edge. The vault targets are the same EC2 / Fargate compute that exists today. The two new pieces are the proxy fleet (always-on at small scale, autoscaled by the Edge Waker) and the Edge Waker itself (cold-cold bootstrap).

# The four layers

| Layer | What it does | Lifecycle | Always-on? |
|---|---|---|---|
| **CloudFront** | TLS termination with wildcard ACM cert, viewer-request Function for Host preservation and slug extraction, origin-group failover to Edge Waker | Permanent | Yes (~$0/mo at zero traffic) |
| **SG/Edge fleet** | OpenResty proxies doing slug-to-backend routing via DNS lookups | Created by Edge Waker, torn down when no vaults active for N minutes | No — true scale-to-zero |
| **Vault targets** | The existing EC2 / Fargate vault backends. Plain HTTP on `:8080`, never speaks TLS | Per-user, per-vault, ephemeral | No |
| **Wakers** | Edge Waker (new) + Vault Waker (existing, `sg va` / `sg vp`) | Lambda, fires only when triggered | Yes (~$0/mo at zero invocations) |

Storage state lives in DNS records and a single S3 lock object — no DynamoDB. This is deliberate (see "State model" below).

# The two wakers

The single most important architectural decision here is keeping the wakers separate. They share `sg-compute` primitives for launching EC2 / Fargate, but their responsibilities, lifecycles, and IAM scopes are completely different.

```
+-----------------------------------------+    +-----------------------------------------+
|              Vault Waker                |    |              Edge Waker                 |
|         (existing, sg va / vp)          |    |               (new)                     |
+-----------------------------------------+    +-----------------------------------------+
| TRIGGER:                                |    | TRIGGER:                                |
|   user-facing CLI / API call            |    |   CloudFront origin-group failover      |
|   "create a vault for me"               |    |   (i.e. proxy fleet is down/cold)       |
|                                         |    |                                         |
| FREQUENCY:                              |    | FREQUENCY:                              |
|   100s-1000s/day, one per user vault    |    |   10-50/day with aggressive teardown;   |
|                                         |    |   no upper limit, no per-cycle cost     |
|                                         |    |                                         |
| OUTPUTS:                                |    | OUTPUTS:                                |
|   - EC2 / Fargate vault backend         |    |   - EC2 OpenResty proxy instances       |
|   - per-slug Route 53 A + TXT records   |    |   - proxies.<parent> Route 53 A records |
|                                         |    |                                         |
| IAM SCOPE:                              |    | IAM SCOPE:                              |
|   - ec2:RunInstances (vault profile)    |    |   - ec2:RunInstances (edge profile)     |
|   - ecs:RunTask (vault task-def)        |    |   - route53:Change (proxies.* only)     |
|   - route53:Change (slug zones)         |    |   - s3:PutObject (lock bucket)          |
|                                         |    |                                         |
| HOLDS UX FOR:                           |    | HOLDS UX FOR:                           |
|   ~30s-2min (compute boot)              |    |   ~30-90s (proxy boot) ON FIRST USER    |
|                                         |    |   ONLY; everyone after hits warm fleet  |
+-----------------------------------------+    +-----------------------------------------+
```

# State model — DNS as the registry

There is no DynamoDB. State is stored in DNS records and (for one specific case) a single S3 object.

```
+---------------------------------------------------------------+
|                    Where state lives                          |
+---------------------------------------------------------------+
|                                                               |
|  Per-slug existence + routing:                                |
|     alice.cv.sgraph.ai      A     -> CloudFront (or proxy)    |
|     _sg.alice.cv.sgraph.ai  TXT   -> "v=1;ip=10.0.1.5;        |
|                                       port=8080;type=ec2;     |
|                                       launched=1747700000"    |
|                                                               |
|  Proxy fleet membership:                                      |
|     proxies.cv.sgraph.ai    A     -> 1.2.3.4                  |
|     proxies.cv.sgraph.ai    A     -> 1.2.3.5                  |
|     (multiple A records, written by Edge Waker on boot,       |
|      removed on terminate)                                    |
|                                                               |
|  Edge Waker boot-lock (the only non-DNS state):               |
|     s3://sg-edge-locks/cv.sgraph.ai/fleet-state.json          |
|     using S3 If-None-Match for conditional writes             |
|                                                               |
+---------------------------------------------------------------+
```

Why DNS-as-registry rather than DynamoDB:

- **Single source of truth.** DNS is needed for routing anyway. If the record exists, the slug exists. No drift between "the registry says it's alive" and "DNS resolves to nothing."
- **Free read scaling.** DNS resolvers cache aggressively; the proxy fleet's load on Route 53 is negligible.
- **Portability.** Every cloud has DNS. Moving the whole thing to Hetzner + Cloudflare DNS is a configuration change, not a rewrite.
- **Smaller IAM surface.** The proxy fleet doesn't need DynamoDB credentials.

The one thing DNS lacks is conditional writes, needed exactly once: ensuring two Edge Waker Lambdas don't both decide to boot the proxy fleet. S3 has `If-None-Match` conditional writes since 2024 — a single small bucket handles it.

# Warm path — the common case

```
User                CloudFront         OpenResty proxy       Vault target
 |                        |                    |                    |
 |--alice.cv.sgraph.ai--->|                    |                    |
 |    (HTTPS, TLS         |                    |                    |
 |     terminates at CF)  |                    |                    |
 |                        |                    |                    |
 |                        |--HTTPS (self-      |                    |
 |                        |  signed at proxy)->|                    |
 |                        |   Host preserved   |                    |
 |                        |   X-SG-Slug=alice  |                    |
 |                        |                    |                    |
 |                        |                    |--TXT lookup--      |
 |                        |                    |  shared_dict       |
 |                        |                    |  cache (30s TTL)   |
 |                        |                    |                    |
 |                        |                    |--HTTP------------->|
 |                        |                    |   :8080            |
 |                        |                    |                    |
 |                        |                    |<--response---------|
 |                        |<-------------------|                    |
 |<-----------------------|                    |                    |
```

Total overhead vs direct-to-vault: one in-region hop (~1-2ms) plus TXT lookup (cached: sub-ms; uncached: 1-5ms). Negligible at the response sizes vault handles.

# Cold-cold path — first user after fleet teardown

```
User           CloudFront      Edge Waker     S3 lock    Fleet     Route 53
 |                  |               |            |         |           |
 |--->req---------->|               |            |         |           |
 |                  |--try primary->X            |         |           |
 |                  |  (no DNS records or        |         |           |
 |                  |   conn refused, ~1s)       |         |           |
 |                  |                            |         |           |
 |                  |---failover to secondary--->|         |           |
 |                  |                  |         |         |           |
 |                  |                  |--PUT---->         |           |
 |                  |                  |  If-None-Match    |           |
 |                  |                  |<--201 (won lock)--|           |
 |                  |                  |                   |           |
 |                  |                  |--RunInstances----->          |
 |                  |                  |                   |           |
 |<--loading page---|<-----------------|                   |           |
 |                  |                                      |           |
 |  (client polls /edge-status/<id>, then reloads)         |           |
 |                  |                                      |           |
 |       ...30-90s: EC2 boots, OpenResty starts...                     |
 |                  |                  |                   |           |
 |                  |                  |<--health green----|           |
 |                  |                  |--add A record (proxies.*)---->|
 |                  |                  |--release lock---->|           |
 |                  |                                      |           |
 |<-------- (client reload -> warm path) ---------------->|           |
```

Total cold-cold time: ~30-90s for the fleet, dominated by EC2 boot. If the vault itself is also cold (slug doesn't exist yet), the Vault Waker adds another 30-90s after the fleet is up. Worst case ~3 minutes for the first user; everyone after pays the warm path.

# What this architecture unlocks

The mechanics above describe *how* it works. This section is about *why it matters* — the capabilities that fall out of an ephemeral, DNS-driven, scale-to-zero edge that aren't possible with the traditional CF + ALB + always-on EC2 pattern.

## Edges are cheap and you can have many

The unit cost of standing up a new edge (new parent domain, new isolation boundary) is roughly:

```
+-----------------------------------------------------------+
|  Cost of one empty edge (no traffic, no vaults):          |
|                                                           |
|    CloudFront distribution    $0.00                       |
|    Wildcard ACM cert           $0.00                       |
|    Route 53 zone              $0.50 / month               |
|    Edge Waker Lambda           $0.00 (idle)               |
|    Proxy fleet                 $0.00 (scaled to zero)     |
|    Vault targets               $0.00 (scaled to zero)     |
|                                                           |
|    Total fixed:                ~$0.50 / month             |
+-----------------------------------------------------------+
```

Compare to the traditional pattern: one ALB at ~$20/month, plus at least one always-on EC2 to make it useful, plus per-environment maintenance overhead. The empty-environment cost is two orders of magnitude lower with the edge architecture.

Practical consequence: spinning up a new isolation boundary (per-customer, per-environment, per-experiment) becomes cheap enough that you can do it generously rather than reluctantly.

## Vault targets are effectively unlimited

There is no DNS record *per target* in the bottleneck sense — there's a DNS record per *slug*, but the slug routing is just a TXT record that costs effectively nothing. And nothing in the architecture requires one target per slug:

- A single EC2 instance can host many container-based slugs, each on a different port. The TXT record holds `ip:port`, so 100 small workloads can share one beefy EC2.
- Fargate tasks remain one-per-slug if isolation requires it, but for lighter workloads the container-on-shared-EC2 path is open.
- Backend mix is heterogeneous by design: some slugs may be EC2, some Fargate, some shared-EC2 containers. The proxy doesn't care; it just reads the TXT and connects.

The DNS limits (10k records per zone default, raisable) and the EC2 instance limits (default 20, raisable to thousands) are both soft AWS quotas, not architectural ceilings. The architecture itself has no inherent ceiling.

## The agentic workload case is where this really pays off

The current model (one EC2 per vault) is the right shape when "vault" means a long-lived encrypted store for human data. It's overkill when "vault" means a sandbox where an agent runs for 60 seconds and terminates.

Agentic workloads want: spin up in seconds, full TLS isolation, real network boundaries, no shared filesystem, near-zero cost when idle, and hundreds running concurrently per customer. This architecture delivers exactly that with no rework — only the target shape changes (smaller compute, faster boot, possibly container-per-agent on shared EC2). The edge layer, the wakers, the DNS-as-registry — all unchanged.

When agentic usage takes off, the count of targets will explode by 1-2 orders of magnitude. The current cert-per-target model would die instantly at that volume; this architecture absorbs it without changes.

## Capability matrix — what the architecture enables

```
+----------------------------------+-----------------------------------+
|  Capability                      |  How this architecture delivers   |
+----------------------------------+-----------------------------------+
|  Cheap isolation per customer    |  ~$0.50/mo per empty edge,        |
|                                  |  add edges generously             |
|                                  |                                   |
|  Full integration test envs      |  Spin up entire stack from CF     |
|  (end-to-end, with TLS)          |  down on demand, tear down after  |
|                                  |  test run; no cost when idle      |
|                                  |                                   |
|  Many environments (dev/QA/      |  Each is one edge ($0.50/mo) +    |
|  staging/prod/agents/...)        |  whatever it actually runs        |
|                                  |                                   |
|  Customer cost scales with use   |  Idle customer = near-zero cost;  |
|  (not with existence)            |  active customer = real cost;     |
|                                  |  no flat infra tax                |
|                                  |                                   |
|  Office-hours-only workloads     |  Teardown during off-hours costs  |
|                                  |  literally nothing; wake-up on    |
|                                  |  first morning request            |
|                                  |                                   |
|  Many concurrent agents          |  Container-per-agent on shared    |
|                                  |  EC2; only DNS TXT per agent      |
|                                  |                                   |
|  DR / BCP if ALB outage          |  Edge path is already validated   |
|                                  |  as parallel option; switch CF    |
|                                  |  origin and route via OpenResty   |
+----------------------------------+-----------------------------------+
```

## Coexists with the traditional pattern — not a replacement

The traditional CF + ALB + always-on EC2 pattern still works and isn't removed. Customers and workloads with steady traffic or a preference for that shape continue to use it. The edge architecture is an additional mode, opt-in per workload:

```
+-------------------------------------------------------------+
|  Workload type            |  Recommended path               |
+-------------------------------------------------------------+
|  High steady traffic      |  Traditional CF + ALB + EC2     |
|  Always-on enterprise     |  Traditional CF + ALB + EC2     |
|                                                             |
|  Bursty / ephemeral       |  SG/Edge                        |
|  Agentic / sandboxed      |  SG/Edge                        |
|  Dev / QA / integration   |  SG/Edge                        |
|  Long tail of small custs |  SG/Edge                        |
|  Cost-sensitive trials    |  SG/Edge                        |
+-------------------------------------------------------------+
```

The two paths share the vault target codebase — only the routing layer differs. Maintenance burden of running both is low.

## What we're really doing — and why it's worth it

The honest framing: several of the constraints driving this work are not vault problems; they are AWS / vendor problems exposed by an ephemeral workload pattern:

- ALB cold-start variance (30s to 30 minutes) makes per-customer ALBs painful
- ALB per-listener rule limit (100 default, ~1000 max) caps the per-ALB customer count
- ACM certs can't be exported to non-AWS-managed terminators
- LE rate limits (50 certs / week / eTLD+1) cap per-slug cert provisioning
- ALBs have a permanent cost even when no traffic

By building a vendor-neutral edge tier (OpenResty + DNS + commodity compute), we route around all of these. The whole stack is portable to Cloudflare, Fastly, Hetzner, bare metal — or split across providers for redundancy. We're not just solving the cert problem; we're decoupling the architecture from AWS-specific limitations so future provider moves (or multi-provider HA) are configuration changes, not rewrites.

## The escape hatch from CF + Lambda dependency

Worth noting for completeness, even though it's out of scope for the MVP: the CloudFront and Edge Waker Lambda dependency at the very top of the stack can also be removed. Replace CloudFront with an always-on edge proxy fleet (same OpenResty pattern, just bigger and managed differently) that holds the wildcard cert and does the cold-cold bootstrap itself. This gets you to a fully-portable, fully-self-hosted edge with no AWS dependency at all.

Not needed now — CF + Lambda is convenient and cheap — but it's a known evolution path if AWS-specific risks ever become unacceptable for a customer segment.

# What's AWS-specific vs portable

| Component | AWS choice | Portable replacement |
|---|---|---|
| CDN / TLS terminator | CloudFront + ACM | Cloudflare, Fastly, Bunny + their managed certs (or LE wildcard via DNS-01) |
| DNS | Route 53 | Cloudflare DNS, NS1, any |
| Edge fleet compute | EC2 | Any VM provider; OpenResty config unchanged |
| Target compute | EC2 / Fargate | Any VM / container service |
| Wakers | Lambda Function URLs | Any FaaS, or a small Go service |
| Boot lock | S3 If-None-Match | R2, MinIO, any S3-compatible store |

The Vault Waker is the most cloud-coupled component (talks `RunInstances` / `RunTask` APIs). Everything else is commodity.

# MVP scope

Recommended first cut, sequenced by *where the unknowns live*. The Vault Waker pattern is already proven in production (`send.sgraph.ai` uses DNS-driven backend lookup at scale). The OpenResty hot path is mechanically straightforward. The genuinely unproven piece is the **Edge Waker + cold-cold bootstrap dance** — CF origin-group failover under real load, S3 lock coordination under concurrent triggers, EC2 boot variance, DNS-propagation behavior at CF POPs when proxy IPs change. That's where the curve balls are. Build that first, in isolation.

**Phase 1 — prove the edge tier in isolation (the risky bit, build first):**

The target here is *not* a vault. It's a static site served directly by OpenResty itself — a small HTML page that responds with the proxy's instance ID, current timestamp, and a few diagnostic headers. The slug routing is short-circuited: any host arriving at the proxy is served the static page locally. This lets us hammer the edge tier without a target backend in the loop at all.

- One CloudFront distribution with wildcard ACM cert
- CloudFront Function (Host preservation, slug extraction)
- CF origin group: primary = `proxies.<parent>`, secondary = Edge Waker Function URL
- Edge Waker Lambda — full implementation: S3 conditional-write lock, EC2 RunInstances, SSM readiness polling, Route 53 A-record writes for `proxies.<parent>`
- OpenResty serving a static diagnostic site directly (no upstream proxying)
- Sidecar suite (Vector, CloudWatch agent, Edge Heartbeat) running and shipping data
- Cleanup + reaper logic for orphaned proxies

What we test against this rig:

```
+-----------------------------------------------------------------+
|  Test                            |  What it validates           |
+-----------------------------------------------------------------+
|  CF failover timing              |  Time from primary down to   |
|                                  |  Edge Waker invocation       |
|                                  |  (should be ~1-2s)           |
|                                  |                              |
|  Concurrent cold-cold triggers   |  S3 lock prevents duplicate  |
|                                  |  EC2 launches; loser returns |
|                                  |  loading page                |
|                                  |                              |
|  EC2 boot under stress           |  What happens when launch    |
|                                  |  takes 3min instead of 30s?  |
|                                  |  Does the loading page hold? |
|                                  |                              |
|  Mid-boot failure                |  Lock holder dies after EC2  |
|                                  |  launch but before DNS write |
|                                  |                              |
|  Proxy kill during traffic       |  Route 53 health checks +    |
|                                  |  CF retry behavior           |
|                                  |                              |
|  Aggressive teardown / boot      |  10+ cycles/day, watch for   |
|                                  |  resource leaks, orphans     |
|                                  |                              |
|  DNS propagation at CF POPs      |  How long after writing A    |
|                                  |  record does CF re-resolve?  |
|                                  |                              |
|  CloudFront cold-cold UX         |  End-to-end first-user       |
|                                  |  experience timing           |
+-----------------------------------------------------------------+
```

This phase has no dependency on the vault target work, no dependency on changes to the Vault Waker, and exercises every component that's genuinely new.

**Phase 2 — wire in vault targets:**

Once Phase 1 has validated the edge tier mechanics, swap the static-site short-circuit for the real routing:

- OpenResty Lua hot path (DNS TXT lookup, `shared_dict` caching, backend selection)
- Vault Waker extended to write A + TXT records on provision
- Self-signed cert on proxy (or stable cert from Secrets Manager — decided in Phase 1)
- Vault Reaper for orphan cleanup
- First end-to-end vault behind the edge

This phase is mostly integration work — the components are individually simpler than Phase 1, and most of the operational risk has been retired.

**Phase 3 — production hardening:**

- Multi-AZ proxy fleet (N >= 2)
- Active vault scaling thresholds and tuning
- Multi-region edge (one CF distribution per region, geo routing)
- Migration path for vaults still on `letsencrypt-hostname` (drain naturally; no forced migration)

**Explicitly out of scope:**
- Replacing the existing `sg vp` slug routing — keeps working in parallel; new traffic via edge, old vaults drain
- Removing CloudFront dependency (the "always-on OpenResty as CF replacement" escape hatch — flagged as a known evolution path, not built)
- Cross-cloud failover (Cloudflare DNS as Route 53 standby, etc.)

Rationale for this ordering: traditional MVP ordering says "ship the simplest thing first." For this architecture the simplest thing (Phase 2) is *also* the bit with the least risk and the most proven primitives. The risky bit (Phase 1) is hidden behind it. Inverting the order means we hit the curve balls early, with a test rig that can't fail in interesting ways, and gain confidence before adding the vault integration layer on top.

# Centralised logging — the security framing

The architecture has a property that's worth naming explicitly because security-sensitive customers will ask about it: TLS terminates at CloudFront, which sounds like it weakens the zero-knowledge story, but doesn't.

Three layers of defense make this safe:

1. **Encrypted payloads.** SG/Vault and SG/Send encrypt all file content client-side in the browser before any HTTP request leaves. CF and OpenResty see ciphertext bodies — request bodies and response bodies that contain user files are already AES-GCM encrypted with keys CF never holds. Centralised TLS termination doesn't change what CF can read; the answer is still "nothing meaningful."

2. **Metadata stripping in logs.** Client-identifying data (IP addresses in particular) is dropped from logs before persistence, matching the practice already in production at `send.sgraph.ai`. CloudFront access logs and OpenResty access logs are post-processed by Vector (or equivalent) to remove or hash client IPs before they reach long-term storage. Vector's `transforms.remap` makes this a one-liner per field.

3. **Wildcard key boundary.** The private key for the wildcard cert lives inside CloudFront's AWS-managed TLS terminator. It's never written to disk on any proxy, never exposed in any vault target, never accessible to any IAM role we own. AWS's TLS infrastructure is the same one that fronts millions of HTTPS sites — the trust boundary is well-established.

The net result: the architecture gains centralised observability (one place to look for "is the edge healthy?", "what's the per-slug request pattern?", "what's the cache hit rate?") without compromising the zero-knowledge story. Customers get to verify this by inspecting either codebase — vault for the encryption layer, edge for the logging-redaction layer.

```
+-----------------------------------------------------------------+
|              What the centralised edge can see                  |
+-----------------------------------------------------------------+
|  Layer                  |  What's visible to it                |
+-----------------------------------------------------------------+
|  CloudFront             |  URL path, response codes, byte      |
|                         |  counts. Client IP (then stripped).  |
|                         |  Cannot decrypt vault payloads —     |
|                         |  they were already ciphertext.       |
|                         |                                      |
|  OpenResty proxy        |  Same as CF plus request timing per  |
|                         |  upstream. Logs structured to        |
|                         |  Vector, which strips PII before     |
|                         |  shipping.                           |
|                         |                                      |
|  Vault target           |  Plain HTTP request bodies — but     |
|                         |  these are already ciphertext        |
|                         |  produced by browser-side AES-GCM.   |
+-----------------------------------------------------------------+
```

Worth adding a section to the public-facing security posture page once the architecture is live: "TLS is terminated at the edge; payloads are encrypted before transit; client metadata is stripped from all logs. Zero-knowledge holds end-to-end."

# Open questions

1. **Cert delivery to proxy.** Self-signed regenerated at boot, or one stable cert in Secrets Manager? Recommendation: self-signed at boot (no secret management), CF doesn't verify origin cert anyway.
2. **TXT record TTL.** 30s seems right (matches `shared_dict` cache TTL), but is 60s safer for cold-start propagation? Recommendation: 30s, with explicit verification step in Vault Waker readiness check.
3. **Where does the CloudFront Function live in code?** New module `sg_compute_specs/edge/cloudfront_function/`? Same repo as proxy config? Recommendation: same repo, since it co-evolves with the proxy.
4. **Scale-up trigger for proxy fleet.** Active vault count, or RPS to proxies, or CPU on proxy instances? Recommendation: active vault count is the simplest and aligns the scale story end-to-end.
5. **Log redaction pipeline.** Vector's `transforms.remap` handles IP stripping cleanly, but where exactly does the redaction happen — in Vector on each proxy before shipping, or in a central enrichment step? Recommendation: at the source (proxy-side) — keeps PII off the network, matches `send.sgraph.ai` current practice.
