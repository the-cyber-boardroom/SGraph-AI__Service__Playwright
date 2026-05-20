---
title: SG/Edge — proxy fleet & Edge Waker
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
scope: the edge tier — OpenResty proxies plus the Edge Waker that boots them
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__03-targets.md
---

# Scope

This document covers the always-on (or scale-to-zero) edge tier that sits between CloudFront and vault targets:

```
       (CloudFront)               (this document)             (vault targets)
            |                            |                            |
            v                            v                            v
   +-----------------+         +------------------+         +-----------------+
   |   CF + ACM      |  -----> |   SG/Edge fleet  |  -----> |   EC2 / Fargate |
   |   wildcard cert |  -----> |   N x EC2 +      |  -----> |   vault backend |
   |                 |         |   OpenResty      |         |                 |
   +-----------------+         +------------------+         +-----------------+
                                        ^
                                        |  provisions / scales / tears down
                                        |
                               +------------------+
                               |    Edge Waker    |
                               |    (Lambda)      |
                               +------------------+
```

Two components, tightly coupled: the proxy fleet (the data plane) and the Edge Waker (the control plane).

# Edge fleet — proxy instance internals

Each proxy instance is a single EC2 host running OpenResty and a small set of sidecars. The shape:

```
+-----------------------------------------------------------------------+
|                        EC2 instance (t4g.small)                       |
|                                                                       |
|   +-----------------------------+   +-----------------------------+   |
|   |        OpenResty            |   |       Edge Heartbeat        |   |
|   |        (nginx + Lua)        |   |     (systemd timer, 30s)    |   |
|   |                             |   |                             |   |
|   |  :443 self-signed HTTPS     |   |  writes /var/run/sg-edge/   |   |
|   |  :80  redirect to :443      |   |   heartbeat.json with last  |   |
|   |  :8089 /_edge/health        |   |   nginx stats, mem, uptime  |   |
|   |       /_edge/stats          |   +-----------------------------+   |
|   |       /_edge/version        |                                     |
|   |                             |   +-----------------------------+   |
|   |  shared_dict zones:         |   |          Vector             |   |
|   |    slug_cache  (50MB)       |   |     (log shipper)           |   |
|   |    health_cache (10MB)      |   |                             |   |
|   |    metrics    (5MB)         |   |  tails /var/log/nginx/*     |   |
|   |                             |   |  ships to CloudWatch Logs   |   |
|   +-----------------------------+   +-----------------------------+   |
|              ^                                                        |
|              |                      +-----------------------------+   |
|              | reads               |        CloudWatch Agent      |   |
|              |                      |                             |   |
|   +-----------------------------+   |  host metrics + custom      |   |
|   |  IAM instance role (minimal)|   |  metrics from /_edge/stats  |   |
|   |  - ec2:DescribeInstances    |   +-----------------------------+   |
|   |    (own instance only)      |                                     |
|   |  - logs:PutLogEvents         |   NO route53:* permissions!         |
|   |  - cloudwatch:PutMetricData |   NO route53:* permissions!         |
|   +-----------------------------+   NO route53:* permissions!         |
|                                                                       |
+-----------------------------------------------------------------------+
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
        Route 53 (TXT lookups)        Vault backends (HTTP)
        - read-only, no IAM needed    - in-region, plain :8080
        - resolver is just DNS        - no auth between proxy
                                        and target today
```

Critical security property: the proxy IAM role can't modify DNS, can't launch instances, can't read secrets. If a proxy is compromised, the blast radius is "this proxy can do what a proxy does — route HTTP requests and read DNS." It can't escalate to anything else.

The Edge Waker holds all privileged operations.

## OpenResty hot-path — what the Lua does

The routing logic is small. Three Lua phases:

