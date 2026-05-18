---
title: "01 — Intent & motivation"
file: 01__intent.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 01 — Intent & motivation

## What's wrong today

`sg vault-publish bootstrap` is a single all-or-nothing operation. It:

1. Zips the waker Lambda and calls `deploy_from_folder`
2. Calls `create_function_url` unconditionally
3. Calls `create_distribution` on CloudFront unconditionally

On the second run — or even on the first run if any step partially
succeeded — AWS rejects the duplicate creates with
`ResourceConflictException` / `EntityAlreadyExists` / similar. The
operator has no recovery story other than to manually delete the
stale resources and retry.

This is the symptom. The deeper issue is that **bootstrap is the wrong
abstraction**. It conflates two distinct concerns:

- **Setup** — provisioning the durable infrastructure that backs every
  slug: ACM cert, CloudFront distribution, Lambda function, Function
  URL, IAM execution role, S3 layer bucket (if we go that route),
  Route 53 wildcard alias. These change rarely. They are slow to
  create. They cost money to keep around.
- **Runtime** — per-slug register / unpublish / start / stop. These
  touch Route 53 records and SSM Parameter Store, change frequently,
  and need to be fast and cheap.

Bootstrap lumps the slow / rare / expensive setup work into one verb
with no granularity, no idempotency, and no introspection.

## What good looks like

The operator should be able to:

```
sg vault-publish setup check
```

…and see a typed report of every resource in the target account/region:
what's present, what's missing, what's mis-configured, what would
change on a `setup * update`. They should be able to apply targeted
fixes one resource at a time, or run `bootstrap` to converge everything
in one shot. Either path should be **safe to run twice**.

## Why this matters now

We are about to start operating this in production. Today's
`ResourceConflictException` is the polite version of the failure mode.
The impolite versions are:

- **Stale CloudFront pointing at a deleted Lambda Function URL.** The
  distribution stays in service, slug requests start returning 502, the
  operator has no `check` to surface it.
- **IAM role with a policy that drifts from `Waker__Policy__Template`.**
  We just added `ssm:GetParameter`; how would the operator know whether
  the live role has it? Today: log into the console.
- **ACM cert renewed in a different region.** The wildcard cert lives
  in `us-east-1` (CloudFront requirement). If a new operator provisions
  the cert in `eu-west-2`, bootstrap silently passes the wrong ARN and
  every TLS handshake on the cold path fails. A `check` would catch
  this in seconds.

These failure modes are all "I forgot how the manual setup worked when
I first wired it up". The cure is to encode the setup contract in
typed, runnable code.

## Three design principles

### 1. Each AWS resource is a unit

Every resource we touch in setup gets the same five verbs:

```
create   — make it if it doesn't exist; no-op if it does
update   — apply config drift if any
delete   — remove it (with confirmation gate)
check    — read state, compare to expected, return typed report
status   — pretty-print current state for humans
```

No verb mutates without a confirmation gate (`SG_AWS__*__ALLOW_MUTATIONS`,
matching today's pattern).

### 2. Setup is composable, not monolithic

`bootstrap` becomes a thin orchestrator that calls each area's
`create` in the right order. There is no special "bootstrap-only"
logic — everything bootstrap does is also reachable as a single-area
verb. Operators who only need to update the IAM policy don't need
to re-run the whole pipeline.

### 3. Check before write

Every `create` / `update` calls `check` first. If the resource is in
the expected state, the verb is a no-op (with a clear "no changes" log
line). If drift is detected, `update` is the only verb that mutates.

This is the same pattern as Terraform's plan / apply, scaled down to
one resource at a time. We avoid Terraform's state-file complexity by
making AWS itself the source of truth — every `check` reads live AWS.

## What this is not

- **Not a replacement for `sg vault-app`.** Vault-app stays as the
  per-slug substrate. Setup is for the slug-spanning infrastructure.
- **Not Terraform.** No state file, no plan/apply. Each verb is direct.
  AWS is the truth.
- **Not a new spec.** Lives inside `sg_compute_specs/vault_publish/`
  under a new `setup/` sub-package.
- **Not addressing per-slug runtime drift.** That's already handled by
  `sg vault-publish register/unpublish/status` and is out of scope.

## What changes for the operator

Today:

```
sg vault-publish bootstrap            # all-or-nothing, breaks on second run
```

After:

```
sg vault-publish setup check                       # what's the state of the world?
sg vault-publish bootstrap                          # converge — safe to re-run
sg vault-publish setup lambda update                # just push new waker code
sg vault-publish setup iam update                   # just apply new policy
sg vault-publish setup teardown                     # remove everything (gated)
```

The `bootstrap` verb still exists and still works — it's the
"converge everything in the right order" verb. It's just now built
on top of idempotent per-area primitives, not on raw boto3 calls.
