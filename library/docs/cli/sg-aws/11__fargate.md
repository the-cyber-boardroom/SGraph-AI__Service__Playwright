---
title: "sg aws fargate — ECS Fargate cluster and task management"
file: 11__fargate.md
author: Dev (Claude)
date: 2026-05-17
status: CURRENT — implemented in v0.2.29 (Slice C)
---

# `sg aws fargate` — ECS Fargate cluster and task management

`sg aws fargate` exposes a Fargate-first ECS CLI for the `cluster`, `task-def`, and `task` lifecycles. All commands default to `FARGATE` launch type; `EC2` is explicitly out of scope in this slice.

---

## Mutation gate

```bash
export SG_AWS__FARGATE__ALLOW_MUTATIONS=1
```

Required for: `cluster create`, `cluster delete`, `task-def register`, `task run`, `task stop`.

Read-only verbs (`cluster list/describe`, `task-def list/show`, `task list/describe/logs`) never require the gate.

---

## cluster

### `cluster list`

```bash
sg aws fargate cluster list [--json]
```

Lists all ECS clusters in the account/region. Returns a Rich table (or JSON array with `--json`).

### `cluster describe`

```bash
sg aws fargate cluster describe <name> [--json]
```

Shows status, running-task count, pending-task count, and active-service count for one cluster.

### `cluster create`

```bash
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 \
  sg aws fargate cluster create <name> [--tag k=v ...] [--yes]
```

Creates an ECS cluster with:
- Capacity providers: `FARGATE` (weight 1, base 1) and `FARGATE_SPOT`
- Container Insights enabled
- `sg:managed=true` tag (plus any `--tag` pairs you supply)

### `cluster delete`

```bash
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 \
  sg aws fargate cluster delete <name> [--yes]
```

Refuses to delete if the cluster still has running tasks. Stop all tasks first.

---

## task-def

### `task-def list`

```bash
sg aws fargate task-def list [--family FAMILY] [--json]
```

Lists active task definitions. `--family` filters by family prefix.

### `task-def show`

```bash
sg aws fargate task-def show <family:revision> [--json]
```

Shows full details for a single task definition revision, e.g. `hello-world:3`.

### `task-def register`

```bash
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 \
  sg aws fargate task-def register \
    --name NAME \
    --image IMAGE_URI \
    --cpu 256 \
    --memory 512 \
    [--env K=V ...] \
    [--yes]
```

Registers a new Fargate task definition revision. Defaults: `--cpu 256`, `--memory 512`. Logging is configured to CloudWatch Logs at `/ecs/<name>` (awslogs driver).

---

## task

### `task list`

```bash
sg aws fargate task list [--cluster CLUSTER] [--family FAMILY] [--json]
```

Lists running tasks. Filter by cluster name and/or task family.

### `task describe`

```bash
sg aws fargate task describe <task-arn> [--cluster CLUSTER] [--json]
```

Shows full state of a task: status, desired status, start/stop times, and stop reason.

### `task run`

```bash
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 \
  sg aws fargate task run \
    --cluster CLUSTER \
    --task-def FAMILY:REVISION \
    [--count 1] \
    [--subnet subnet-XXXXXXXX ...] \
    [--sg sg-XXXXXXXX ...] \
    [--assign-public-ip] \
    [--yes]
```

Launches a FARGATE task. Defaults: 1 task, no public IP. Subnets and security groups must be supplied or configured as environment defaults.

> **Note:** Cost awareness — every running task bills until stopped. Use `task stop` promptly.

### `task stop`

```bash
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 \
  sg aws fargate task stop <task-arn> \
    [--cluster CLUSTER] \
    [--reason TEXT] \
    [--yes]
```

Stops a running task. `--reason` is forwarded to the ECS stop-task API.

### `task logs`

```bash
sg aws fargate task logs <task-arn> \
  [--cluster CLUSTER] \
  [--since 30m] \
  [--json]
```

Fetches CloudWatch Logs for a task from the `/ecs/<family>` log group. Supports `--since` durations like `30m`, `1h`, `2h`.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SG_AWS__FARGATE__ALLOW_MUTATIONS` | Set to `1` to allow mutating commands |

---

## What backs this

- Service: `sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py`
- CLI: `sgraph_ai_service_playwright__cli/aws/fargate/cli/Cli__Fargate.py`
- Logs: reuses `sgraph_ai_service_playwright__cli/aws/logs/service/Logs__AWS__Client.py`
- Schemas: `fargate/schemas/Schema__ECS__Cluster.py`, `Schema__ECS__Task.py`, `Schema__ECS__Task__Definition.py`