```
+----------------------+   +----------------------+   +----------------------+
|   access_by_lua      |   |   balancer_by_lua    |   |    log_by_lua        |
|                      |   |                      |   |                      |
| 1. Read X-SG-Slug or |   | Set upstream from   |   | Structured log line  |
|    parse Host header |   | ngx.var.backend     |   | (slug, status,       |
| 2. Cache hit?         | --> | (set in access      | --> | latency, backend) |
|    -> set backend    |   | phase)              |   |                      |
|    -> done           |   |                      |   | Increment            |
| 3. Cache miss:       |   |                      |   | shared_dict.metrics  |
|    DNS TXT lookup    |   |                      |   |                      |
|    of _sg.<host>     |   |                      |   |                      |
| 4. Parse TXT v=1     |   |                      |   |                      |
| 5. Cache 30s         |   |                      |   |                      |
| 6. Set ngx.var       |   |                      |   |                      |
|                      |   |                      |   |                      |
| Errors:              |   |                      |   |                      |
|  no TXT -> 404       |   |                      |   |                      |
|  bad TXT -> 502      |   |                      |   |                      |
|  conn refused later: |   |                      |   |                      |
|   -> invalidate      |   |                      |   |                      |
|      cache,          |   |                      |   |                      |
|   -> trigger vault   |   |                      |   |                      |
|      waker async,    |   |                      |   |                      |
|   -> serve loading   |   |                      |   |                      |
|      page            |   |                      |   |                      |
+----------------------+   +----------------------+   +----------------------+
```

Pseudocode (~40 lines, real impl ~80 with error handling):

```
-- access_by_lua_block
local slug = ngx.var.http_x_sg_slug or extract_slug(ngx.var.host)
if not slug then return ngx.exit(400) end

local cache = ngx.shared.slug_cache
local cached = cache:get(slug)
if cached then
    ngx.var.backend = cached
    return  -- fast path, sub-microsecond
end

local resolver = require("resty.dns.resolver"):new{...}
local answers, err = resolver:query("_sg." .. ngx.var.host, { qtype = TXT })
if not answers or #answers == 0 then
    return ngx.exit(404)  -- no slug
end

local txt = answers[1].txt  -- e.g. "v=1;ip=10.0.1.5;port=8080;type=ec2"
local parsed = parse_sg_txt(txt)
if not parsed or parsed.v ~= "1" then return ngx.exit(502) end

local backend = parsed.ip .. ":" .. parsed.port
cache:set(slug, backend, 30)
ngx.var.backend = backend

-- balancer_by_lua_block
local b = require("ngx.balancer")
local ip, port = ngx.var.backend:match("([^:]+):(%d+)")
b.set_current_peer(ip, tonumber(port))

-- on upstream connection failure, invalidate and fire waker
-- (handled in proxy_pass error_page + small Lua block)
```

## Sidecar details

| Sidecar | Purpose | Resource cost |
|---|---|---|
| OpenResty | Main proxy | ~50-100MB RAM idle, scales with connections |
| Vector | Log shipping (nginx access + error + system) | ~20MB RAM |
| CloudWatch Agent | Host metrics + parses `/_edge/stats` JSON | ~30MB RAM |
| Edge Heartbeat | systemd timer, writes local heartbeat file | negligible |

No Redis, no DynamoDB client, no AWS SDK in the hot path. The only outbound calls from the proxy are: DNS lookups (free, no IAM), HTTP to vault backends, CloudWatch (via agent, batched), Vector log shipping (batched).

## Boot sequence — what happens when EC2 comes up

```
Time   Step
-----  ---------------------------------------------------------------
T+0    EC2 starts, user-data script begins
T+5    OS basics + cloud-init done
T+10   Pull sg-edge image from ECR (or already baked into AMI)
T+15   Generate self-signed cert for :443
T+18   Start OpenResty (listening, but not yet in DNS)
T+20   Start Vector + CloudWatch Agent
T+22   Start Edge Heartbeat systemd timer
T+25   Curl localhost:8089/_edge/health until 200
T+27   Write status to /var/run/sg-edge/ready
T+27   <Edge Waker detects readiness via SSM Run Command or similar>
T+30   <Edge Waker adds A record proxies.<parent> -> <this IP>>
T+30   Instance is now serving traffic
```

The instance never touches Route 53. The Edge Waker watches for `/ready` via SSM polling and writes DNS centrally. This keeps the proxy IAM role minimal.

