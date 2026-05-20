---
title: SG/Edge — proxy fleet & Edge Waker
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
scope: the edge tier — OpenResty proxies plus the Edge Waker that boots them
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__03-targets.md
  - sg-edge__05-mvp-test-and-acceptance.md
---

# Scope

This document covers the (scale-to-zero) edge tier that sits between CloudFront and vault targets:

```
       (CloudFront)               (this document)             (vault targets)
            |                            |                            |
            v                            v                            v
   +-----------------+         +------------------+         +-----------------+
   |   CF + ACM      |  ----->  |  SG/Edge fleet   |  ----->  |   EC2 / Fargate |
   |   wildcard cert |  HTTP    |  N x EC2 +       |  HTTP    |   vault backend |
   |                 |          |  OpenResty       |          |                 |
   +-----------------+          +------------------+          +-----------------+
                                        ^
                                        |  provisions / scales / tears down
                                        |
                               +------------------+
                               |    Edge Waker    |
                               |    (Lambda)      |
                               +------------------+
```

Two components: the proxy fleet (the data plane) and the Edge Waker (the control plane). Plain HTTP everywhere inside AWS — TLS is terminated at CloudFront and the wildcard private key never leaves AWS-managed infrastructure.

# Edge fleet — proxy instance internals (MVP)

Each proxy instance is a single EC2 host running OpenResty and nothing else. No sidecars in the MVP — observability tooling lands in Phase 3 once the architecture is proven.

```
+-----------------------------------------------------------------------+
|                        EC2 instance (t4g.small)                       |
|                                                                       |
|   +-----------------------------+                                     |
|   |        OpenResty            |                                     |
|   |        (nginx + Lua)        |                                     |
|   |                             |                                     |
|   |  :80   plain HTTP           |                                     |
|   |  :8089 /_edge/health        |                                     |
|   |        /_edge/stats         |                                     |
|   |        /_edge/version       |                                     |
|   |        /_edge/slug_seen     |  <-- queried by Vault Reaper       |
|   |                             |                                     |
|   |  shared_dict zones:         |                                     |
|   |    a_cache     (10MB)       |                                     |
|   |    txt_cache   (50MB)       |                                     |
|   |    health_cache (10MB)      |                                     |
|   |    slug_seen   (20MB)       |  <-- last-success timestamp        |
|   |                             |       per slug; the liveness       |
|   |                             |       source-of-truth              |
|   |    metrics    (5MB)         |                                     |
|   |                             |                                     |
|   |  ENV: SERVERLESS_FAST_API_  |                                     |
|   |       KEY=<secret>          |  <-- injected as header on every   |
|   |                             |       proxy_pass; vault target's   |
|   |                             |       Serverless_Fast_API          |
|   |                             |       middleware validates         |
|   |                             |                                     |
|   |  Logging: nginx access log  |                                     |
|   |   to stdout, client IP      |                                     |
|   |   omitted from log_format   |                                     |
|   +-----------------------------+                                     |
|              ^                                                        |
|              |                                                        |
|   +-----------------------------+                                     |
|   |  IAM instance role          |                                     |
|   |  - ec2:DescribeInstances    |                                     |
|   |    (own instance only)      |                                     |
|   |  - logs:PutLogEvents        |                                     |
|   |    (own log group only)     |                                     |
|   |                             |                                     |
|   |  NO route53:* permissions   |                                     |
|   |  NO secrets:* permissions   |                                     |
|   |  NO acm:* permissions       |                                     |
|   +-----------------------------+                                     |
+-----------------------------------------------------------------------+
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
        Route 53 (DNS lookups)        Vault backends (HTTP)
        - read-only via resolver      - in-region, plain :8080
        - no IAM needed               - X-API-Key header injected
                                      - validated by vault's
                                        Serverless_Fast_API mware
```

Critical security property: the proxy IAM role can't modify DNS, can't launch instances, can't read secrets. If a proxy is compromised, the blast radius is "this proxy can do what a proxy does — route HTTP requests and read DNS." It can't escalate to anything else.

The `SERVERLESS_FAST_API_KEY` env var is the shared secret used between proxy and vault target (matching the existing `Serverless_Fast_API` pattern already in use elsewhere in the codebase). The proxy injects it as a request header on every upstream proxy_pass; the vault target's existing Serverless_Fast_API middleware validates it. This is defense-in-depth — the security group already restricts proxy→target traffic at the network layer, but the API key adds an application-layer check that survives security group misconfiguration and works identically in local development.

