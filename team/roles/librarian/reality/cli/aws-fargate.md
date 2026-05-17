---
title: "Reality — sg aws fargate"
file: aws-fargate.md
domain: cli
author: Dev (Claude)
date: 2026-05-17
status: CURRENT — shipped in v0.2.29 (Slice C); updated v0.2.30 Open-2 (typed primitives)
---

# Reality — `sg aws fargate`

## Status

CURRENT. Implemented in v0.2.29 Slice C on branch `claude/aws-primitives-support-uNnZY`.

## What exists

### Production files

```
sgraph_ai_service_playwright__cli/aws/fargate/
├── cli/
│   └── Cli__Fargate.py              — Typer app with cluster / task-def / task sub-trees
├── service/
│   └── Fargate__AWS__Client.py      — boto3 ECS boundary (EXCEPTION noted in header)
├── schemas/
│   ├── Schema__ECS__Cluster.py
│   ├── Schema__ECS__Task.py
│   └── Schema__ECS__Task__Definition.py
├── collections/
│   ├── List__Schema__ECS__Cluster.py
│   ├── List__Schema__ECS__Task.py
│   └── List__Schema__ECS__Task__Definition.py
├── enums/
│   ├── Enum__ECS__Launch__Type.py   — FARGATE | EC2 | EXTERNAL
│   └── Enum__ECS__Task__Status.py   — PROVISIONING → RUNNING → STOPPED + UNKNOWN
└── primitives/
    ├── Safe_Str__ECS__Cluster__Name.py
    ├── Safe_Str__ECS__Task__ARN.py
    ├── Safe_Str__ECS__Task__Definition.py
    ├── Safe_Str__ECS__Cluster_Arn.py        — REPLACE, allow_empty (full cluster ARN)
    ├── Safe_Str__ECS__Status.py             — REPLACE, allow_empty (ACTIVE/INACTIVE/…)
    ├── Safe_Str__ECS__Task__Family.py       — REPLACE, allow_empty (task family name)
    ├── Safe_Str__ECS__Task__Def_Arn.py      — REPLACE, allow_empty (full task-def ARN)
    ├── Safe_Str__ECS__CPU.py                — REPLACE, allow_empty (e.g. "256")
    ├── Safe_Str__ECS__Memory.py             — REPLACE, allow_empty (e.g. "512")
    ├── Safe_Str__ECS__Timestamp.py          — REPLACE, allow_empty (ISO-8601 from ECS)
    ├── Safe_Str__ECS__Stop_Reason.py        — REPLACE, allow_empty (free-form stop reason)
    └── Safe_Str__ECS__Group.py              — REPLACE, allow_empty (task group string)
```

### Commands

| Verb | Tier |
|------|------|
| `cluster list` | read-only |
| `cluster describe <name>` | read-only |
| `cluster create <name>` | mutating — gated by `SG_AWS__FARGATE__ALLOW_MUTATIONS=1` |
| `cluster delete <name>` | mutating — refuses if running tasks; gated |
| `task-def list [--family F]` | read-only |
| `task-def show <family:rev>` | read-only |
| `task-def register --name N --image I` | mutating — gated |
| `task list [--cluster C] [--family F]` | read-only |
| `task describe <arn>` | read-only |
| `task run --cluster C --task-def F:R` | mutating — FARGATE only; gated |
| `task stop <arn>` | mutating — gated |
| `task logs <arn> [--since 30m]` | read-only — fetches CloudWatch Logs via `Logs__AWS__Client` |

### Mutation gate

`SG_AWS__FARGATE__ALLOW_MUTATIONS=1`

### Tests

```
tests/unit/sgraph_ai_service_playwright__cli/aws/fargate/
├── service/
│   ├── Fargate__AWS__Client__In_Memory.py   — dict-backed fake ECS boto3 client
│   └── test_Fargate__AWS__Client.py         — 15 tests
└── cli/
    └── test_Cli__Fargate.py                  — 20 tests
```

All 35 unit tests pass (no mocks, no patches).

### Fixture

`tests/fixtures/fargate/hello-world.yaml` — sample task definition YAML for manual CLI testing.

### Docs

- `library/docs/cli/sg-aws/11__fargate.md` — user guide

### v0.2.30 Open-2 — schema fields typed

All previously raw `str` fields in Fargate schemas now use typed primitives:
- `Schema__ECS__Cluster`: `cluster_arn → Safe_Str__ECS__Cluster_Arn`, `status → Safe_Str__ECS__Status`
- `Schema__ECS__Task`: `last_status`, `desired_status → Safe_Str__ECS__Status`; `started_at`, `stopped_at → Safe_Str__ECS__Timestamp`; `stopped_reason → Safe_Str__ECS__Stop_Reason`; `group → Safe_Str__ECS__Group`
- `Schema__ECS__Task__Definition`: `family → Safe_Str__ECS__Task__Family`; `task_def_arn → Safe_Str__ECS__Task__Def_Arn`; `status → Safe_Str__ECS__Status`; `cpu → Safe_Str__ECS__CPU`; `memory → Safe_Str__ECS__Memory`

## What does NOT exist

- Integration tests (`tests/integration/…/fargate/`) — gated on `SG_AWS__FARGATE__INTEGRATION=1`; deferred to follow-up slice
- `Fargate__Task__Wait.py` — task wait-until-RUNNING loop; deferred (run_task returns immediately)
- `Fargate__Task__Logs__Streamer.py` — task logs currently handled inline in Cli__Fargate; a dedicated streamer is a follow-up
- `Fargate__Task_Def__Validator.py` — YAML/JSON file validation; `task-def register --from <file>` not yet implemented
- EC2 launch type support (explicitly out of scope per dev pack)
- Phase 2 (containerise the vault app) and Phase 3 (Fargate-vs-Lambda benchmark) — separate follow-up work

## Decisions

- boto3 used directly (EXCEPTION pattern) — no osbot-aws ECS wrapper at the time of writing
- `cluster delete` refuses if `runningTasksCount > 0`; no `--force` flag in this slice
- Default CloudWatch log group convention: `/ecs/<family>`
- `task run` defaults to `assign_public_ip=False`; explicitly passes FARGATE launch type
- `register_task_definition` hard-codes `networkMode=awsvpc` and `requiresCompatibilities=['FARGATE']`
