---
title: "04 — Lambda reverse-proxy mode"
file: 04__lambda-reverse-proxy.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 04 — Lambda reverse-proxy mode

## The idea

When the Lambda waker receives a request for a slug whose EC2 is
RUNNING and reachable, **proxy the request to the EC2** instead of
returning a warming page or relying on DNS to have propagated.

This is in fact what the waker already does when EC2 is fully
RUNNING + healthy (`Endpoint__Proxy.proxy(...)`). The proposal here
is to **broaden when the proxy kicks in** — specifically:

1. **Always** when path starts with `/.well-known/acme-challenge/`
   (cert challenge — see [03](03__lets-encrypt-catch-22.md)).
2. **Always** when EC2 is RUNNING and port 80 (or the workload port)
   responds — even before the "vault-app fully healthy" probe
   succeeds. (DNS-not-propagated window.)
3. **Optionally** during cert renewal: if a vault-app sets
   `proxy_mode: always` in its SSM entry, Lambda proxies every
   request regardless of DNS state. (Useful for staging / debugging
   environments where you want all traffic to flow through the
   observable Lambda path.)

## What changes vs today

Today's `Waker__Handler.handle` decision tree (simplified):

```
state = UNKNOWN                          → 404
state = STOPPED                          → start EC2, return warming HTML
state = PENDING / STOPPING               → return warming HTML (don't re-start)
state = RUNNING + workload healthy       → proxy request
state = RUNNING + workload NOT healthy   → return warming HTML
state = RUNNING + no IP                  → return warming HTML
```

Proposed:

```
if path startswith '/.well-known/acme-challenge/':
    if state = RUNNING + port 80 reachable    → proxy to EC2:80
    if state = STOPPED                        → start, return 503 retry-after: 5
    if state = PENDING                        → return 503 retry-after: 5
    else                                       → 404

else (normal request):
    state = UNKNOWN                            → 404
    state = STOPPED                            → start EC2, return warming HTML
    state = PENDING / STOPPING                 → return warming HTML
    state = RUNNING:
       if workload port reachable             → PROXY (regardless of full health)
       else                                   → return warming HTML
```

The key behavioural change for normal requests: **as soon as
`workload_port` responds at all**, we proxy. Today we wait for the
full health probe (`/ui/#!/login` returns 200). The change means the
window where the user sees a warming page shrinks dramatically —
from "EC2 boot + vault-app full boot + DNS propagation" down to just
"EC2 boot + workload-port-open" (often just a few seconds after EC2
RUNNING).

## What it enables

### A. Solves the LE catch-22 (see [03](03__lets-encrypt-catch-22.md)).

The `/.well-known/acme-challenge/*` path always reaches the EC2 via
the Lambda, even before per-slug DNS exists.

### B. Hides DNS propagation entirely from the user.

Today, when EC2 just booted, the user sees the warming page until
DNS propagates and their browser switches to the per-slug A record.
With reverse-proxy mode, the first request that lands on the Lambda
proxies through — so the user sees the vault UI *immediately*, then
silently transitions to direct EC2 access once their DNS cache
expires.

### C. Makes the waker a uniform observability point.

Today, after DNS propagates, traffic goes direct to EC2 and the
Lambda has no visibility. For some debugging use cases that's a
problem — "I can't see what requests Sara's vault is getting any
more". With an opt-in `proxy_mode: always` per-slug flag, all
traffic stays in the Lambda path and we get unified logs / metrics.

### D. Graceful slug deletion / move.

Deleting a slug today leaves the per-slug DNS record dangling
briefly (until the auto-DNS cleanup runs on EC2 stop). Requests in
that window get connection-refused. With reverse-proxy mode and
slug-no-longer-registered, the Lambda returns a proper 404 page.

Similarly, *moving* a slug to a new EC2 (re-publishing) becomes
seamless: Lambda always knows the current IP via SSM; clients with
stale DNS still get routed correctly.

## What it costs

### 1. More Lambda invocations / more traffic

Today, after DNS propagation, the Lambda is cold and idle. With
reverse-proxy on for non-trivial windows, the Lambda is in the data
path for every request — Lambda execution costs + egress costs scale
with usage.

**Mitigation:** the broader proxy only kicks in for:
- ACME paths (tiny, infrequent)
- The "EC2 just booted, DNS not propagated" window (seconds to a
  minute)
- Explicit `proxy_mode: always` (operator opt-in for specific slugs)