The Edge Waker holds all privileged operations.

## In-memory slug liveness — the proxies ARE the source of truth

The proxies are the long-lived components that actually see traffic for every slug. Rather than have vault targets phone home with a heartbeat (which would require SSM permissions on every vault, extra system services, etc.), the proxies track per-slug liveness in their `slug_seen` shared_dict. Every successful proxy_pass updates `slug_seen[slug] = now()`. This becomes the authoritative liveness signal for the Reaper — see `sg-edge__03-targets.md`.

The Reaper queries `/_edge/slug_seen` on each proxy (returns a JSON map of `{slug: last_seen_ts}`) and unions the results across the fleet. If no proxy has seen a slug in the last N minutes AND the EC2/Fargate instance referenced in TXT is no longer healthy, the slug's TXT record is removed. The proxy in-memory data is the long-lived ground truth; nothing extra is needed on the vault target side.

## Why no sidecars in MVP

Each sidecar would add boot time, memory pressure, configuration surface, and a separate failure mode to debug. The MVP scope is "prove that DNS-driven routing through OpenResty works end-to-end" — none of that needs Vector, CloudWatch agent, or Edge Heartbeat to be true.

Observability degrades gracefully without them: nginx access logs go to stdout, CloudWatch Logs captures stdout automatically (via the standard ECS/EC2 log driver). Per-slug metrics are exposed via `/_edge/stats` JSON and can be scraped on demand. CPU/memory comes from CloudWatch's native EC2 metrics.

The full sidecar suite is documented for Phase 3 below. For MVP, "fewer moving parts" wins.

## OpenResty hot-path — what the Lua does

Three Lua phases doing the work:

```
+----------------------+   +----------------------+   +----------------------+
|   access_by_lua      |   |   balancer_by_lua    |   |    log_by_lua        |
|                      |   |                      |   |                      |
| 1. Read X-SG-Slug or |   | Set upstream from    |   | nginx access log     |
|    parse Host header |   | ngx.var.backend      |   | with client IP       |
| 2. Cache hit for A?   |   | (set in access      |   | omitted              |
|    Miss -> DNS A     | --> | phase)              | --> |                      |
|    NXDOMAIN -> 404   |   |                      |   | Increment per-slug   |
|    page              |   |                      |   | counters in          |
| 3. Cache hit TXT?    |   |                      |   | shared_dict.metrics  |
|    Miss -> DNS TXT   |   |                      |   |                      |
|    NXDOMAIN -> waker |   |                      |   |                      |
|    Found -> parse    |   |                      |   |                      |
| 4. Check health      |   |                      |   |                      |
|    cache             |   |                      |   |                      |
| 5. Set ngx.var       |   |                      |   |                      |
|    .backend          |   |                      |   |                      |
|                      |   |                      |   |                      |
| On upstream fail:    |   |                      |   |                      |
|   invalidate health, |   |                      |   |                      |
|   trigger waker      |   |                      |   |                      |
|   async, serve       |   |                      |   |                      |
|   loading page       |   |                      |   |                      |
+----------------------+   +----------------------+   +----------------------+
```

Pseudocode for the access phase (~60-80 lines of actual Lua):

