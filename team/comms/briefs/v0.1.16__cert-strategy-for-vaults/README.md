---
title: Cert strategy for vault provisioning — debrief for Claude-Web handoff
date: 2026-05-19
status: brief / discussion-input
audience: a fresh Claude-Web thread with no prior context
goal: explore options for HTTPS-on-vault that work around Let's Encrypt rate limits
---

# Context — what we have working

Three command surfaces can spin up a vault from scratch today, end-to-end in 30s-2min:

| Surface | Compute | Network entry | TLS today |
|---------|---------|---------------|-----------|
| `sg va` (vault-app) | EC2 (t3.medium, ~30-90s boot) | direct EC2 public IP, optional Route 53 A record | cert-init container on the EC2 runs ACME against Let's Encrypt; cert lands at `/certs/cert.pem` and vault binds `:443` |
| `sg vp` (vault-publish) | EC2 + slug routing | CloudFront wildcard `*.aws.sg-labs.app` → Waker Lambda → EC2 (or direct EC2 after DNS converges) | same cert-init container; cert for `<slug>.aws.sg-labs.app` |
| `sg va fargate` (just landed v0.2.33) | Fargate task (~20-30s to RUNNING) | direct task public IP, optional Route 53 A record | **none — vault is on plain HTTP :8080** ← the gap |

The end-state user URL is:
- `sg va` → `https://<ip-or-hostname>/` (working)
- `sg vp` → `https://<slug>.aws.sg-labs.app/` (working)
- `sg va fargate` → `http://<task-ip>:8080/` (working — but plain HTTP)

All three flows are otherwise smooth (timing breakdowns, auto-DNS, registry tags, waker proxy etc.). The Fargate flow specifically validated end-to-end with the vault UI rendering at `http://3.8.163.59:8080/en-gb/` — landing page, vault-creation form, encryption claims, all functional from a UX perspective. **But the encryption itself doesn't work over plain HTTP, which is the constraint that motivates this brief.**

---

# Cert provisioning — what we can do today

The cert-init container (`sg-host-control` image, runs on the EC2 boot) supports three TLS modes:

## 1. `letsencrypt-ip` mode

