# Edge and Routing

How a request for `https://<slug>.sgraph.app/` reaches the right vault, and how a
stopped instance gets woken.

---

## 1. Wildcard DNS

Route 53 hosts `sgraph.app`. One ALIAS/A record per environment wildcard points at
the single CloudFront distribution:

```
  *.sgraph.app        ALIAS  → dxxxx.cloudfront.net
  *.qa.sgraph.app     ALIAS  → dxxxx.cloudfront.net
  *.dev.sgraph.app    ALIAS  → dxxxx.cloudfront.net
  *.main.sgraph.app   ALIAS  → dxxxx.cloudfront.net
```

DNS is provisioned **once**. No per-slug record. No propagation wait at publish
time. All AWS calls go through `osbot-aws` (locked decision #14).

**Single-label rule.** A wildcard matches exactly one label. `*.sgraph.app` does
not cover `slug.qa.sgraph.app` — that needs `*.qa.sgraph.app`. Region-in-hostname
(`slug.eu-west-1.sgraph.app`) would need `*.eu-west-1.sgraph.app`, and so on. The
environment list is closed and known; the region list, when it comes, must also be
closed. This is the whole reason region routing is deferred (locked decision #15).

---

## 2. Wildcard certificate

One ACM certificate, issued in `us-east-1` (CloudFront's requirement), DNS-validated
against the Route 53 zone. Its SANs are the four environment wildcards above. ACM
auto-renews DNS-validated certificates as long as the validation records remain in
the zone — DevOps must confirm this and monitor it (see `09__dev-ops`).

---

## 3. CloudFront — one distribution

Alternate domain names = the four wildcards. The distribution's job is to pick an
origin per request and serve the response. Origin selection is where the phases
differ.

### Phase 1 — always-on, prove routing only

The instance is always running. CloudFront has a single dynamic origin resolution
step that maps the Host header to the slug's instance (VPC origin). No waking, no
failover. The goal is only to prove that `sara-cv.sgraph.app` reaches the
`sara-cv` instance over HTTPS with the wildcard cert.

### Phase 2a — wake-on-demand, simple form (recommended MVP)

CloudFront's origin is the **waker Lambda** (the `vault_publish` FastAPI app behind
a Lambda Function URL). Every request goes through it. The FastAPI:

1. extracts the slug from the forwarded Host header,
2. checks the instance state via `Instance__Manager`,
3. if **down** — runs the wake sequence (see §4) and returns the warming page,
4. if **up** — proxies the request to the per-slug EC2 (the Lambda is in the VPC
   and reaches the private instance directly).

This honours "as small as possible Lambda invoking FastAPI" exactly: the Lambda is
the router, and it routes by calling FastAPI routes. The cost is one Lambda hop on
warm requests. For light vault apps that is acceptable for an MVP — and it is
trivially simple, with no Lambda@Edge and no origin groups.

### Phase 2b — wake-on-demand, optimised (deferred)

Introduce **CloudFront origin failover** so warm traffic bypasses the Lambda:

```
  origin group
    ├─ primary   = the per-slug EC2 (VPC origin)
    └─ secondary = the waker Lambda Function URL
```

CloudFront sends every request to the primary. A stopped instance → connection
failure → CloudFront fails over to the secondary (the waker), which wakes it and
serves the warming page. Tune the origin connection timeout low (≈2 s, 1 attempt)
so failover is fast — the 30 s default is far too slow.

The open problem in Phase 2b is **per-slug primary origin selection**: a plain
origin group has a *fixed* primary, but each slug needs a *different* EC2. Options,
to be settled by a spike:

| Option | Note |
|--------|------|
| Lambda@Edge origin-request rewrites the origin per slug | Works, but Lambda@Edge has size limits, no env vars, runs globally — against principle 6. Keep it minimal: a slug→origin decision only. |
| Edge-cached slug→origin map | Slugs are immutable-ish and the set is small; an edge function can hold a periodically-refreshed map. Lowest per-request latency. |
| Edge function calls the FastAPI `/resolve` route | Cleanest code reuse, but adds a network hop on every request. |

**Do not build Phase 2b until the Phase 2a hop cost is measured.** The upstream
brief itself flagged "wildcard cert + Lambda@Edge routing performance" as research
required — this is that research item. Phase 2a ships value without needing it
resolved.

---

## 4. The wake sequence

Run by the waker (Phase 2a) or the failover secondary (Phase 2b):

1. Parse the slug from the Host header.
2. `Slug__Resolver` derives `(Transfer-ID, read key)`.
3. `Vault__Fetcher` fetches the immutable vault folder from `send.sgraph.ai`.
4. `Manifest__Verifier` verifies the manifest signature (key from the billing
   record). **Reject → return an error page, do not start anything.**
5. `Instance__Manager.start()` — idempotent: check state first, only `StartInstances`
   if stopped. The call returns immediately; it does not block on the instance
   becoming healthy.
6. `Control_Plane__Client` provisions the instance with a single-use key + the
   verified declarative manifest (see `05__provisioning`).
7. Return an auto-refreshing "warming up your vault (~20 s)" HTML page with
   `Cache-Control: no-cache` — see §5.
8. The instance boots, applies the manifest, arms its idle-shutdown timer, becomes
   healthy. The next request is served from the live instance.

The wake sequence is idempotent end to end — two cold requests arriving together
both run it, and `StartInstances`-if-stopped plus immutable inputs make that safe.

---

## 5. The warming page — not a redirect

Use an HTML page that polls, not an HTTP redirect. A redirect loop is fragile and
caches badly; a page that polls `/healthz` (or simply uses
`<meta http-equiv="refresh">`) gives the visitor feedback ("starting your vault,
~20 seconds") and breaks cleanly the moment the instance is up.

**Caching:** the warming response must be `no-cache` / min-TTL 0. If CloudFront
caches "still warming", a visitor keeps seeing it after the instance is live. In
Phase 2b, custom error responses have their own TTL — set it to a few seconds.

---

## 6. Idle → stop

Reuse the existing `sg lc` shutdown-timer pattern (locked decision #10). The
per-slug instance arms an idle-shutdown timer on boot; the waker re-arms it on
every cold hit (and the live instance re-arms it on activity). When traffic stops,
the instance stops itself — and the next visitor triggers the wake sequence again.
"One EC2 per slug" only stays affordable because idle instances are stopped.

---

## 7. Failover trigger constraints (Phase 2b)

CloudFront origin-group failover only fires for `GET`, `HEAD`, and `OPTIONS`, and
only on connection failures or `500/502/503/504`. For read-only vault sites that is
exactly the traffic shape, so it is not a limitation in practice — but note it, and
make sure the per-slug instances never legitimately return a bare `500` that would
be mistaken for "down".