```
-- access_by_lua_block

local host = ngx.var.host
local slug = ngx.var.http_x_sg_slug or extract_slug(host)
if not slug then return ngx.exit(400) end

-- Step 1: A record check
local a_cache = ngx.shared.a_cache
local a_status = a_cache:get(slug)
if a_status == nil then
    local resolver = require("resty.dns.resolver"):new{...}
    local answers, err = resolver:query(host, { qtype = A })
    if not answers or answers.errcode == 3 then  -- NXDOMAIN
        a_cache:set(slug, "nxdomain", 60)
        return serve_slug_not_found(slug)
    end
    a_cache:set(slug, "exists", 300)
elseif a_status == "nxdomain" then
    return serve_slug_not_found(slug)
end

-- Step 2: TXT lookup
local txt_cache = ngx.shared.txt_cache
local txt = txt_cache:get(slug)
if txt == nil then
    local answers, err = resolver:query("_sg." .. host, { qtype = TXT })
    if not answers or answers.errcode == 3 then
        txt_cache:set(slug, "nxdomain", 5)  -- short TTL!
        return trigger_waker_and_serve_loading_page(slug)
    end
    txt = answers[1].txt
    txt_cache:set(slug, txt, 30)
elseif txt == "nxdomain" then
    return trigger_waker_and_serve_loading_page(slug)
end

local parsed = parse_sg_txt(txt)
if not parsed or parsed.v ~= "1" then return ngx.exit(502) end

-- Step 3: health cache
local health = ngx.shared.health_cache:get(slug)
if health == "unhealthy" then
    return trigger_waker_and_serve_loading_page(slug)
end

ngx.var.backend = parsed.ip .. ":" .. parsed.port

-- balancer_by_lua_block
local b = require("ngx.balancer")
local ip, port = ngx.var.backend:match("([^:]+):(%d+)")
b.set_current_peer(ip, tonumber(port))

-- on upstream failure (handled in proxy_pass error block):
-- ngx.shared.health_cache:set(slug, "unhealthy", 10)
-- (next request for this slug falls through to waker path)
```

The implementation has a few details worth noting:

- **DNS resolver** uses OpenResty's `lua-resty-dns`, configured against the VPC resolver (typically `169.254.169.253` on EC2). No external DNS calls.
- **Negative caching** must be asymmetric — long for A NXDOMAIN (60s), short for TXT NXDOMAIN (5s). See the TTL reasoning in `sg-edge__01-solution-overview.md`.
- **Waker invocation** is async via `ngx.timer.at` — fires off an HTTP call to the Edge Waker's Function URL but doesn't block the response. The proxy returns the loading page in the same request.
- **Loading page** is HTML+JS served from disk (`/var/www/loading.html`), polls `<slug>.<parent>/_edge/wait-status` which OpenResty handles directly (checks TXT cache; returns ready=true when present).
- **Slug-not-found rate limiting** uses nginx's `limit_req_zone` keyed on `$remote_addr` with a low rate (e.g. 5/sec) for requests that resolve to NXDOMAIN. Cheap to serve, hard to weaponize.

## Boot sequence — what happens when a proxy comes up

```
Time   Step
-----  ---------------------------------------------------------------
T+0    EC2 starts, user-data script begins
T+5    OS basics + cloud-init done
T+10   Pull OpenResty container image from ECR (or already baked in AMI)
T+12   Start OpenResty (listening on :80 immediately)
T+15   localhost:8089/_edge/health returns 200
T+15   Edge Waker (polling HTTP) detects readiness via direct
       probe of <instance-private-ip>:8089/_edge/health
T+18   Edge Waker adds A record proxies.<parent> -> <this IP>
T+18   Instance is now serving traffic
```

The instance never touches Route 53 and has no AWS API calls in the boot path. The Edge Waker polls the proxy's HTTP health endpoint directly (over the VPC private network) and writes DNS centrally. This keeps the proxy IAM role minimal — `logs:PutLogEvents` is the only privileged action, no SSM, no nothing else.

Why HTTP probe instead of a coordination service: same reason the rest of the architecture avoids them. The Edge Waker already has the instance ID (from `RunInstances`) and can resolve its private IP (from `DescribeInstances`), so polling its `/_edge/health` endpoint is a single GET that needs no setup. The instance doesn't write anything to signal readiness; "readiness" is just "HTTP server answers." This works identically locally with a docker-compose service — same code path.

Without sidecars and certificate generation, the boot path is ~18s start-to-serving (vs ~27s in the earlier design with sidecars and self-signed cert). A real measurement against EC2 boot variance is in scenario P-07 of `sg-edge__05-mvp-test-and-acceptance.md`.

# Edge Waker — the control plane

The Edge Waker is a Lambda Function URL exposed as the CloudFront origin-group secondary. It bootstraps the fleet from zero, scales it up under load, and tears it down when idle.

