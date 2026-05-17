---
title: "01 — Intent & principles"
file: 01__intent-and-principles.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 01 — Intent & principles

What we are trying to learn, and the rules the harness lives by.

---

## 1. The five questions the v2 brief assumes are answered

Reading the v2 brief end-to-end, **five claims about AWS behaviour** are load-bearing. The harness exists so each one stops being an assumption.

| # | The claim | Where in the v2 brief | What we don't actually know |
|---|-----------|-----------------------|------------------------------|
| Q1 | A more-specific Route 53 record beats the wildcard at every resolver | `01__intent §2`, the whole architecture | Is this *every* resolver? What about old DNS-over-HTTPS gateways, mobile carrier resolvers, captive-portal resolvers? How fast does the swap actually take to converge across the public-resolver set? |
| Q2 | After `upsert_record`, "INSYNC" is reached in ~30–90 s | `02 §3` (`AUTO_DNS__INSYNC_TIMEOUT_SEC = 120`) | What's the distribution? Median? 99th percentile? Does it depend on zone size, prior change-batch backlog, time of day? |
| Q3 | CloudFront falls through to the (single) origin when DNS resolves the wildcard | `01 §3.2` | What does CF actually do when the origin (Lambda Function URL) times out, errors, throttles, or returns 5xx? What's the retry behaviour? |
| Q4 | The Waker Lambda can serve a warming page in <200 ms cold-start | `01 §1` (operational property) | What is the *actual* cold-start distribution? With osbot-aws + osbot-utils added? With a Function URL invoking it (not API Gateway)? |
| Q5 | "Once the DNS swap happens, Lambda is in the data path for at most one TTL" | `01 §3.3` | Is that true *per resolver*, or per client? How long does Chrome cache DNS? Firefox? Curl with no override? Mobile Safari? |

Every experiment in the catalogue ([§3](03__experiment-catalogue.md)) maps back to one of these five questions (sometimes more than one).

---

## 2. Seven principles

These govern every decision about what goes in the harness and what doesn't.

### P1 — Measurement before code

The harness exists to *replace assumptions with timings*. Every experiment produces numbers. "It works" is not a result; "it returned in 84 ms ± 12 ms over 50 runs" is.

### P2 — Tiny units, big claims

Each experiment tests **the smallest meaningful unit**. A composite claim ("the wildcard fall-through works") is the *combination* of small experiments, not a single big one. This is why [§2](02__component-decomposition.md) has ~22 components for 5 claims.

### P3 — Cleanup is enforced, not requested

No experiment can leak. The harness refuses to run if the ledger from the previous run isn't empty (or if `--force-cleanup` flushes it). The teardown order is hard-coded, not opportunistic. See [§4](04__safety-and-cleanup.md).

### P4 — Reuse existing primitives

We already have `Route53__AWS__Client`, `Dig__Runner`, `Route53__Authoritative__Checker`, `Route53__Public_Resolver__Checker`, `Route53__Smart_Verify`. The harness wraps these — it does **not** re-implement them. New code is the experiments, the ledger, the timing utilities, and the renderers.

### P5 — Type_Safe + osbot-utils + no boto3 outside the existing boundaries

The harness obeys the same boundary rules as everything else: schemas are `Type_Safe`, no Pydantic, no Literals, no raw primitives. The CloudFront and Lambda surfaces (when they need to mutate) use `osbot-aws` where available; where it isn't, they extend the existing `Route53__AWS__Client`-style narrow exception, **but routed through new client classes that live in `sg aws cf` / `sg aws lambda`** when those land. Before then, the harness uses temporary boto3 wrappers (`Lab__CloudFront__Client__Temp`, `Lab__Lambda__Client__Temp`) that get **deleted** once the proper primitives ship.

### P6 — No experiment is "global"

Every experiment is scoped to a unique run-id (UTC timestamp + 6-char nonce). Resources carry the run-id in their tags / name / caller-reference. Two operators running experiments in the same account see each other's resources but never collide.

### P7 — Read-only by default

Experiments split into two clear classes:

- **read-only experiments** — no mutations, no cleanup needed, no gate. e.g. "measure dig latency to 8 public resolvers", "show Route 53 NS for a zone", "ask CloudFront the TTL of the wildcard SOA". Safe in any environment.
- **mutating experiments** — gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1`. Use the ledger. Create + destroy resources. Cost a few cents per run.

Most of the value lands with read-only experiments. Mutating experiments are reserved for behaviour that can only be observed by causing the behaviour.

---

## 3. The two questions that drive the design

**Q-A: How do you measure a propagation that happens partly outside your control?**

Route 53 propagation involves: AWS's internal change-batch machinery → 4 authoritative NS → public recursive resolvers (each with their own caching policy) → end-user devices. We can only directly observe two of these layers (AWS API + dig from our host). The harness mitigates by:

1. measuring authoritative NS visibility directly via `dig +norecurse @<ns>`,
2. measuring 6–8 public resolvers in parallel,
3. tagging every dig with a per-experiment unique value (so cache-pollution from other operators is filtered out),
4. recording every observation in a typed timeline.

We cannot measure my mobile phone's resolver. The harness is honest about that — the "client-side TTL" experiment ([§3 E18](03__experiment-catalogue.md#e18--client-side-ttl-distribution)) is explicitly an *informed best-effort*: it runs from the harness host + the GitHub Actions runner + the Lambda itself, three different network positions. Better than nothing; not exhaustive.

**Q-B: How do you make destructive experiments safe?**

By making destruction the default for every resource the harness creates. Resources are created with **short, observable TTLs in tags** (e.g. `sg:lab:expires-at=2026-05-16T15:30:00Z`). The leak sweeper deletes anything past its expiry. This means even a corrupt ledger or a hard kernel kill on the test host won't leak — the next session's `sg aws lab sweep` finds and removes the strays.

---

## 4. Out of scope of this brief

To keep the harness focused and small:

- **No multi-region experiments.** Single region (`eu-west-2` for everything except the ACM cert in `us-east-1`).
- **No multi-account experiments.** Single AWS account.
- **No IPv6.** Same wildcard / specific-record logic applies; we measure v4 only.
- **No production traffic injection.** Real users never see lab resources.
- **No fault injection.** We don't simulate "what if Route 53 is degraded" — we measure the steady state.
- **No load testing.** Single requests, repeated. Not concurrent thousands.
- **No long-running experiments.** Every experiment finishes within ~5 minutes worst case (a single CF distribution create is the longest single step, and even that is a one-off).