- Calls Let's Encrypt's ACME HTTP-01 challenge for the EC2's **public IP** (not a hostname)
- LE has issued IP certs since mid-2025 (general availability)
- Works for direct-to-EC2 access — `https://<ec2-ip>/` validates
- Cert auto-renews every 60-90 days while EC2 is up
- **Rate limit (separate from domain limit)**: certs per /24 block — roughly 5-10 per /24 per week (LE doesn't publish exact figure for IP certs)
- Use case: ephemeral vaults where the user is OK pasting a raw IP

## 2. `letsencrypt-hostname` mode

- Calls LE's ACME HTTP-01 against `<fqdn>` (e.g. `tls-test.aws.sg-labs.app`)
- Requires a per-FQDN Route 53 A record pointing at the EC2's public IP **before** cert-init runs (we have `Vault_App__Auto_DNS` for this)
- Cert is bound to the FQDN — survives EC2 IP changes (as long as the A record updates)
- Used by `sg vp register --with-tls` today
- **Rate limit (the problematic one)**: **50 certs per registered domain per week**
  - "Registered domain" = `sg-labs.app` (the eTLD+1) — NOT `aws.sg-labs.app`
  - So every subdomain under `sg-labs.app` (including `aws.sg-labs.app`, future `sg-vault.app`, etc.) shares the same 50/week bucket
  - Window is rolling 168 hours; oldest cert ages out
  - Going over: 7-day backoff before you can issue another
- Use case: per-slug HTTPS that users can bookmark

## 3. `self-signed` mode

- Generates a self-signed cert in cert-init
- Browser shows scary warnings; user has to click through
- Works for dev / closed-network use, not production
- **No rate limit** (offline operation)

Plus, separately:

## 4. ACM cert (used by CloudFront only, today)

- AWS-managed cert, DNS-validated via Route 53
- Wildcard supported (`*.aws.sg-labs.app`) — one cert covers all subdomains
- **No public rate limit** (ACM has internal limits but generous)
- **Cannot be exported as a private key file** — ACM only exposes the cert ARN, not the .pem
- Only usable on AWS-managed TLS terminators:
  - CloudFront (the `sg vp` slug routing uses this)
  - ALB / NLB
  - API Gateway
  - Nitro Enclaves (via a special grant)
- **Cannot** be installed directly on an EC2 instance or a Fargate task

---

# Why we need certs — the WebCrypto constraint

Vault encrypts files in the browser using AES-256-GCM via `window.crypto.subtle` (the Web Crypto API). Per the spec, `crypto.subtle` is **only available in a "secure context"**:

- **HTTPS pages** (any cert that the browser accepts)
- **`http://localhost`** (special browser exemption for development)
- **`http://127.0.0.1`** (same exemption)

Plain HTTP on a public IP — like `http://3.8.163.59:8080/` (the Fargate task right now) — gets `window.crypto.subtle === undefined`. Vault's encryption code can't run. The user sees the UI, clicks "create vault", and gets a runtime error.

This is enforced by every modern browser. There is no flag for users to override it for arbitrary origins (only `localhost` and explicit per-origin trust via `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, but that's a per-user dev flag, not a deployable solution).

Bottom line: **every vault URL a real user might open must be HTTPS**. Plain-HTTP vault is fundamentally non-functional for the encryption use case.

---

# The Let's Encrypt 50/week problem

50 certs per registered domain per week sounds generous in absolute terms, but at our actual usage rate it bites quickly:

- During the v0.1.14 → v0.1.16 work above I personally issued ~15 test certs against `aws.sg-labs.app` over 4 days (`tls-test-1` through `tls-test-12`, plus a few `clever-hopper` / `brave-curie` style names)
- A single demo session with a customer might burn 5-10 certs as we walk through the flows
- If we open self-serve provisioning to ~5 customers, each running 2-3 trial vaults, we're at the wall

The 7-day backoff is brutal in practice — you lose a day of dev work to wait it out. You can apply for a higher rate limit via LE's form, but they take weeks to respond and it's a manual review.

This is the constraint that means we can't just keep using `letsencrypt-hostname` for new vault provisioning. We need a strategy that doesn't burn one LE cert per vault.

---

# Options space — what to explore in the Claude-Web thread

I'll sketch the option set with rough tradeoffs. None of these are decided; the goal of the thread is to pick one (or a combination).

## A. ALB + ACM wildcard (probably the right call for Fargate)

- Provision an Application Load Balancer with `*.fargate.aws.sg-labs.app` or `*.vault.sg-labs.app` ACM wildcard cert
- Fargate tasks register as ALB targets (target group per task or path-based routing)
- Each new vault: register target, point its DNS at the ALB
- **No LE involvement at all** — ACM has no rate limit
- ~$20/month for the ALB + per-LCU usage; modest

Tradeoffs:
- One ACM wildcard cert covers infinite slugs
- ALB latency overhead is ~5-10ms (negligible)
- ALB is the ONE place where ACM certs work cleanly with non-CloudFront origins
- Need a target-group-per-slug or shared target-group with path-based routing
- DNS pinning concern (the same H2 coalescing problem we just solved for vault-publish) — but ALB has different IPs per zone, similar to the CloudFront pattern

## B. CloudFront in front of Fargate (mirrors sg vp's pattern)

- CloudFront wildcard `*.fargate.aws.sg-labs.app` → Fargate task public IP as origin
- Same model as `sg vp` (slug routing via Lambda), just with Fargate at the back instead of EC2 wake-on-access
- Or: CloudFront → Lambda → Fargate (admin-Lambda dispatcher)

Tradeoffs:
- CloudFront is HTTPS-by-default with the ACM cert
- No LE involvement
- Adds ~50-150ms of latency vs direct
- Adds CloudFront cost per request

## C. Pre-issued LE cert pool + slot assignment

- Pre-issue 50 LE certs for `slot-1.aws.sg-labs.app`, `slot-2.aws.sg-labs.app`, ..., `slot-50.aws.sg-labs.app`
- When a user creates a vault, assign them the next free slot
- The slug they pick (`my-cool-vault`) becomes a DNS alias to `slot-N.aws.sg-labs.app` (or just renders on a per-slot URL)
- Recycle slots when vaults terminate

Tradeoffs:
- Keeps the LE-hostname model that already works
- Burns one LE cert per slot, but slots are reusable (50 active vaults, but unlimited lifetime user vaults if they don't run concurrently)
- Complex DNS choreography
- 50 active concurrent vaults is the cap — might be too low for prod

## D. Alternative CAs (less rate-limited than LE)

- **ZeroSSL** (90-day certs, no documented per-domain rate limit — undocumented but apparently much higher)
- **Buypass** (180-day certs, separate quota)
- **Google Trust Services** (free, has its own limits)
- Same ACME protocol → drop-in replacement in cert-init
- Run multiple CAs in fallback mode (LE first, fall back to ZeroSSL when rate-limited)

Tradeoffs:
- Quick win: change one URL in cert-init, done
- Less battle-tested than LE
- Different CAs have different trust roots — usually fine, but some edge cases

## E. Different LE accounts / parent zones to multiply the limit

- `sg-labs.app` (current) — 50/week
- `sg-vault.app` (we own it) — separate 50/week
- `sg-compute.sgraph.ai` (we own it) — separate 50/week
- Multiple zones add operational complexity but legitimately triple the available rate

Tradeoffs:
- Operationally messy
- Doesn't fundamentally solve the scaling problem at production scale
- Each new domain needs its own ACM cert / CloudFront setup

## F. Hybrid — ACM/ALB for prod, LE-hostname for testing

- Production vaults go behind ALB + ACM wildcard (option A)
- Test vaults use LE-staging environment (no rate limit, browsers reject the cert)
- Devs add the LE-staging root to their machine
- 50/week prod quota is plenty if individual customers run only a handful of vaults

Tradeoffs:
- Two cert flows to maintain
- Test environment doesn't match prod

## G. WebCrypto polyfill on plain HTTP (NOT viable)

Just noting for completeness: there are JS-only AES-GCM libraries (e.g. tweetnacl, asmcrypto.js) that don't depend on `crypto.subtle`. Vault could fall back to those over plain HTTP. **But**:
- Performance: 50-100× slower than native crypto.subtle
- Doesn't have the same key-storage primitives (no non-extractable keys, etc.)
- Audit / security posture: the polyfills are smaller, less reviewed
- Doesn't match the "your browser does the crypto natively" marketing message

I'd rule this out as a path.

---

# What I want from the Claude-Web thread

Concrete asks for the conversation:

1. **Validate or refute option A** — ALB + ACM wildcard for Fargate. This feels like the obvious AWS-native answer. What's the catch? Cost analysis at 100 / 1k / 10k concurrent vaults?

2. **For sg vp (existing slug routing) — should we move off LE-hostname?** The current model (per-slug LE cert) hits the 50/week wall fast. CloudFront already fronts every slug — the per-slug LE cert is only useful for the direct-routing optimization after DNS propagates. If we accept always-via-CloudFront (slight latency penalty), we never need per-slug LE certs again. Is that worth doing?

3. **What's the right answer for the "many concurrent vaults" production scenario?** Customer self-serve creates N vaults. N grows. We can't pre-issue 1k LE certs. Options A, B, C, D all have different scaling properties — which scales cleanest to 10k concurrent vaults?

4. **Multi-tenancy concerns** — if many users share an ALB / CloudFront / Lambda, what does the security boundary look like? Today each vault has its own EC2 / Fargate task with its own keys. Putting them all behind a shared TLS terminator doesn't reduce that, but worth thinking through.

5. **What about IP cert mode** (option not listed above but worth raising) — LE has IP certs now. Can we just give every vault an HTTPS-on-IP cert and skip DNS entirely? Rate limits on IP certs aren't well documented. Worth investigating.

---

# Repo references (for the Claude-Web thread if it wants to pull code)

Branch: `claude/waker-debug-clean-bRIbm` (the v0.1.16 admin-split work).

Key files:
- `sg_compute_specs/vault_app/service/Vault_App__Service.py` — `create_stack` flow (TLS mode dispatch)
- `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py` — bakes the cert-init env into EC2 user-data
- `sg_compute_specs/vault_publish/service/Vault_Publish__Service.py` — slug registration that calls `create_stack` with `tls_mode=letsencrypt-hostname`
- `sg_compute_specs/vault_app/fargate/service/Vault_App__Fargate__Setup.py` — Fargate cluster + task-def (NO TLS layer today — this is the gap)
- `team/comms/plans/v0.1.16__admin-lambda-split/README.md` — the admin Lambda separation work; sets up patterns for future cert-related Lambda work
- `library/docs/research/v0.1.14__http2-connection-coalescing.md` — the cert constraint research (relevant if we go ALB or CloudFront route)

---

# Summary for the thread starter

> We have three command surfaces (`sg va`, `sg vp`, `sg va fargate`) that can spin up an isolated browser-vault in 30s-2min. The first two have TLS via Let's Encrypt cert-init; the third has no TLS yet. WebCrypto requires HTTPS, so the third is non-functional for actual encryption. We were about to wire LE-hostname into Fargate too, but LE's 50-cert-per-week-per-eTLD+1 limit means this doesn't scale.
>
> Options to evaluate: ALB + ACM wildcard (option A), CloudFront in front of Fargate (option B), pre-issued LE cert pool (option C), alternative ACME CAs (option D), multiple parent zones (option E), hybrid prod/test (option F). Rule out WebCrypto polyfills (option G).
>
> Goal of this thread: pick the path forward for cert provisioning that scales to ~10k concurrent vaults without hitting LE rate limits, and write the implementation plan.