Steady-state usage of normal slugs is still "Lambda invoked once on
cold start, then direct DNS for hours/days". Cost impact: marginal.

### 2. Lambda response size limit

Lambda Function URLs cap response body at **6 MB** (un-base64'd) or
~10 MB (base64). Anything bigger fails. Vault-app pages today are
well under that, but file uploads / downloads via the proxied path
could blow it. We already handle this with a "page too large"
warning state (see waker-internals brief). The reverse-proxy mode
inherits that constraint.

### 3. Latency

Direct EC2:  client → DNS → EC2:443           = ~50–100 ms
Via Lambda:  client → CF → Lambda → EC2:80    = ~150–300 ms
                                                (Lambda cold start +
                                                 internal hop)

Adds ~100–200 ms per request. Acceptable for the "DNS not propagated
yet" transition window; would be annoying as a steady state. Hence
the per-slug `proxy_mode` flag is opt-in.

### 4. Streaming / WebSocket / SSE

Lambda Function URLs support response streaming (since 2023) but
don't support full duplex / WebSocket. If a vault-app uses
WebSockets, the proxy path doesn't work for those.

**Today's vault-app doesn't use WebSockets** — the vault UI is a
plain static React app talking to REST over HTTPS. So OK for now.
Future workloads with WebSocket might need the per-slug
`proxy_mode: never` to skip the broader proxy and rely purely on
DNS.

### 5. TLS termination

CloudFront terminates TLS for us. The Lambda → EC2 leg is HTTP
(port 80) inside our VPC / public internet. Fine for today's
architecture (the cert dance is exactly about getting HTTPS in
front), but worth being explicit: **the Lambda → EC2 hop is
plaintext.** If EC2 also serves on 443, the Lambda could prefer
HTTPS once cert exists; for the LE bootstrap window, plaintext to
port 80 is the only option.

## Configuration shape

Per-slug, in the SSM entry:

```python
class Schema__Vault_Publish__Entry(Type_Safe):
    # ... existing fields ...
    port           : int = 8080
    health_path    : str = '/ui/#!/login'

    # NEW
    proxy_mode     : Enum__Proxy_Mode = Enum__Proxy_Mode.AUTO
    acme_proxy     : bool             = True       # proxy /.well-known/acme-challenge/*
    workload_label : str              = 'vault'
```

```python
class Enum__Proxy_Mode(str, Enum):
    NEVER  = 'never'     # always serve warming HTML when waker is in path
    AUTO   = 'auto'      # proxy when EC2 is RUNNING + reachable; warming otherwise
    ALWAYS = 'always'    # always proxy; never serve warming HTML
```

Defaults (AUTO + acme_proxy=True) match the recommended new
behaviour. NEVER preserves today's behaviour for any slug that
wants it.

## Implementation sketch

1. **`Waker__Handler.handle`** gets the ACME-path early branch and
   the broader "RUNNING + port reachable" proxy condition.
2. **`Endpoint__Proxy.proxy`** is unchanged — it already does the
   HTTP forwarding via urllib3.
3. **`Endpoint__Proxy`** gains a port parameter (or reads
   `entry.port`). Today it's hard-coded to 8080-ish via vault_url.
4. **A new health probe** for "port reachable" — much cheaper than
   the full path probe. Just a TCP connect or a `HEAD /` with short
   timeout.
5. **Tests** — extend `lambda_entry_local.py` (from the waker brief)
   with `--proxy-mode auto/always/never` flags so we can exercise
   all three locally.

Estimated effort: 1–2 days, including tests.

## What we shouldn't do

- **Don't make reverse-proxy mandatory for all slugs.** Per-slug
  `proxy_mode: never` opt-out is essential for WebSocket workloads
  or anything that hits the 6 MB cap.
- **Don't rely on the proxy as a long-term replacement for direct
  DNS.** Direct DNS is cheaper, faster, and decouples the slug from
  the Lambda's availability. The proxy is a transition mechanism +
  edge-case handler, not a steady state for production traffic.
- **Don't proxy admin-style paths blindly.** If a vault-app exposes
  e.g. `/admin/dangerous-action`, going through the Lambda doesn't
  add a security layer. The Lambda is a *forwarder*, not a WAF. The
  vault-app retains its own auth.

## Open question

Should `proxy_mode` be in SSM (per-slug, default-driven) or in
CloudFront (origin-level, all-slugs)? SSM is more flexible (per-slug
override), CF would be one config knob to flip. Recommend SSM —
matches the per-slug ownership model we already have.
