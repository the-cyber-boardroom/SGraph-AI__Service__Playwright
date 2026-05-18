---
title: "README — Waker internals, UX, and debugging"
file: README.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: ../../../README.md
---

# v0.2.29 — Waker internals, UX, and debugging

What happens inside the waker Lambda from the moment a request hits
the Function URL until the response leaves; what each step looks like
to the end-user (the person who typed `https://sara-cv.aws.sg-labs.app`
into their browser); and what debug surface the CLI and Lambda should
expose so operators can diagnose problems without SSH-ing into anything.

Motivating moment: today the live Lambda came up clean (returned the
404 HTML for an unmatched Host header — correct behaviour). But the
moment something goes wrong, we have almost no visibility:
- The 404 page doesn't tell us which Host the Lambda actually saw.
- The CLI has no `sg vp waker invoke --host sara-cv.aws.sg-labs.app`.
- There's no `sg vp tail` to stream the Lambda logs.
- The warming page doesn't say "I just called EC2 start; here's the
  instance ID; check back in 30 s".

This brief catalogues every state the request can enter, what the
user sees, what the operator should be able to see, and how to wire
the missing pieces.

## Reading order

| # | File | What it covers |
|---|------|----------------|
| 01 | [`01__request-lifecycle.md`](01__request-lifecycle.md) | What happens inside the Lambda, step by step, with the state machine and every code path |
| 02 | [`02__ux-by-state.md`](02__ux-by-state.md) | What the end-user sees at each state — 404, warming, healthy proxy, error — with mockups and copy |
| 03 | [`03__debug-surface.md`](03__debug-surface.md) | What debug info the Lambda should expose and how operators consume it (response headers, debug endpoints, structured logs) |
| 04 | [`04__cli-debug-commands.md`](04__cli-debug-commands.md) | New `sg vp waker {invoke,tail,inspect,trace}` and existing `sg aws lambda logs` patterns |
| 05 | [`05__local-replay.md`](05__local-replay.md) | Running the waker locally with seeded SSM + EC2 fakes for end-to-end debugging without AWS |

## TL;DR — what's missing today

```
Today                                       Proposed
─────                                       ────────

User sees "404 — Slug not found"            Page says the Host header that the Lambda saw
  (no idea what Host was sent)              + list of registered slugs (if --debug header set)

User sees "Vault is warming up"             Page shows: instance-id, state-before-start,
  (no idea what's happening backstage)      seconds since start, current EC2 state

Operator: tails CloudWatch via console      sg vp waker tail
Operator: invokes manually via console      sg vp waker invoke --host sara-cv.aws.sg-labs.app
Operator: introspects state via boto3       sg vp waker inspect <slug>
Operator: tests cold path locally           python -m sg_compute_specs.vault_publish.waker.lambda_entry
                                            + sg vp waker fake-event --slug sara-cv | jq
```

## The three layers of debug surface

1. **Per-response headers** — `X-Waker-State`, `X-Waker-Slug`,
   `X-Waker-Instance-Id`, `X-Waker-Elapsed-Ms`. Always on. No
   sensitive info. Lets curl/devtools tell you exactly what happened.

2. **Structured logs** — every request emits a single JSON log line
   with `slug, host, state, action, instance_id, elapsed_ms, source_ip`.
   CloudWatch Insights queries become one-liners.

3. **CLI debug verbs** — `sg vp waker {invoke,tail,inspect,trace,replay}`
   for operator workflows. No AWS console required.

Each layer is independently shippable. Per-response headers first
(zero infrastructure cost), structured logs second, CLI verbs third.
