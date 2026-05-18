---
title: "06 — Decisions & trade-offs"
file: 06__decisions-and-tradeoffs.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 06 — Decisions & trade-offs

A one-page summary of the questions raised in this brief and the
recommended answers. Each row links to the file that argues the
case.

---

## Question 1 — Should we rename `vault-publish` → `ephemeral-ec2`?

| Option | Verdict   | Why                                                                            |
|--------|-----------|--------------------------------------------------------------------------------|
| A — Leave + document        | acceptable    | Zero churn. But name keeps promising vault-specific behaviour.         |
| B — Full rename + split     | wrong now     | Massive cost (Lambda rename, SSM migration). For a benefit we don't need yet. |
| **C — Keep name, decouple internally** | **recommended** | Cleanest tradeoff. No names change; code becomes workload-agnostic via per-slug SSM fields. |

**Decision:** Option C. See [02](02__decoupling-vault-from-ec2.md).
Add `port`, `health_path`, `warming_label` to
`Schema__Vault_Publish__Entry` with vault-shaped defaults. Strip the
hard-coded vault strings from the waker code.

**Reversible?** Yes — if a real second workload arrives, the
rename-to-`ephemeral-ec2` path is still open with no extra cost
beyond what it would have today.

---

## Question 2 — How do we solve the Let's Encrypt cert catch-22?

| Option | Verdict | Why |
|--------|---------|-----|
| 1 — HTTP-01 + Lambda reverse-proxy | **recommended** | Same mechanism solves several other UX issues. No new IAM surface on EC2. |
| 2 — DNS-01 via Route 53 from EC2   | viable but narrow | Cleaner for cert alone, but gives every vault EC2 the ability to write our zone. Doesn't help other use cases. |
| 3 — Central cert-issuer service    | over-engineered  | New component, key distribution, separate lifecycle. Not justified today. |

**Decision:** Option 1. See [03](03__lets-encrypt-catch-22.md).
Lambda forwards `/.well-known/acme-challenge/*` to the EC2
regardless of DNS state. Vault-app side keeps its existing certbot
flow.

**Open verification:** confirm port 80 on EC2 is up from boot, not
only after cert exists.

---

## Question 3 — Should the Lambda do general reverse-proxy?

| Mode      | When                                                | Default? |
|-----------|------------------------------------------------------|---------|
| `NEVER`   | warming HTML even when EC2 is RUNNING                | opt-in for WebSocket / streaming workloads |
| `AUTO`    | proxy when EC2 RUNNING + port reachable; warming HTML otherwise | **default** |
| `ALWAYS`  | proxy every request, never serve warming HTML        | opt-in for debug / staging |

**Decision:** AUTO as default; per-slug `proxy_mode` field for
opt-in/out. See [04](04__lambda-reverse-proxy.md).

**Why AUTO over today's "warming HTML until full health":**
shrinks the warming window from "EC2 boot + workload boot + DNS
propagation" to just "EC2 boot + port reachable" — often a few
seconds. User sees the vault UI sooner.

**Trade-off accepted:**
- Slightly more Lambda invocations (small)
- 6 MB response cap inherited (vault-app pages well under)
- WebSocket / SSE workloads need `proxy_mode: NEVER` opt-out

---

## Question 4 — Should we build the eval / step-by-step CLI?

| Verdict | Why                                                                                                 |
|---------|-----------------------------------------------------------------------------------------------------|
| **Yes** | It's the post-deploy smoke test, the demo script, the CI integration test, AND the field debug tool. Four uses from one build. |

**Decision:** Yes. See [05](05__eval-cli-step-by-step.md).

**Naming:** `sg vault-publish eval` (not `test`, not `qa`).

**Shape:** 11 steps, one per file. Each step runnable in isolation
(`step-N-{action}`) or chained via `eval run`.

---

## Question 5 — Where should per-slug config live?

| Option                       | Verdict   |
|------------------------------|-----------|
| SSM Parameter Store (today)  | **keep**  |
| DynamoDB                     | no — adds dep, no win |
| CloudFront distribution config | no — operator can't set per-slug knobs |
| Lambda env vars              | no — global, not per-slug |

**Decision:** stay with SSM. Extend the entry schema with the new
fields. SSM's `describe_parameters` already lets us iterate, and
the `Slug__Registry` boundary doesn't change.

---

## What lands when

| Phase | Work | When |
|-------|------|------|
| **Phase A++** | Implementation-review fixes (statement-level drift, trust policy, _find_inline_policy parameter, status schema, missing tests) | Before Phase B2 |
| **Phase B2**  | Setup areas: Lambda + Function URL (from setup-architecture brief) | Next |
| **Decoupling**| Add port / health_path / warming_label to entry. Make waker use them. | Parallel with B2 |
| **Reverse-proxy** | ACME path forwarding + AUTO mode + port-reachable probe | Right after decoupling |
| **Eval CLI** | Step skeleton + first 4 steps (register → wait-for-ec2). Rest follow. | Parallel with reverse-proxy |
| **Phase B3**  | Setup areas: CF + ACM + DNS | After B2 |
| **Phase B4**  | Setup aggregator + bootstrap rewrite + teardown | Last setup phase |

Roughly speaking:

```
  Today:        Phase A + B1 ✓
  Next 0.5d:    Implementation-review fixes
  Next 2d:      Phase B2 (Lambda + URL setup)
  Next 2d:      Decoupling fields + reverse-proxy mode
  Next 2d:      Eval CLI v1 (steps 1–6)
  Next 2.5d:    Phase B3 (CF + ACM + DNS setup)
  Next 1d:      Phase B4 (aggregator + bootstrap rewrite)
  Next 1d:      Eval CLI v2 (steps 7–11)
                + reality doc update + debrief
```

About 11 days of work. Many of the rows are parallelisable across
two Devs (decoupling + B2 don't conflict; eval steps + setup areas
don't conflict).

---

## Things we explicitly DON'T do

- **Rename the Lambda function.** Operationally painful, no benefit
  beyond cosmetics.
- **DNS-01 cert challenge.** Doesn't generalize beyond cert; gives
  EC2 too much DNS-write power.
- **WebSocket support via Lambda proxy.** Out of scope until a
  workload needs it. AUTO + opt-out covers it.
- **Plan / apply / state-file model (Terraform-style).** AWS is the
  state. Each setup verb reads-then-writes; no shadow state to keep
  consistent.
- **Multi-account / multi-region orchestration.** One target at a
  time. Operator's responsibility to point creds at the right
  account.
- **Per-step retry logic in eval.** Each step has a single timeout.
  Eval is a diagnostic tool — if a step fails, the operator wants
  to see exactly where, not have it papered over by retries.

---

## Cross-references

- v0.2.29 setup architecture brief →
  [10/v0.2.29__brief__setup-architecture/](../../10/v0.2.29__brief__setup-architecture/)
- v0.2.29 waker internals + UX + debug brief →
  [10/v0.2.29__brief__waker-internals-ux-debug/](../../10/v0.2.29__brief__waker-internals-ux-debug/)
- This brief →
  [11/v0.2.29__brief__decoupling-and-eval-cli/](.)

The three together describe a coherent v0.2.29 → v0.3.0 trajectory
for vault-publish:

1. **Static infrastructure** (setup) — well-defined, idempotent,
   drift-detectable, teardownable.
2. **Runtime behaviour** (waker + UX + debug) — observable,
   debuggable, predictable across states.
3. **Operational lifecycle** (eval + decoupling + reverse-proxy) —
   testable end-to-end, workload-agnostic, robust to DNS races and
   cert dances.
