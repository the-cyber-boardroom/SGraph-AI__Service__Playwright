---
title: "README — Setup architecture for vault-publish"
file: README.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: ../../../README.md
---

# v0.2.29 — Setup architecture for vault-publish

A briefing pack that takes a step back from the `sg vault-publish bootstrap`
one-shot and reframes it as a **setup capability** with idempotent,
per-resource verbs and a unified `check` that verifies the target AWS
account/region is correctly provisioned.

Motivating event: today's bootstrap blew up on `ResourceConflictException`
because the Lambda Function URL already existed from a prior partial run.
The fix isn't just a try/except — it's recognising that **setup is not
the same kind of operation as the runtime path**, and giving it its own
verbs and checks.

## Reading order

| # | File | What it covers |
|---|------|----------------|
| 01 | [`01__intent.md`](01__intent.md) | Why we split setup from runtime, and the cost of getting it wrong |
| 02 | [`02__bootstrap-error-and-immediate-fix.md`](02__bootstrap-error-and-immediate-fix.md) | The specific `ResourceConflictException` — root cause, narrow fix, and why the narrow fix is not enough |
| 03 | [`03__setup-vs-runtime.md`](03__setup-vs-runtime.md) | The conceptual split: which resources are set up once vs. touched every operation |
| 04 | [`04__per-area-capabilities.md`](04__per-area-capabilities.md) | ACM, CloudFront, Lambda, Function URL, IAM, S3 — each gets create / update / delete / check / status |
| 05 | [`05__check-architecture.md`](05__check-architecture.md) | `sg vault-publish setup check` — runs every area's check, returns a single typed report |
| 06 | [`06__implementation-phases.md`](06__implementation-phases.md) | How to land this incrementally without breaking the existing bootstrap users |

## TL;DR

```
sg vault-publish setup check                  # report state of every resource
sg vault-publish setup acm   {create,update,delete,check,status}
sg vault-publish setup cf    {create,update,delete,check,status}
sg vault-publish setup lambda {create,update,delete,check,status}
sg vault-publish setup url   {create,update,delete,check,status}
sg vault-publish setup iam   {create,update,delete,check,status}
sg vault-publish setup s3    {create,update,delete,check,status}     # optional, only if we adopt layer-via-S3

sg vault-publish bootstrap                    # composes setup * create (idempotent)
sg vault-publish teardown                     # composes setup * delete (in reverse order)
```

Every verb is idempotent. Running `bootstrap` twice is a no-op the second
time. Every `create` checks first and updates or skips as appropriate.
`check` never mutates.
