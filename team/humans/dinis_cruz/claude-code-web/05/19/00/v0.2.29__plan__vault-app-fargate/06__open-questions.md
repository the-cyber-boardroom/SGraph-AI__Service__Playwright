---
title: "`sg vault-app fargate` — open questions"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# Open questions

Decisions I need from you before slice 0a kicks off. Each is small enough
to answer in one line; I've picked a recommended answer for each so you can
just say "all defaults" if you want.

## Q1 — Scope of V1: do we include EFS + Secrets Manager?

- **A.** V1 ships with `--env` access-token (plaintext in task-def) and
  ephemeral storage. EFS + Secrets Manager land in slice 8 once V1 has real
  users. **(recommended — fastest path to a working vault on Fargate)**
- **B.** V1 includes EFS + Secrets Manager. Adds ~4 days, two more
  pre-work sub-packages.
- **C.** V1 includes Secrets Manager but not EFS.

## Q2 — Mutation gate model

- **A.** One env var `SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1`. The CLI
  programmatically sets the underlying `SG_AWS__*__ALLOW_MUTATIONS` for the
  scope of the command. **(recommended — best UX)**
- **B.** User must set every underlying gate (`SG_AWS__FARGATE__`,
  `SG_AWS__IAM__`, `SG_AWS__LOGS__`, `SG_AWS__ECR__`,
  `SG_AWS__EC2__`) before running setup. Safer but annoying.
- **C.** Single gate, but it doesn't unlock the underlying ones — instead
  the setup orchestrator bypasses the gates by passing the in-memory
  client directly (no shell env-var dance). Cleaner; requires a small
  refactor in each AWS client.

## Q3 — Where does the config file live?

- **A.** `$HOME/.config/sg/vault-app-fargate.json`. Per-user, follows XDG
  conventions. **(recommended)**
- **B.** Repo-local at `./.sg/vault-app-fargate.json`. Per-checkout,
  visible in git diffs (gitignored by default).
- **C.** Both: repo overrides user. (Adds complexity but is the standard
  pattern for tools like AWS CLI / kubectl.)

## Q4 — Slug naming + scoping

- **A.** Free-form slugs, no namespace. User picks. **(recommended for
  developer use)**
- **B.** Auto-prefixed with `$USER` or `git config user.email` to prevent
  collisions in shared accounts (e.g. `dinis-tue` becomes
  `dinis-cruz-dinis-tue`).
- **C.** Per-AWS-account UUID, never user-visible — surface a friendly name
  on top of it.

## Q5 — Image source: ECR mirror or Docker Hub?

- **A.** `setup create` requires a Docker Hub → ECR mirror (uses local
  `docker pull / push`). Once mirrored, all task definitions reference ECR.
  Latency-stable but requires a Docker daemon at setup time. **(recommended)**
- **B.** Reference Docker Hub directly (`diniscruz/sg-send-vault:latest`).
  Simpler but subject to Docker Hub rate limits and the unpredictable image
  pull latency that bypasses our SLA.
- **C.** Use Docker Hub but configure `repositoryCredentials` so pulls are
  authenticated (no rate limit). Requires Secrets Manager → bumps Q1
  scope up.

## Q6 — Default storage mode

`sg vault-app create` defaults to `--storage-mode memory` for fastest
spin-up. Should Fargate match?

- **A.** Yes, `memory`. **(recommended — fastest start, no persistence
  needed for short-lived dev sessions)**
- **B.** No, `disk` (ephemeral — lost on stop). Slightly slower but matches
  the EC2 default behaviour.
- **C.** Force user to specify (no default). Annoying.

## Q7 — Public IP or ALB-fronted?

V1 path:

- **A.** Per-start public IP on the task ENI, Route 53 A-record upsert. Same
  model as `sg vault-app` (the IP changes per start). **(recommended for
  dev; cheapest)**
- **B.** Pre-create an ALB during setup, register tasks as targets on start,
  ALB hostname is stable. Adds ALB to setup phases. ~$20/mo per env.
- **C.** Both, gated on a `--alb` flag in `setup create`.

If A, then v1 has no `sg aws elbv2` dependency at all (lift gap C2 from
the extensions doc).

## Q8 — Per-customer multi-tenant model

When this eventually faces customers (the eventual "give me a vault" SaaS
endpoint mentioned in the brief), how do we want slugs to map to AWS
resources?

- **A.** One AWS account, one cluster, many tasks (slug = task tag).
  **(recommended for v1; defer SaaS-shape to a later phase)**
- **B.** One AWS account, one cluster per tenant (slug = cluster name).
  More isolation, more overhead.
- **C.** One AWS account per tenant. Too aggressive for v1.

V1 should not foreclose any of these — but the config-file shape and the
CLI commands should be tenant-aware enough that we can switch later.

## Q9 — Should `start` block waiting for `/info/health`, or return early?

- **A.** Block by default; `--no-wait` to return as soon as task is
  RUNNING. **(recommended — matches `sg vault-app create --wait` default)**
- **B.** Return early by default; `--wait` to block until healthy. Faster
  CLI exit but the user has to follow up with `sg vault-app fargate
  health`.
- **C.** Block until either healthy OR a timeout, exit non-zero on
  timeout but still emit JSON output with the partial state.

## Q10 — Live progress in `--json` mode?

- **A.** No live rendering when `--json` is set — buffer everything, emit
  the JSON envelope at the end. **(recommended)**
- **B.** Stream per-phase JSON lines (JSONL) so a caller can react to
  in-flight phases. More work; only useful for interactive frontends.

## Q11 — CloudWatch metric publication in V1?

- **A.** No. Add as P2 follow-up. **(recommended — keeps V1 small)**
- **B.** Yes, behind a `--publish-metrics` flag (off by default).
- **C.** Yes, always-on (with an opt-out env var).

## Q12 — Backport `Phase__Timer` to `sg vp`?

Once `Phase__Timer` lands in slice 1, the existing `sg vp wake` and
`sg vp setup` will still use their bespoke `time.time()` calls.

- **A.** Leave them alone; backport when someone changes those files for
  another reason. **(recommended — don't break what works)**
- **B.** Backport as part of slice 7 (docs slice). Adds ~1 day.
- **C.** Backport before V1 ships so we have one timing pattern in the
  whole repo from day one.

---

## Recommended-defaults TL;DR

If you say "all defaults" the plan becomes:
- A1, A2, A3, A4 (memory mode), A5 (ECR mirror), A6 (memory default),
  A7 (public-IP + Route 53), A8 (one-cluster many-tasks), A9 (block by
  default), A10 (buffer JSON), A11 (no metrics), A12 (don't backport).
- 10 dev-days, ~8800 LOC, ~360 tests.
- One working `sg vault-app fargate setup all && sg vault-app fargate start`
  flow with EC2-parity feature surface minus the EBS-persistent storage.

If you want EFS + Secrets in V1 (Q1 → B) it's +4 days.
If you want ALB-fronted (Q7 → B) it's +3 days.
Both together: V1 ≈ 17 dev-days; matches a full milestone, not a single sprint.

## What I'd recommend you do next

1. Skim [`00__overview.md`](./00__overview.md) and [`02__cli-design.md`](./02__cli-design.md).
2. Answer this doc (even just "all defaults" works).
3. I'll write the first slice (0a — `sg aws fargate` flags) and we can
   evaluate against the real codebase before committing to the rest.

If the answer to anything is "I'm not sure yet, let's see when we get
there," call it out and I'll plan for both branches and we decide at the
relevant slice boundary.
