---
title: "03 — The Let's Encrypt catch-22"
file: 03__lets-encrypt-catch-22.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 03 — The Let's Encrypt catch-22

## The setup

Every published vault gets a per-slug DNS name —
`sara-cv.aws.sg-labs.app` — that needs to serve **HTTPS** for the
vault UI to work in a browser. The vault-app uses Let's Encrypt to
issue + auto-renew the cert. LE offers two challenge types we could
use:

- **HTTP-01** — LE makes an HTTP request to
  `http://sara-cv.aws.sg-labs.app/.well-known/acme-challenge/<token>`
  and checks the response. Whoever can serve that path "owns" the
  domain.
- **DNS-01** — LE asks us to publish a TXT record at
  `_acme-challenge.sara-cv.aws.sg-labs.app` with a specific value.
  Whoever can control DNS "owns" the domain.

## The catch-22 with HTTP-01

```
Time T₀: operator runs `sg vault-publish register sara-cv`
   ↓
   • Slug__Registry.put(sara-cv → instance-id i-0abc)
   • Vault_App__Service.create_stack(sara-cv) starts an EC2.
   • Per-slug DNS record NOT YET created (auto-DNS runs on EC2 boot)

Time T₀ + 5s: EC2 boots, vault-app stack starts up.
   ↓
   • EC2's auto-DNS script registers
     sara-cv.aws.sg-labs.app A → <ec2-public-ip>
   • DNS propagates (~30 s with TTL 60).

Time T₀ + 30s: vault-app inside EC2 tries to fetch its cert.
   ↓
   • calls certbot / acme-tiny / etc.
   • LE responds: "ok, serve /.well-known/acme-challenge/abc123 at
     http://sara-cv.aws.sg-labs.app/"
   • LE then makes its validation request.

Time T₀ + 30s: LE's request to http://sara-cv.aws.sg-labs.app/.well-known/acme-challenge/abc123
   ↓
   • If DNS has propagated → goes to EC2 → cert issued. ✓
   • If DNS HAS NOT propagated yet → goes to CloudFront wildcard →
     Lambda waker → waker has no idea about this challenge →
     returns 404 warming page → LE sees the wrong content → cert
     denied. ✗
```

**The race is real.** Auto-DNS registers the per-slug record on EC2
boot, but DNS propagation (even at TTL 60) takes 30–60 s. LE doesn't
wait; if validation fails it just fails and certbot retries with
exponential backoff. We've seen this make the first-ever cert take
5–15 minutes to issue, or fail entirely if the operator gives up.

The DNS-01 path avoids the HTTP round-trip but has its own headaches
(see below).

---

## Three options

### Option 1 — HTTP-01 + Lambda reverse-proxy for `/.well-known/acme-challenge/*`

The Lambda waker, when it sees a request whose path starts with
`/.well-known/acme-challenge/`, forwards it to the EC2 instance for
that slug — bypassing DNS entirely. EC2 serves the challenge, LE is
satisfied, cert issues.

```
LE → sara-cv.aws.sg-labs.app/.well-known/acme-challenge/abc
   → DNS resolves to CloudFront (wildcard)
   → CF forwards to Lambda waker
   → waker: "ACME path detected"
   → waker resolves slug → EC2 IP
   → waker proxies request to http://<ec2-ip>/ on port 80
   → EC2 serves the challenge token
   → response flows back: CF → LE
   → cert issued ✓
```

**Pros:**
- Solves the catch-22 deterministically — no wait for DNS.
- Re-uses the proxy machinery the waker already has.
- The same reverse-proxy mode is useful for other "DNS hasn't
  propagated yet" cases (see [04](04__lambda-reverse-proxy.md)).

**Cons:**
- Requires the EC2 to serve HTTP on port 80 *before* cert is issued
  (vault-app already does this for the ACME challenge stage; not new
  work, just enshrining current behaviour).
- Lambda needs to know the EC2 IP at the moment the challenge
  arrives. If EC2 hasn't started yet (slug newly registered, no
  prior request), the proxy fails. **Mitigation**: `register`
  triggers an immediate Lambda warm-up call that brings up the EC2
  before LE asks. Or even simpler: `register` calls
  `ec2.start_instances` synchronously before returning, so by the
  time DNS could possibly be queried, EC2 is at least PENDING.

---

### Option 2 — DNS-01 challenge (EC2 publishes a TXT record via Route 53)

The vault-app on EC2 has an IAM role with `route53:ChangeResourceRecordSets`
on our hosted zone. Cert issuance:

```
certbot on EC2 → LE: "please challenge me via DNS-01"
   → LE: "publish TXT _acme-challenge.sara-cv.aws.sg-labs.app = abc"
   → certbot on EC2 → Route 53 ChangeResourceRecordSets
   → wait for DNS propagation (~30 s)
   → certbot: "go check"
   → LE checks TXT record, sees abc, issues cert ✓
```

**Pros:**
- Doesn't need any HTTP traffic to reach the EC2. The whole cert
  dance is via API calls.
- Doesn't depend on Lambda being in the path.
- Standard pattern for wildcards (we'd need DNS-01 anyway if we ever
  wanted `*.something` certs).

**Cons:**
- EC2 needs Route 53 permissions on our hosted zone. Per-slug IAM
  role + tag-based condition can constrain this, but it's still
  giving every vault EC2 the ability to write DNS records for the
  zone.
- More moving parts on the EC2 side: certbot DNS-01 hook scripts.
- Doesn't help with the broader "DNS-not-propagated-yet" UX issue;
  it only solves the cert problem.

---

### Option 3 — Pre-provision certs centrally; share them to EC2 via SSM/S3

A central process (the operator's machine, or a separate Lambda)
issues the cert for `sara-cv.aws.sg-labs.app` using DNS-01 via
Route 53, then drops the cert files into SSM Parameter Store
(encrypted) or a private S3 bucket. EC2 reads them on boot.

**Pros:**
- EC2 needs no LE / Route 53 permissions.
- Renewal happens centrally on a schedule, no per-EC2 cron.

**Cons:**
- Whole new component (cert-issuer service / Lambda).
- Need to handle key distribution + rotation safely.
- Decouples cert lifecycle from EC2 lifecycle, which is conceptually
  cleaner but means more state to manage centrally.
- Doesn't solve the "first request goes to a vault with no cert yet"
  issue — same DNS race exists; just now the cert is in SSM waiting
  for EC2 to pick it up.

---

## Recommendation: Option 1 (HTTP-01 + Lambda reverse-proxy)

The reverse-proxy mode is independently valuable (see
[04](04__lambda-reverse-proxy.md)). Solving the cert catch-22 is
one of several use cases it enables. Option 2 (DNS-01) is fine for
cert specifically but doesn't help the other use cases.

**Concrete plan:**

1. **`register` warms the EC2 synchronously.** Before returning,
   `Vault_Publish__Service.register` calls `ec2.start_instances` on
   the new instance — so the moment the Lambda receives the first
   request for that slug, the EC2 is already booting (or running).

2. **Lambda detects ACME path early.** In `Waker__Handler.handle`,
   right after slug resolution, check if `ctx.path` starts with
   `/.well-known/acme-challenge/`. If yes, force-proxy regardless of
   the usual healthy/unhealthy logic — even if the EC2 is mid-boot,
   port 80 is up by the time vault-app stack starts the cert dance.

3. **Per-slug cert path stays on the EC2.** No central cert store.
   Vault-app keeps its current cert issuance flow; the catch-22 is
   resolved by the Lambda being a backstop while DNS settles.

4. **Once DNS propagates**, traffic for `sara-cv` skips Lambda
   entirely — same as today.

5. **Renewals** (30/60/90 days later) might or might not hit
   Lambda depending on DNS state. Either way, the same reverse-proxy
   path works.

**Why not DNS-01?**

DNS-01 is cleaner in isolation but means giving every vault EC2 IAM
permissions on our root hosted zone. Per-slug tag conditions help,
but the blast radius of a compromised vault becomes "rewrite DNS for
the whole zone" — not great. With Option 1, the vault EC2 needs
nothing on our AWS account beyond what it already has.

DNS-01 also doesn't solve the "I deleted the slug but the DNS record
is stale and traffic still tries to reach a dead IP" UX problem;
reverse-proxy mode handles that case too by returning a proper
warming/404 page from the Lambda.

---

## Open questions

1. **Port 80 on EC2 — is it always open during cert dance?** Need to
   confirm vault-app's nginx/caddy listens on 80 from boot, not only
   after cert exists. (If it doesn't, vault-app needs a tiny change:
   listen on 80, serve `/.well-known/acme-challenge/*` plainly,
   redirect everything else to 443.)
2. **What does the Lambda do when the EC2 is STOPPED and an ACME
   request arrives?** Probably: start the EC2, return 503
   "challenge-server-warming" so LE retries in 5 s. Not pretty, but
   LE retries are part of its protocol; should work.
3. **Caching.** CloudFront is configured to disable caching for our
   distribution. Need to confirm `/.well-known/acme-challenge/*`
   isn't accidentally cacheable per any AWS default. (Belt-and-
   braces: explicit `Cache-Control: no-store` on the proxied
   response.)
