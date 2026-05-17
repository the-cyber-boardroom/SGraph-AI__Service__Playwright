---
title: "v0.2.29 — sg aws fargate (Slice C)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: M — ~1500 prod lines, ~600 test lines, ~2.5 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_brief: team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__fargate-vault-hosting-experiment.md
feature_branch: claude/aws-primitives-support-uNnZY-fargate
---

# `sg aws fargate` — Slice C

The CLI primitive layer for Fargate. Enables the Fargate-vs-Lambda benchmark the source brief frames (the benchmark itself is a separate experiment, not part of this slice).

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/cli/` (look for `cli/aws-*.md`) before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

Independent of all other v0.2.29 slices. Consumers are the Fargate-vs-Lambda benchmark, the future container-hosts primitive (which compares against Fargate), and any "deploy to Fargate" workflow.

---

## Source brief

[`v0.27.43__dev-brief__fargate-vault-hosting-experiment.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__fargate-vault-hosting-experiment.md) is ground truth. This slice delivers **Phase 1 of the source brief** (the CLI commands). Phase 2 (containerise the vault app) and Phase 3 (run the benchmark) are out of scope and ship as follow-up work using these primitives.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/fargate/` (Foundation ships the skeleton; you fill in the bodies)

### Verbs

| Verb | Tier | Notes |
|------|------|-------|
| `cluster-list` | read-only | All Fargate clusters in account/region |
| `cluster-describe <name>` | read-only | Capacity, running task count, default platform version |
| `cluster-create <name>` | mutating | Sensible defaults (Fargate-only capacity providers; CloudWatch Logs on) |
| `cluster-delete <name>` | mutating | Refuses if tasks still running |
| `task-def list` | read-only | Family names + latest revisions |
| `task-def show <family>[:rev]` | read-only | Full task definition JSON |
| `task-def register --from <file>` | mutating | Register a new revision from a Type_Safe-validated YAML/JSON file |
| `task-run <task-def>` | mutating | Launch a task — see flags below |
| `task-list [--cluster X]` | read-only | Running + recently stopped tasks |
| `task-describe <task-id>` | read-only | Full task state |
| `task-stop <task-id>` | mutating | Stop a running task |
| `task-logs <task-id>` | read-only | Stream / fetch task logs from CloudWatch |

**Mutation gate:** `SG_AWS__FARGATE__ALLOW_MUTATIONS=1` required for `cluster-create / cluster-delete / task-def register / task-run / task-stop`.

### `task-run` flags

```
sg aws fargate task-run <task-def-family>[:rev]
  --cluster <name>                          # default: $SG_AWS__FARGATE__DEFAULT_CLUSTER
  --subnets <id>[,<id>...]                  # default: $SG_AWS__FARGATE__DEFAULT_SUBNETS
  --security-groups <id>[,<id>...]          # default: $SG_AWS__FARGATE__DEFAULT_SG
  --assign-public-ip / --no-public-ip       # default: --no-public-ip
  --command <override>                      # container command override
  --env K=V[,K=V...]                        # environment overrides
  --tags K=V[,K=V...]                       # in addition to sg:* tags from Foundation
  --wait                                    # block until RUNNING (default: true)
  --json