```
+--------------------------------------------------------------------+
|                         Edge Waker (Lambda)                        |
+--------------------------------------------------------------------+
|                                                                    |
|  TRIGGERS:                                                         |
|    1. CF origin-group failover (cold-cold, primary unreachable)    |
|    2. Scheduled: scale check every 1 min                           |
|    3. Scheduled: idle-teardown check every 5 min                   |
|    4. Manual invocation (admin CLI)                                |
|                                                                    |
|  RESPONSIBILITIES:                                                 |
|    - Provision EC2 proxy instances (RunInstances)                  |
|    - Poll instance readiness via direct HTTP probe on              |
|      <instance-private-ip>:8089/_edge/health                       |
|    - Write proxies.<parent> A records to Route 53                  |
|    - Tear down idle proxies + remove their A records               |
|    - Return loading page on cold-cold (serves HTML directly)       |
|    - Parallel-fork to Vault Waker for the slug requested,          |
|      so target and proxy boot in parallel on cold-cold             |
|                                                                    |
|  IAM SCOPE:                                                        |
|    - ec2:RunInstances, ec2:TerminateInstances                      |
|    - ec2:DescribeInstances                                         |
|    - route53:ChangeResourceRecordSets (proxies.<parent> and        |
|      _state.<parent> only)                                         |
|    - route53:ListResourceRecordSets (read _state.<parent> for      |
|      zero_streak counter)                                          |
|    - lambda:InvokeFunction (to fire parallel Vault Waker)          |
|    - logs:* (own log group)                                        |
|                                                                    |
|  NO SSM. NO S3 lock. NO DynamoDB.                                  |
|  All Edge Waker state lives in DNS — convergent reconciliation.    |
|                                                                    |
+--------------------------------------------------------------------+
```

## Convergent reconciliation — no locking

Rather than holding a lock during boot transitions, the Edge Waker reads ground truth from DNS and reconciles toward the target. Every invocation does the same loop:

```
+-------------------------------------------------------------+
| Reconciliation step (every Edge Waker invocation)           |
+-------------------------------------------------------------+
|                                                             |
|  1. Count healthy proxies                                   |
|     current = count of A records under proxies.<parent>     |
|                                                             |
|  2. Determine target (MVP - static)                         |
|     active_vaults = count of _sg.*.<parent> TXT records     |
|     if active_vaults == 0:                                  |
|         target = 0                                          |
|     else:                                                   |
|         target = EDGE_PROXY_TARGET_COUNT  (e.g. 2)          |
|                                                             |
|     (Phase 3 will replace the static value with a           |
|      load-derived function. The reconciliation loop is      |
|      identical either way.)                                 |
|                                                             |
|  3. Determine what to do                                    |
|     if current < target:                                    |
|         launch (target - current) new proxies               |
|                                                             |
|     if current > target AND idle_long_enough:               |
|         drain (current - target) proxies                    |
|                                                             |
|  4. Return                                                  |
|     (next invocation will re-read state and reconcile       |
|     further if needed)                                      |
|                                                             |
+-------------------------------------------------------------+
```

Race-safety properties:

- Two concurrent invocations both deciding to add a proxy: one extra `t4g.small` boots. Idle teardown removes it within minutes. Cost: cents.
- Two concurrent invocations both deciding to terminate: `TerminateInstances` is idempotent on the same instance ID; one succeeds, the other is a no-op.
- Two concurrent invocations both calling `route53:ChangeResourceRecordSets` with `UPSERT`: idempotent; Route 53 deduplicates.

The traffic shapes where over-provisioning could become expensive (thousands of concurrent cold-cold triggers per minute) are precisely the shapes where the operator has already switched to always-on proxies, eliminating the cold-cold path entirely. The cycle-tolerant design is correct at both ends.

## Cold-cold sequence — parallel-boot variant

The cold-cold flow forks two parallel tracks: proxy fleet boot (track A) and vault target boot (track B). Neither depends on the other.

```
CloudFront      Edge Waker          EC2 API      Vault Waker     Route 53
    |               |                  |              |              |
    |--invoke------>|                  |              |              |
    | (failover)    |                  |              |              |
    |               |                  |              |              |
    |               |--TRACK A: proxy fleet           |              |
    |               |  RunInstances------------------->              |
    |               |<--instance-id--------------------              |
    |               |                                                |
    |               |--TRACK B: vault for requested slug              |
    |               |  InvokeFunction (Vault Waker)->|               |
    |               |                                |               |
    |<--HTML--------|                                |               |
    | loading page  |                                |               |
    |               |                                |               |
    |               | (both tracks run concurrently)                 |
    |               |                                |               |
    |               |--HTTP probe /_edge/health (poll)              |
    |               |   on track A's instance IP                    |
    |               |                               |               |
    |               |                              ...vault target  |
    |               |                                 boots         |
    |               |                                |               |
    |               |<--track A: instance ready--                    |
    |               |--add A record (proxies.<parent>)-------------> |
    |               |                                |               |
    |               |                               <--track B:      |
    |               |                                  TXT written   |
    |               |                                                |
    |               | (both tracks complete; client polling          |
    |               |  detects ready, reloads)                       |
```