# Edge Waker — the control plane

The Edge Waker is a Lambda Function URL exposed as the CloudFront origin-group secondary. Its job is to bring the fleet from zero to ready and keep it appropriately scaled.

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
|    - Acquire S3 lock (If-None-Match) to serialize boot decisions   |
|    - Provision EC2 proxy instances (RunInstances)                  |
|    - Poll for instance readiness (SSM Run Command)                 |
|    - Write proxies.<parent> A records to Route 53                  |
|    - Tear down idle proxies + remove their A records               |
|    - Return loading page on cold-cold (serves HTML directly)       |
|                                                                    |
|  IAM SCOPE (much wider than proxy):                                |
|    - ec2:RunInstances, ec2:TerminateInstances                      |
|    - ec2:DescribeInstances                                         |
|    - route53:ChangeResourceRecordSets (proxies.<parent> only)      |
|    - ssm:SendCommand, ssm:GetCommandInvocation                     |
|    - s3:PutObject, s3:GetObject (lock bucket)                      |
|    - logs:* (own log group)                                        |
|                                                                    |
+--------------------------------------------------------------------+
```

## Fleet state machine

The fleet has four states, transitioned by the Edge Waker:

```
       +------------+
       |    zero    |  <-- no proxies running, $0 baseline
       +------------+
             |
             | cold-cold trigger (CF failover)
             | + lock acquired
             v
       +------------+
       |  booting   |  <-- EC2 launched, waiting for readiness
       +------------+
             |
             | proxy /_edge/health green
             | + DNS A record added
             v
       +------------+      scale-up trigger     +------------+
       |   active   |  ---------------------->  |  scaling   |
       |   (N=1+)   |  <----------------------  |   (adding) |
       +------------+      proxy added          +------------+
             |
             | idle teardown trigger
             | (no vaults for X min)
             v
       +------------+
       | draining   |  <-- removed from DNS, waiting connections drain
       +------------+
             |
             | drain complete (60s)
             v
       (zero)
```

The S3 lock is held only during state transitions (zero -> booting -> active). Once active, the lock is released. Concurrent Lambda invocations during the active state are normal — they just observe the state and return.

## Cold-cold sequence — zoomed in

```
CloudFront      Edge Waker      S3 lock      EC2 API     SSM       Route 53
    |               |              |             |         |            |
    |--invoke------>|              |             |         |            |
    | (failover)    |              |             |         |            |
    |               |              |             |         |            |
    |               |--PUT lock--->|             |         |            |
    |               |  If-None-    |             |         |            |
    |               |  Match: *    |             |         |            |
    |               |<--201 OK-----|             |         |            |
    |               |  (won lock)  |             |         |            |
    |               |              |             |         |            |
    |               |--RunInstances------------>|         |            |
    |               |<--instance-id-------------|         |            |
    |               |                            |         |            |
    |<--HTML--------|                            |         |            |
    | loading page  |                            |         |            |
    |               |                            |         |            |
    |               |  (Lambda returns, re-invoked by poll-status)      |
    |               |                            |         |            |
    |               |--SendCommand check ready->                        |
    |               |   (poll every 5s via                              |
    |               |    /_edge/health)                                 |
    |               |                                                   |
    |               |        ...30-90s later...                         |
    |               |                                                   |
    |               |<--instance ready--                                |
    |               |                                                   |
    |               |--add A record proxies.cv.sgraph.ai-->             |
    |               |<--ok----------------------------------|           |
    |               |                                                   |
    |               |--update lock state to "active"----->|             |
    |               |<--ok-------------------------------|              |
    |               |--release lock---------------------|              |