```

---

## Production files (indicative)

```
aws/fargate/
├── cli/
│   ├── Cli__Fargate.py
│   └── verbs/
│       ├── Verb__Fargate__Cluster__List.py
│       ├── Verb__Fargate__Cluster__Describe.py
│       ├── Verb__Fargate__Cluster__Create.py
│       ├── Verb__Fargate__Cluster__Delete.py
│       ├── Verb__Fargate__Task_Def__List.py
│       ├── Verb__Fargate__Task_Def__Show.py
│       ├── Verb__Fargate__Task_Def__Register.py
│       ├── Verb__Fargate__Task__Run.py
│       ├── Verb__Fargate__Task__List.py
│       ├── Verb__Fargate__Task__Describe.py
│       ├── Verb__Fargate__Task__Stop.py
│       └── Verb__Fargate__Task__Logs.py
├── service/
│   ├── Fargate__AWS__Client.py             # wraps Sg__Aws__Session (ECS API)
│   ├── Fargate__Task__Wait.py
│   ├── Fargate__Task__Logs__Streamer.py    # uses existing aws/logs/ for CloudWatch Logs
│   └── Fargate__Task_Def__Validator.py     # validates the YAML/JSON file against Schema__Fargate__Task__Definition
├── schemas/                                # Schema__Fargate__Cluster, ...Task, ...Task__Definition, ...Container__Definition, etc.
├── enums/                                  # Enum__Fargate__Task__State, Enum__Fargate__Launch__Type
├── primitives/                             # Safe_Str__Fargate__Task_Id, Safe_Str__Fargate__Task_Def_Arn, etc.
└── collections/                            # List__Schema__Fargate__Task, etc.
```

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned)
- Containerising the vault app (Phase 2 of the source brief — out of scope here)
- The benchmark suite itself (Phase 3 — out of scope; uses these primitives)
- The container-hosts primitive (separate v0.2.30 pack)

---

## Acceptance

```bash
# read-only
sg aws fargate cluster-list                                            # → table
sg aws fargate task-def list --json | jq length
sg aws fargate task-list --cluster sg-test-cluster

# mutating (gated)
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 sg aws fargate cluster-create sg-test-cluster --yes

# register a task-def from a YAML file
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 sg aws fargate task-def register \
    --from tests/fixtures/fargate/hello-world.yaml --yes
# → returns the new revision number

SG_AWS__FARGATE__ALLOW_MUTATIONS=1 sg aws fargate task-run hello-world \
    --cluster sg-test-cluster --yes --wait
# → returns task ARN, blocks until RUNNING

sg aws fargate task-list --cluster sg-test-cluster --json | jq '.[].task_id'
sg aws fargate task-logs <task-id>                                      # → tail of CloudWatch logs

SG_AWS__FARGATE__ALLOW_MUTATIONS=1 sg aws fargate task-stop <task-id> --yes
SG_AWS__FARGATE__ALLOW_MUTATIONS=1 sg aws fargate cluster-delete sg-test-cluster --yes

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/fargate/ -v
SG_AWS__FARGATE__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/fargate/ -v
```

---

## Deliverables

1. All files under `aws/fargate/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/fargate/`
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/fargate/` (gated; provisions + tears down a real cluster)
4. A fixture task-definition YAML under `tests/fixtures/fargate/hello-world.yaml`
5. New user-guide page `library/docs/cli/sg-aws/11__fargate.md`
6. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
7. Reality-doc update: new `team/roles/librarian/reality/cli/aws-fargate.md`

---

## Risks to watch

- **Networking defaults.** Fargate requires a VPC with subnets + security groups. The first-run experience needs sensible env-var defaults (`SG_AWS__FARGATE__DEFAULT_CLUSTER / SUBNETS / SG`) plus a clear "you must configure these" error if missing.
- **Cluster-delete with running tasks.** AWS allows it but it abandons the tasks. Refuse unless `--force` AND tasks are explicitly listed by ARN in the command.
- **Task-logs streaming.** Reuse the existing `aws/logs/` CloudWatch Logs primitives; don't reinvent. `Fargate__Task__Logs__Streamer` orchestrates which log group + stream to read.
- **Launch-type lock-in.** Default to `FARGATE` launch type. Refuse `EC2` launch type in this slice (out of scope; will land later via the container-hosts primitive).
- **Cost during dev iteration.** A task running with no `--wait` and no `task-stop` keeps billing. Default `task-run --wait` to true so the operator sees the running state and remembers to stop it.

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-fargate`

Commit message: `feat(v0.2.29): sg aws fargate — cluster/task/task-def primitives + logs streaming`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

Independent. Cancelling here defers the Fargate-vs-Lambda benchmark and the future "deploy to Fargate" workflow; no other v0.2.29 slice is affected.