Cold-cold total time = `max(track A, track B)` plus CF DNS-cache refresh at the POP (~10-30s) plus the client poll interval (negligible). Typical ~30-90s, worst case ~120s.

If only the proxy fleet is cold (vault target is already up, e.g. someone hit it directly via a different mechanism), track B is a no-op — Vault Waker checks the slug status, sees a healthy backend, returns immediately. Cheap to fire speculatively.

Race condition handling for the cold-cold case: if two CF failover invocations arrive simultaneously, both fire `RunInstances` on track A. Worst case is two proxies boot instead of one — both will work, both will register their A records, the second will get idle-teardown'd within minutes if not needed. This is fine. No explicit coordination required.

## Loading page (the cold-cold UX)

The Edge Waker returns HTML directly on cold-cold. The page:

1. Shows a friendly "spinning up infrastructure..." message
2. JS polls `<slug>.<parent>/_edge/wait-status` every 2s
3. The status endpoint is served by OpenResty (once the proxy is up) and checks TXT presence + backend health
4. On `status=ready`, reloads `window.location` — now hits the warm path

Two layers of cold start (edge fleet + vault target) are hidden behind one continuous loading screen. The Edge Waker fires track B in parallel so the user doesn't see them sequenced.

## Scale-up logic

**MVP: static count.** The MVP runs with a predefined number of proxy instances (configured per parent domain, e.g. `EDGE_PROXY_TARGET_COUNT=2`). The Edge Waker maintains the count — boots replacements when proxies die, but doesn't try to auto-scale based on traffic. This is intentional: we don't yet have load-test data to choose the right scaling metric (active vault count vs RPS vs CPU vs concurrent connections), and the bench environment will produce that data in Phase 1/2.

The static-count model already exercises every architectural mechanism (cold-cold boot, idle teardown, DNS reconciliation, parallel boot) — the dynamic decision-making is the part being deferred, not the underlying mechanics.

**Phase 3: data-driven dynamic scaling.** Once we have real load-test results, dynamic scaling lands. The shape is sketched here for context but is not built for MVP:

```
+-------------------------------------------------------------+
| Scheduled scale-check (EventBridge -> Edge Waker, every 1m) |
+-------------------------------------------------------------+
|                                                             |
|  active_vaults  = count of _sg.*.<parent> TXT records       |
|  current_proxies = count of A records under proxies.<parent>|
|                                                             |
|  target_proxies = <function-of-load-metric>                 |
|                  capped at [1, MAX_PROXIES]                 |
|                                                             |
|  if target_proxies > current_proxies:                       |
|      launch one more proxy                                  |
|      (no lock needed - eventually converges)                |
|                                                             |
|  if target_proxies < current_proxies                        |
|     AND time_since_last_scale > 5m:                         |
|      drain oldest proxy (remove from DNS, wait 60s, term.)  |
|                                                             |
+-------------------------------------------------------------+
```

The metric (`active_vault_count / N`, `rps_per_proxy`, CPU avg, etc.) and threshold (`N`) come out of Phase 1/2 measurements. Until then, static count is the right answer.

## Idle teardown

```
+-------------------------------------------------------------+
|     Scheduled idle-check (EventBridge -> Edge Waker, 5m)    |
+-------------------------------------------------------------+
|                                                             |
|  active_vaults = count of _sg.*.<parent> TXT records        |
|                                                             |
|  if active_vaults == 0:                                     |
|      if zero_streak >= IDLE_TEARDOWN_THRESHOLD:             |
|          drain all proxies                                  |
|      else:                                                  |
|          zero_streak += 1                                   |
|  else:                                                      |
|      zero_streak = 0                                        |
|                                                             |
+-------------------------------------------------------------+
```

