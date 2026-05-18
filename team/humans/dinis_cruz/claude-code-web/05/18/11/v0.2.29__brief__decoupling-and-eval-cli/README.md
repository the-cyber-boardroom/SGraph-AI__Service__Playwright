---
title: "Brief — decoupling, reverse proxy & eval CLI (v0.2.29)"
file: README.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
version: v0.2.29
parent: ../../../README.md
---

# Brief — decoupling, reverse proxy & eval CLI

A follow-up to the v0.2.29 setup-architecture brief
([10/v0.2.29__brief__setup-architecture/](../../10/v0.2.29__brief__setup-architecture/))
and the v0.2.29 waker-internals brief
([10/v0.2.29__brief__waker-internals-ux-debug/](../../10/v0.2.29__brief__waker-internals-ux-debug/)).

This brief explores three intertwined questions raised after Phase A +
B1 (IAM area) landed:

1. **Is the "vault-publish" name a misnomer?** The waker doesn't know
   or care that the EC2 runs a vault-app. The slug → EC2 lifecycle is
   100 % independent of the workload inside. Should the sub-package
   be renamed? Should the EC2-lifecycle bits become a generic
   "ephemeral-EC2" service that vault-publish consumes?

2. **The Let's Encrypt catch-22.** A fresh slug needs a cert for
   `slug.zone`. Cert issuance via HTTP-01 requires LE to reach
   `slug.zone:80` and get the right challenge response. But the
   slug's IP isn't in DNS yet, so traffic for `slug.zone` lands on
   the wildcard CloudFront → Lambda waker — which has no idea how to
   answer the challenge. Two paths out (DNS-01 challenge, or
   Lambda-as-reverse-proxy); we should pick one explicitly.

3. **A reverse-proxy mode for the Lambda.** The waker today returns
   warming HTML when EC2 is starting. What if instead it *proxied*
   the request to the running EC2 the moment the IP is available,
   bypassing DNS propagation entirely? Same code path solves the
   cert challenge (route `/.well-known/acme-challenge/*` to EC2).
   Tempting — but it changes the waker from "front door + HTML
   page" into "front door + proxy", and there are real trade-offs.

4. **A step-by-step eval/qa CLI.** Mirror the setup-check pattern but
   for the *operational* lifecycle: create slug → wait for live →
   probe vault → tear down → confirm absent. Each step runnable in
   isolation; all steps chainable as one end-to-end flow with a
   progress bar.

## Files in this brief

| File                                                                        | Topic                                                  |
|-----------------------------------------------------------------------------|--------------------------------------------------------|
| [01__implementation-review.md](01__implementation-review.md)                | Review of Phase A + B1 (what landed today)             |
| [02__decoupling-vault-from-ec2.md](02__decoupling-vault-from-ec2.md)        | Separating slug-lifecycle from workload-inside-EC2     |
| [03__lets-encrypt-catch-22.md](03__lets-encrypt-catch-22.md)                | The cert-issuance bootstrap problem                    |
| [04__lambda-reverse-proxy.md](04__lambda-reverse-proxy.md)                  | Lambda as transparent proxy (option B for cert + more) |
| [05__eval-cli-step-by-step.md](05__eval-cli-step-by-step.md)                | The operational-lifecycle eval CLI                     |
| [06__decisions-and-tradeoffs.md](06__decisions-and-tradeoffs.md)            | Options matrix + recommendations                       |

## Quick summary of the recommendations

| Question                                            | Recommended option                                              | Confidence |
|-----------------------------------------------------|-----------------------------------------------------------------|------------|
| Rename `vault-publish` → `ephemeral-ec2`?           | **No.** Keep the name; extract a `Workload` seam internally     | high       |
| Lambda always returns warming HTML?                 | **No.** Default to *reverse-proxy when IP known*, HTML otherwise| medium     |
| Let's Encrypt approach                              | **HTTP-01 with Lambda reverse-proxy** (one mechanism, two uses) | medium     |
| `sg vault-publish eval` CLI                         | **Yes.** Mirror the `setup check` shape with step-x verbs       | high       |
| Decouple workload health probe from waker config    | **Yes.** Per-slug `health_probe_path` in SSM entry              | high       |

Read [06__decisions-and-tradeoffs.md](06__decisions-and-tradeoffs.md)
for the full reasoning behind these picks.