```

Race condition handling: if two CF failover invocations arrive simultaneously, only one wins the S3 conditional write. The loser reads the lock, sees `state=booting`, returns the loading page directly to the user. The user's client polls `/edge-status/<request_id>` which the Edge Waker exposes; that endpoint reads the S3 lock state and reports back.

## Loading page (the cold-cold UX)

The Edge Waker returns HTML directly on cold-cold. The page:

1. Shows a friendly "spinning up edge infrastructure..." message
2. JS polls `/edge-status/<request_id>` every 2s
3. On `status=active`, reloads `window.location` — now hits the warm path
4. If the slug itself is cold, the proxy serves its own loading page (different waker, but same UX pattern)

Two layers of cold start, two layers of loading page, but to the user it looks like one continuous "we're getting your vault ready" experience. The existing Vault Waker UX already handles the second layer; the Edge Waker layer just wraps it.

## Scale-up logic

```
+-------------------------------------------------------------+
| Scheduled scale-check (EventBridge -> Edge Waker, every 1m) |
+-------------------------------------------------------------+
|                                                             |
|  active_vaults  = count of slug records in DNS              |
|  current_proxies = count of proxies.<parent> A records      |
|                                                             |
|  target_proxies = ceil(active_vaults / 200)                 |
|                  capped at [1, MAX_PROXIES]                 |
|                                                             |
|  if target_proxies > current_proxies:                       |
|      acquire lock; launch one more proxy; release lock      |
|                                                             |
|  if target_proxies < current_proxies                        |
|     AND time_since_last_scale > 5m:                         |
|      drain oldest proxy (remove from DNS, wait 60s, term.)  |
|                                                             |
+-------------------------------------------------------------+
```

The 200 vaults/proxy figure is a starting estimate. A t4g.small running OpenResty can handle far more — load testing will fine-tune the ratio. The cap (MAX_PROXIES) prevents runaway from being a runaway cost event.

## Idle teardown

```
+-------------------------------------------------------------+
|     Scheduled idle-check (EventBridge -> Edge Waker, 5m)    |
+-------------------------------------------------------------+
|                                                             |
|  active_vaults = count of slug records in DNS               |
|                                                             |
|  if active_vaults == 0:                                     |
|      if zero_streak >= 6 (i.e. 30 min of zero):             |
|          drain all proxies                                  |
|          state -> zero                                      |
|      else:                                                  |
|          zero_streak += 1                                   |
|  else:                                                      |
|      zero_streak = 0                                        |
|                                                             |
+-------------------------------------------------------------+
```

30 minutes of zero vaults before teardown is conservative — strong protection against teardown/boot thrash if vault activity is bursty. Tunable.

# Operational concerns

**Observability.** Every proxy ships nginx access logs + error logs to CloudWatch via Vector. Per-slug request rates and latencies land in CloudWatch Metrics via the agent reading `/_edge/stats`. Edge Waker emits structured events (boot started, boot succeeded, scale-up, teardown) to its own log group. A single CloudWatch dashboard shows active vaults, active proxies, p99 routing latency, cache hit rate.

**Failure modes.**

| Failure | Impact | Mitigation |
|---|---|---|
| One proxy dies | DNS keeps two A records, CF falls over within sub-second; Route 53 health checks remove dead IP within ~30s | Multi-AZ proxy fleet (N >= 2 in production) |
| All proxies die | CF falls back to Edge Waker, which detects and re-boots | Origin group is the safety net |
| Edge Waker fails | Cold-cold first request fails; warm path still works | Standard Lambda DLQ + retries |
| DNS propagation slow | New slug TXT not yet visible; OpenResty returns 404 | Vault Waker verifies record resolves before returning URL |
| Route 53 itself down | Whole architecture down | Multi-region Route 53 + Cloudflare DNS as standby is the long-term answer |

**CVE management.** The proxy AMI is rebuilt weekly via Packer, signed, and the latest is the only AMI the Edge Waker is configured to launch. New CVEs in OpenResty / Vector / system packages are picked up automatically. Existing proxies are not patched in-place — they're rolled by terminating the oldest and letting the scaler re-add.

**Cost at zero traffic.** Strictly $0 (Lambda not invoked, no EC2 running, CF and Route 53 have no fixed cost). The first user pays the cold-cold latency.

**Cost at steady state.** N proxies × (~$12/mo + LCU-equivalent CloudWatch costs). For 200 active vaults: 1 proxy ≈ $15/mo all-in.