`IDLE_TEARDOWN_THRESHOLD` is the knob that controls scale-to-zero aggressiveness. The trade-off:

- **Aggressive (e.g. 3 = 15 minutes idle):** minimizes cost when traffic is bursty; first user after the window pays cold-cold latency.
- **Conservative (e.g. 12 = 60 minutes idle):** smoother UX, more cost when occasional traffic keeps the fleet warm.

The per-parent-domain configurability of this knob is part of the commercial story in `sg-edge__04-commercial-angles.md` — different customer tiers can have different teardown thresholds.

The state stored to track `zero_streak` lives in a DNS TXT record at `_state.<parent>` — a single TXT record per parent domain holding the current counter value (e.g. `"zero_streak=2;updated=1747700000"`). Read on every idle check, written when it changes. This keeps the DNS-as-registry pattern complete: every piece of Edge Waker state is in DNS, nowhere else. Concurrent updates use Route 53's `UPSERT` semantics — if two invocations race, the last write wins, but the counter only ever needs to be approximately right (off-by-one across a 5-minute interval doesn't matter for an idle-teardown threshold of 3-12 intervals).

This eliminates the only remaining SSM dependency. The complete Edge Waker state model: `proxies.<parent>` A records (fleet membership), `_state.<parent>` TXT (zero_streak), and `_sg.<slug>.<parent>` TXT records (read-only, observed). Three record types, all DNS, no other coordination service.

# Phase 3 — production hardening (deferred from MVP)

For completeness, what the proxy instance will gain in Phase 3:

```
+-------------------------------------------------------------+
|              Phase 3 sidecar additions                      |
+-------------------------------------------------------------+
|                                                             |
|   Vector              Log shipping (nginx access + error    |
|                       + system) to CloudWatch or external   |
|                       SIEM. Strips additional PII fields.   |
|                                                             |
|   CloudWatch Agent    Host metrics + scrapes /_edge/stats.  |
|                                                             |
+-------------------------------------------------------------+
```

For scale decisions in Phase 3, the Edge Waker queries `/_edge/stats` and `/_edge/slug_seen` directly on each proxy over HTTP (the same mechanism the Reaper already uses). No separate heartbeat sidecar is needed — the proxy is reachable, the data is there, the Edge Waker just polls. Consistent with the no-SSM, no-coordination-service principle.

Multi-AZ proxy fleet (N>=2 minimum), multi-region edge (one CloudFront distribution per geographic region, latency-based DNS at the parent level), CVE management via weekly AMI rebuilds, automated proxy rolling.

None of this is needed for MVP. The architecture's correctness can be demonstrated without it. Phase 3 turns the architecture from "works in principle" into "operationally ready for paying customers."

# Operational concerns (MVP-level)

**Observability.** nginx access logs (with client IP stripped) go to stdout. EC2's default log driver ships stdout to CloudWatch Logs. `/_edge/stats` exposes per-slug counters as JSON. Single CloudWatch dashboard tracks active vaults, active proxies, error rate. Good enough to validate Phase 1 and Phase 2.

**Failure modes.**

| Failure | Impact | Mitigation |
|---|---|---|
| One proxy dies | DNS A record stays for ~30s (TTL), CF retries other origins; Route 53 health checks (Phase 3) remove dead IP within ~30s | N>=2 in production; MVP accepts the brief gap |
| All proxies die | CF falls back to Edge Waker secondary, which detects and re-boots | Origin group is the safety net; cold-cold path |
| Edge Waker fails | Cold-cold first request fails; warm path still works | Standard Lambda DLQ + retries |
| DNS propagation slow | New slug TXT not yet visible; OpenResty serves loading page | Short TXT NXDOMAIN cache TTL (5s) catches it fast |
| Route 53 itself down | Whole architecture down | Multi-region Route 53 + Cloudflare DNS as standby is the Phase 3 answer |

**Cost at zero traffic.** Strictly $0 (Lambda not invoked, no EC2 running, CF and Route 53 have no fixed cost beyond ~$0.50/mo per zone). The first user pays the cold-cold latency.

**Cost at steady state.** N proxies x (~$12/mo on-demand `t4g.small` plus CloudWatch costs). For 200 active vaults: 1 proxy ≈ $15/mo all-in.
