---
title: "`sg aws *` extensions needed before `sg vault-app fargate` can ship"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# `sg aws *` extensions needed first

The rule from `00__overview.md`: vault-app's Fargate sub-app delegates to
existing `sg aws *` commands. That rule only holds if those commands can
actually express what the vault needs. This doc lists every gap.

Each item is scored:
- **P0** — blocks `sg vault-app fargate setup all` even working
- **P1** — blocks parity with `sg vault-app create` UX
- **P2** — nice-to-have / production-readiness

## A. `sg aws fargate` extensions (in-place changes to the existing package)

### A1. `task-def register --port-mapping` (P0)

Current state: `Fargate__AWS__Client.register_task_definition`
(`sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py:134`)
never sets `containerDefinitions[0].portMappings`. Without it the container
listens but nothing can reach it — ENI, ALB, or otherwise.

Add:

```
sg aws fargate task-def register ... --port-mapping 8080/tcp [--port-mapping 443/tcp]
```

Flag is repeatable. Value parses as `<containerPort>/<protocol>` with `tcp`
default. Optional `:<hostPort>` suffix for awsvpc-mode parity (but in awsvpc
mode hostPort==containerPort always — validate and reject any mismatch).

Schema addition: `Schema__ECS__Port_Mapping` (container_port, protocol).
Carry on `Schema__ECS__Task__Definition` so `task-def show --json` reports it.

### A2. `task-def register --execution-role-arn` (P0)

Current state: hard-coded to `''` at line 144. Without it Fargate cannot pull
from ECR or write to CloudWatch Logs.

Add: `--execution-role-arn arn:aws:iam::...` (required when image is from ECR
— the CLI can validate by inspecting the image URI). Default to the
convention name `ecsTaskExecutionRole` resolved via `sg aws iam role show`
(if it exists in this account).

### A3. `task-def register --task-role-arn` (P1, optional)

Current state: not threaded through. Useful when the container needs to
assume an AWS role (e.g. for CloudWatch metric publication, S3 reads —
case-by-case). NOT used by the vault for persistence (peer-vault path)
nor for secrets (peer-vault path). Optional flag, kept for future
use-cases that genuinely need an AWS-side identity.

### A4. ~~`task-def register --secret name=arn`~~ **DROPPED**

Per user decision: we will not use AWS Secrets Manager at all. The
eventual plan is to host secrets in one of our own vaults, fetched at
container start. Access tokens stay in `--env` until the in-vault fetch
path lands. There is no AWS Secrets Manager integration in this plan.

### ~~A5. `task-def register --efs-volume`~~ **DROPPED**

Per user decision: all data persistence will use peer SG vaults, not
EFS. Fargate tasks remain ephemeral (no `volumes`, no `mountPoints`,
no EBS). When state needs to survive a task stop, the container will
fetch from a peer vault at start and (optionally) push to it on
shutdown — outside the scope of this plan.

### A6. `task-def register --log-group <name>` (P1)

Current state: log group is hard-coded to `/ecs/<family>` (line 154). We want
to optionally point at an existing group with a custom retention.

Add: `--log-group /ecs/vault-app` with default fallback to `/ecs/<name>`.

### A7. `task run --launch-type FARGATE|FARGATE_SPOT` (P0 for cost; P1 for hot path)

Current state: hard-coded `'FARGATE'` at line 217. Cluster already enables
FARGATE_SPOT in the capacity provider strategy.

Add: `--launch-type FARGATE_SPOT` flag — emits `capacityProviderStrategy`
instead of `launchType`. Vault dev stacks should default to SPOT for cost
parity with `sg vault-app --use-spot`.

### A8. `task run --tag k=v` (P1)

Current state: only `sg:managed=true` is added (line 222).

Add: repeatable `--tag` like `cluster create`. Vault uses `Stack=...`,
`TerminateAt=...`, `Owner=...` — same pattern as `sg vault-app`.

### A9. `task run --service-discovery <namespace>` (P2)

For ALB / Cloud Map flows. Skip for now.

### A10. New `service` sub-command (P2)

`sg aws fargate service create|update|delete|describe|list` for long-running
deployments. Vault dev stacks are one-off tasks; production might want
services. P2 — out of scope for the vault-app Fargate work but called out so
the sub-package contract is forward-compatible.

## B. New CLI surface on existing service-only packages

### B1. `sg aws logs` CLI (P0)

Current state: `sgraph_ai_service_playwright__cli/aws/logs/` has schemas
(`Schema__Logs__Event`, `Schema__Logs__Query__Result`) and service classes
(`Logs__Insights__Queries`) but **no `cli/Cli__Logs.py`**. We need:

```
sg aws logs groups list                                          [--json]
sg aws logs group create <name> [--retention 7]                  [SG_AWS__LOGS__ALLOW_MUTATIONS]
sg aws logs group delete <name>                                  [SG_AWS__LOGS__ALLOW_MUTATIONS]
sg aws logs group describe <name>                                [--json]
sg aws logs tail <group> [--stream <pat>] [--since 5m] [--follow]
```

`group create` is needed by `vault-app fargate setup` and by the existing
`task-def register` flow (gap A6). `tail` consolidates what `sg aws fargate
task logs` already does today (and what every other service-with-cloudwatch
needs).

Effort: medium (~ECR slice 1 scale).

### B2. `sg aws iam role-for-fargate` helper (P1)

`sg aws iam role create` already exists but creating the canonical execution
role for ECS is a 3-step recipe (create role with the ECS trust policy,
attach `AmazonECSTaskExecutionRolePolicy`, optionally attach extras). Wrap
this as a single command:

```
sg aws iam role-for-fargate create [--name ecsTaskExecutionRole]
                                   [--extra-policy arn:...]      [SG_AWS__IAM__ALLOW_MUTATIONS]
```

OR — keep it inside `vault-app fargate setup iam` and have it just call the
underlying `sg aws iam role create` + `sg aws iam policy attach` twice. **My
preference: the latter** — keeps vault-app composing primitives, doesn't
pollute `sg aws iam` with use-case-specific shortcuts.

## C. Brand-new sub-packages

These are bigger than the in-place changes above. Each is sized as "1 slice"
of the ECR-style effort (~10–20 production files + tests).

### ~~C1. `sg aws efs`~~ **DROPPED**

Per user decision: data persistence will use peer SG vaults, not EFS.
The `sg aws efs` sub-package proposal is removed from this plan
permanently. If we ever do need to manage EFS for an unrelated reason
in the future it'll be a fresh proposal, not a resurrection of this.

### ~~C2. `sg aws elbv2`~~ **DROPPED**

Per user decision: we may not need ALB at all — alternative ingress
patterns are being explored. The proposal is removed from this plan;
add it back as a fresh proposal if/when an ALB-shaped requirement
actually materialises. V1 + foreseeable future use the per-task public
IP + Route 53 A-record upsert pattern from `sg vault-app` today.

### ~~C3. `sg aws secrets`~~ **DROPPED**

Per user decision: we will not use AWS Secrets Manager at all. The
project will host secrets in its own vaults; building a wrapper around a
service we'll never use is dead work. No `sg aws secrets` sub-package
will be created.

## D. Cross-cutting: `sg aws ec2 eni` sub-app (P1)

`vault-app fargate start` needs to resolve `task.attachment.eniId →
public_ip`. That's `ec2.describe_network_interfaces`. We already have
`list_network_interfaces` inside `EC2__AWS__Client` (from slice 4) — it just
needs CLI exposure:

```
sg aws ec2 eni describe <eni-id>                                 [--json]
sg aws ec2 eni list [--sg <sg-id>] [--vpc <vpc-id>]              [--json]
```

Cheap — most of the work is already in the service class. **Bundle with
vault-app fargate slice 1**.

## Summary — what slice 0 (pre-work) needs to land

| Priority | Item | Scope |
|---|---|---|
| **P0** | A1 `--port-mapping` | 1 flag + schema field + tests |
| **P0** | A2 `--execution-role-arn` | 1 flag + tests |
| **P0** | A7 `--launch-type FARGATE_SPOT` | 1 flag + tests |
| **P0** | B1 `sg aws logs` CLI (groups + tail) | new sub-app, ECR-sized slice |
| **P0** | D `sg aws ec2 eni` CLI | thin wrapper, ~50 LOC + tests |
| **P1** | A3 `--task-role-arn` (optional, for non-vault AWS-identity needs) | 1 flag + tests |
| **P1** | A6 `--log-group` | 1 flag + tests |
| **P1** | A8 `task run --tag` | 1 flag + tests |
| ~~P1~~ | ~~A4 `--secret` + C3 `sg aws secrets`~~ | **DROPPED — peer vaults, not AWS Secrets Manager** |
| ~~P1~~ | ~~A5 `--efs-volume` + C1 `sg aws efs`~~ | **DROPPED — peer vaults, not EFS** |
| **P2** | A10 `sg aws fargate service` | new commands |
| ~~P2~~ | ~~C2 `sg aws elbv2`~~ | **DROPPED — alternative ingress patterns being explored** |

**P0 alone is ~3–4 slices of work.** That's the gate before any
`vault-app fargate setup all` invocation can succeed end-to-end. Everything
else can land incrementally after the first vault is running on Fargate.
