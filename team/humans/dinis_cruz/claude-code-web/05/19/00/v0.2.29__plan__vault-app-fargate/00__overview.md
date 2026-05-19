---
title: "`sg vault-app fargate` — plan overview"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
related:
  - sg_compute_specs/vault_publish/setup/cli/Cli__Setup.py
  - sg_compute_specs/vault_publish/setup/service/
  - sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py (wake command, lines 95–196)
  - sg_compute_specs/vault_app/cli/Cli__Vault_App.py
  - sgraph_ai_service_playwright__cli/aws/fargate/
documents:
  - 00__overview.md            — this file
  - 01__sg-aws-extensions.md   — what `sg aws *` needs added / extended first
  - 02__cli-design.md          — `sg vault-app fargate` command tree + flags + outputs
  - 03__orchestrator-design.md — Setup__Fargate__* + Start__Fargate orchestrator classes
  - 04__timing-instrumentation.md — Phase__Timer utility + live progress
  - 05__implementation-slices.md  — slice-by-slice ordering and dependencies
  - 06__open-questions.md      — decisions needed before coding
---

# `sg vault-app fargate` — Plan Overview

## North star

> Make `sg vault-app fargate start` produce a healthy, reachable vault on Fargate
> **as fast as physically possible** (target: under 30 s on a warm setup), while
> keeping `sg vault-app fargate setup` a clean, idempotent, fully checkable
> one-time provisioning step.

## The two-mode shape (matches `sg vp setup` / `sg vp wake`)

| Mode | Frequency | Latency budget | Reversible by |
|------|-----------|---------------:|---------------|
| **Setup** (cluster, IAM, log group, ECR repo, task definition, optional EFS/ALB) | Once per account/region/environment | Minutes (one-time) | `sg vault-app fargate teardown` |
| **Start** (run a task, wait for RUNNING, wait for `/info/health`, optional DNS upsert) | Every vault session | **< 30 s warm path** | `sg vault-app fargate stop` |

The cost of putting things in the wrong column is high: anything in the start
path that doesn't strictly need to happen per-session belongs in setup.

## What this is NOT

- Not a re-implementation of `sg aws fargate` — the new sub-app delegates
  almost everything to `sg aws fargate`, `sg aws iam`, `sg aws ecr`,
  `sg aws ec2`, `sg aws acm`, `sg aws dns`. It owns *only* the vault-specific
  workflow (image identity, env-var contract, port set, DNS naming, the
  start-fast / setup-slow split).
- Not a replacement for `sg vault-app create` (EC2 path) on day 1 — both live
  side-by-side. Fargate is opt-in.
- Not production-ready as a single command. The plan exposes everything as
  checkable phases so we can pause, inspect, retry, and eventually wrap them
  in a one-shot `setup all` / `start` pair.

## Architecture at a glance

```
                          sg vault-app fargate
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
      setup                       start                       teardown
        │                           │                           │
        ├─ check (read-only)        ├─ start (default)          ├─ delete-task
        ├─ status                   ├─ stop                     ├─ delete-task-def
        ├─ create-all               ├─ restart                  ├─ delete-cluster
        ├─ update-all               ├─ health                   ├─ delete-log-group
        ├─ ecr ……→ sg aws ecr       ├─ logs                     ├─ delete-iam-roles
        ├─ iam ……→ sg aws iam       ├─ url                      ├─ delete-ecr-repo
        ├─ logs ……→ aws/logs        └─ open                     └─ delete-all
        ├─ task-def …→ sg aws fargate task-def register
        ├─ efs ……→ aws/efs (NEW)
        └─ alb ……→ aws/elbv2 (NEW, optional)
```

Every leaf node is either (a) a wrapper around an existing `sg aws *`
command/client or (b) a clearly-scoped new sub-package under `aws/` that gets
its own checked-in surface, **not** a one-off helper inside vault-app.

Vault-specific knowledge lives only in:
- `Vault_App__Fargate__Spec` — vault image URI resolver, env-var contract,
  port set, default CPU/memory, default tag set
- `Vault_App__Fargate__Setup` — orchestrates the per-phase setup against the
  underlying `sg aws *` clients
- `Vault_App__Fargate__Starter` — orchestrates the fast start path

## Two distinct kinds of "fast"

We track two timings that the user cares about, and report them separately:

| Timing | Definition | Optimization levers |
|--------|------------|---------------------|
| **Task ready** | `t=0` (CLI invocation) → `RUNNING` from ECS | task-def warm image, Fargate platform version, ENI attach time, subnet placement |
| **Vault ready** | `t=0` → first 2xx from `/info/health` | container cold-start, vault boot, public IP propagation, DNS update if requested |

Both surface in the start-command output, both ship in the `--json` envelope,
both feed the historical timings table (see [04](./04__timing-instrumentation.md)).

## Why this is worth doing (and where it fits)

`sg vault-app create` (EC2) is 60–90 s of cloud-init *every* time. The Fargate
path puts everything build-able into setup-once and leaves only "RunTask →
attach ENI → boot container → first health check" in the per-session loop.
Real-world target: **5–15 s warm-image start**, scaling to a few seconds with
SOCI-indexed images or pre-pulled platform versions later.

Operating this as a per-customer per-session surface (the customer-facing
"give me a vault" path) is only credible if we measure these numbers and
expose them. The plan threads timing through every layer so the eventual
public-facing UX has real data behind it.

## Documents in this plan

1. [`01__sg-aws-extensions.md`](./01__sg-aws-extensions.md) — what blocks us:
   the four flags `sg aws fargate task-def register` needs (`--port-mapping`,
   `--execution-role-arn`, `--task-role-arn`, `--secret`), a `--launch-type`
   on `task run`, and the new sub-packages (`aws/logs` CLI, `aws/elbv2`,
   `aws/efs`, `aws/secrets`) — each scored P0 / P1 / P2 against the start-fast
   goal.
2. [`02__cli-design.md`](./02__cli-design.md) — the full `sg vault-app
   fargate` command tree: every command, every flag, the JSON envelope, the
   Rich table output, the `--time` flag for verbose timing.
3. [`03__orchestrator-design.md`](./03__orchestrator-design.md) — the
   `Vault_App__Fargate__Setup` and `Vault_App__Fargate__Starter` classes; the
   `Schema__VAF__*` report schemas; how check/create/update/delete map onto
   one set of phases.
4. [`04__timing-instrumentation.md`](./04__timing-instrumentation.md) —
   `Phase__Timer` utility, callback contract, live-progress Table, JSON
   timing envelope, optional CloudWatch metric publication.
5. [`05__implementation-slices.md`](./05__implementation-slices.md) — eight
   slices ordered by dependency, each commit-shaped, each shippable.
6. [`06__open-questions.md`](./06__open-questions.md) — decisions I need from
   you before slice 1: do we add ALB and EFS to P0, do we publish to
   CloudWatch metrics, do we want a `--profile` fast/slow toggle.

## Reading order

Read this file → [open-questions](./06__open-questions.md) → answer questions
→ read [extensions](./01__sg-aws-extensions.md) → read [cli-design](./02__cli-design.md). The
orchestrator and slice docs are reference material for implementation.
