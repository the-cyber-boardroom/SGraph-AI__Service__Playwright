---
title: "`sg vault-app fargate` — CLI design"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# `sg vault-app fargate` — CLI design

## Mount point

New Typer sub-app added to `sg_compute_specs/vault_app/cli/Cli__Vault_App.py`:

```python
from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app
app.add_typer(fargate_app, name='fargate')
```

All Fargate-specific code lives under `sg_compute_specs/vault_app/fargate/`
(new sub-package), structured exactly like the ECR sub-package shipped on
this branch — `cli/`, `service/`, `schemas/`, `collections/`, `enums/`,
`primitives/`. One class per file. Empty `__init__.py`.

## Full command tree

```
sg vault-app fargate                                        (no-arg shows help)

  # Cluster-level commands take --cluster <name>. Auto-generated on
  # `setup create` if omitted. Auto-resolved on task-level commands
  # (start/stop/etc.) — see "Slug + cluster semantics" below.

  setup                                                     CLUSTER-LEVEL
    check    [--cluster C] [--phase ecr|iam|logs|cluster|image-mirror|task-def|all] [--json]
    status   [--cluster C] [--json]                            what's currently in place
    create   [--cluster C] [--phase ...] [--yes] [--time] [--json]   auto-generates cluster name if --cluster omitted
    update   [--cluster C] [--phase ...] [--yes] [--time] [--json]   re-apply (e.g. image bump)
    delete   [--cluster C] [--phase ...] [--yes] [--time] [--json]   teardown, reverse order
    plan     [--cluster C] [--phase ...] [--json]                    dry-run
    show     [--cluster C]                                           resolved cluster config (tags + active task-def)

  start                                                     TASK-LEVEL — THE FAST PATH
           [--slug S] [--cluster C]
           [--cpu 512] [--memory 1024]
           [--with-aws-dns] [--public-ip|--no-public-ip]
           [--launch-type FARGATE_SPOT|FARGATE]
           [--seed-vault-keys K1,K2] [--access-token T]
           [--time] [--json] [--yes]
           # Slug auto-generated if omitted. Cluster auto-resolved if omitted.
           # Slug must be unique within the cluster (collision check at start).
           # Container env SEND__STORAGE_MODE=memory is hard-coded (Q1/Q6).
  stop     [--slug S] [--cluster C] [--yes] [--time] [--json]
  restart  [--slug S] [--cluster C] [--time] [--json]
  health   [--slug S] [--cluster C] [--timeout 30]
  logs     [--slug S] [--cluster C] [--since 30m] [--follow] [--source vault|ecs]
  url      [--slug S] [--cluster C]                                  print the reachable URL
  open     [--slug S] [--cluster C]                                  open URL in browser
  info     [--slug S] [--cluster C]                                  rich task description + last timings

  list                                                      LIST QUERIES
           [--cluster C]                                              list tasks; default = all our clusters
           [--clusters]                                               list clusters themselves (no tasks)
           [--json]
  timings  [--slug S] [--cluster C] [--last 10] [--json]              historical timings

  # NOTE: `config` subcommand removed per decision Q3 (07__decisions.md).
  # Resolved config lives on AWS tags + the active task definition.
  # `sg vault-app fargate setup show --cluster C` prints the live resolved config.
```

### Slug + cluster semantics

Per the revised Q4 (`07__decisions.md`): **slug ≠ cluster**. The two
identifiers map onto different things:

- **Cluster name** — tenancy / use-case grouping; one cluster per
  customer or per use-case. Carries the shared infrastructure (subnets,
  SG, IAM roles, log group, ECR repo, DNS zone). Created by `setup
  create`. Long-lived.
- **Slug** — identifier of one running vault container (one ECS task).
  Lives only while the task runs. Multiple slugs co-exist in one
  cluster.

Relationship: **1 cluster : N slugs**.

#### `--cluster` and `--slug` flags

`setup create / update / delete / check / status / show / plan` operate
on a **cluster** and take `--cluster`. Auto-generated if omitted.

`start / stop / restart / health / logs / url / open / info` operate on a
**task** identified by `--slug` within a `--cluster`.

#### Cluster identification when `--cluster` is omitted on task-level commands

1. `--cluster <name>` (explicit) → use it.
2. `$SG_VAULT_APP__FARGATE__CLUSTER` env-var → use it.
3. Exactly one cluster tagged `Stack=sg-vault-app-fargate` in the
   current region → use it (typical dev case).
4. Otherwise: `typer.BadParameter` listing candidate cluster names.

#### Slug identification when `--slug` is omitted on task-level commands

1. `--slug <name>` (explicit) → use it.
2. Exactly one RUNNING task in the resolved cluster → use it (typical
   single-vault dev case).
3. Otherwise: `typer.BadParameter` listing candidate slug names.

#### Validation primitives

- `Safe_Str__VAF__Slug`    — regex `^[a-z0-9][a-z0-9-]{1,40}$`
- `Safe_Str__VAF__Cluster` — regex `^[a-z0-9][a-z0-9-]{1,64}$`

Auto-generation uses the same Heroku-style word-list helper that
`sg vault-app create` uses for EC2 stack naming (locate during slice 2;
do NOT duplicate the word lists).

#### `list` semantics

- `list` (no `--cluster`)         — lists tasks across **all** clusters
                                    tagged `Stack=sg-vault-app-fargate`.
- `list --cluster X`              — lists tasks in cluster X only.
- `list --clusters`               — lists clusters themselves (no tasks).

## Output format

Every command supports two modes:

### Default (Rich, human-readable)

Live-progress table during setup/start (see `04__timing-instrumentation.md`).
Final summary panel:

```
╭─ vault-app on Fargate ────────────────────────────────────╮
│ slug          : dinis-tue                                 │
│ cluster       : acme-prod                                 │
│ task arn      : arn:aws:ecs:eu-west-2:…:task/acme-prod/abc│
│ public ip     : 18.130.45.12                              │
│ vault url     : https://dinis-tue.sg-compute.sgraph.ai    │
│ access token  : sg_abc…xyz  (shown ONCE)                  │
│ task ready    :  4.2 s  (RunTask → RUNNING)               │
│ vault ready   :  9.7 s  (RunTask → 200 /info/health)      │
│ total         : 11.1 s                                    │
╰───────────────────────────────────────────────────────────╯
```

The DNS pattern is `<slug>.<cluster-dns-zone>`. The zone comes from the
cluster's `VaultApp__DnsZone` tag set during `setup create`. If two
clusters share a DNS zone, they also share the slug namespace within
that zone — give each cluster its own zone to avoid collisions.

### `--json` (machine-readable)

```json
{
  "slug": "dinis-tue",
  "cluster": "acme-prod",
  "task_arn": "...",
  "task_definition": "acme-prod:7",
  "public_ip": "18.130.45.12",
  "private_ip": "10.0.1.15",
  "vault_url": "https://dinis-tue.sg-compute.sgraph.ai",
  "access_token": "sg_…",
  "phases": [
    {"name": "resolve-task-def",    "ms":  120, "status": "ok"},
    {"name": "run-task",            "ms":  580, "status": "ok"},
    {"name": "wait-running",        "ms": 3490, "status": "ok"},
    {"name": "resolve-eni-ip",      "ms":  240, "status": "ok"},
    {"name": "dns-upsert",          "ms":  410, "status": "ok"},
    {"name": "wait-http-health",    "ms": 6240, "status": "ok"}
  ],
  "timings": {
    "task_ready_ms": 4070,
    "vault_ready_ms": 9750,
    "total_ms": 11080
  },
  "executed_at": "2026-05-19T00:14:33Z"
}
```

JSON envelope is stable and is the contract for downstream tooling (the
eventual customer-facing API, the historical timings table, dashboards).

### `--time` (verbose timing breakdown without JSON)

Adds an extra "phase × duration" Rich table to the default output. Useful
when you want the panel + the breakdown but not the JSON dump.

## Flag conventions

| Flag | Meaning | Default |
|------|---------|---------|
| `--yes`  | Skip confirm prompt for destructive ops | False |
| `--time` | Print phase timings table | False (still measured + included in --json) |
| `--json` | Machine-readable output, no Rich | False |
| `--phase` | Restrict to one or more phases (setup/check/create/update/delete) | `all` |
| `--slug` | Target a specific vault | Auto if exactly one exists |

Mutation gates (matching the project convention):
- All `setup create/update/delete` and `start/stop/restart`: `SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1`
  (mirrors `SG_VAULT_APP__ALLOW_MUTATIONS` if there's one already; otherwise
  reuse the per-AWS-service gates of the underlying calls).

**Decision needed (see [06](./06__open-questions.md)):** one big vault-app
mutation env-var, or rely on the per-service ones (`SG_AWS__FARGATE__ALLOW_MUTATIONS`,
`SG_AWS__IAM__ALLOW_MUTATIONS`, etc.)? My preference: one wrapper env-var
that, when set, unlocks the underlying gates **only for the duration of the
command** by setting them programmatically. This avoids the user having to
export 5 env vars to run setup.

## Setup phases (ordered by dependency)

Each phase is a separately runnable check / create / update / delete.

| Phase | Wraps | What it ensures exists |
|-------|-------|------------------------|
| `ecr` | `sg aws ecr repo-create` | ECR repo `sg-send-vault` exists in this account/region |
| `iam` | `sg aws iam role create`, `sg aws iam policy attach` | `vault-app-fargate-execution` role with `AmazonECSTaskExecutionRolePolicy` attached; `vault-app-fargate-task` role only if `--task-role-arn` requested (no Secrets Manager extras per Q1) |
| `logs` | `sg aws logs group create` (B1 from extensions) | `/ecs/<slug>` log group, 7-day retention |
| `cluster` | `sg aws fargate cluster create` (with `--tag` flag from A8) | Cluster named `<slug>` with the VaultApp__* tag set described above |
| `image-mirror` | local `docker pull/tag/push` (NOT an `sg aws *` call) | `diniscruz/sg-send-vault:latest` mirrored to ECR, captured by SHA — added per Q5 |
| `task-def` | `sg aws fargate task-def register` (extensions A1, A2, A3, A6, A7) | Task definition `<slug>:N` with port mappings (8080/tcp, 443/tcp), execution role, log group, ECR image URI pinned to SHA from `image-mirror` |
| `dns` (optional, P1) | `sg aws dns` (already exists) | Cluster tag `VaultApp__DnsZone` recorded; no record created until start |

`setup create` runs them in order, stopping at first failure. `setup delete`
runs them in **reverse**. `setup check` runs all in parallel (read-only).

## Start phases (the fast path)

| Phase | Time budget | Wraps |
|-------|------------:|-------|
| `resolve-task-def` | < 200 ms | `sg aws fargate task-def show <family>` (latest revision) |
| `run-task`         | < 1 s     | `sg aws fargate task run` with cached subnet/SG (looked up once during setup, persisted to config) |
| `wait-running`     | 3–10 s    | poll `sg aws fargate task describe` every 1 s |
| `resolve-eni-ip`   | < 500 ms  | `sg aws ec2 eni describe <eni-id>` (extension D) |
| `dns-upsert`       | 200–500 ms | `sg aws dns ...` if `--with-aws-dns` |
| `wait-http-health` | 2–15 s    | poll `https://<ip>:443/info/health` (or `:8080`) with adaptive backoff |

**Critical optimization (revised per Q3):** subnet IDs, SG IDs, role ARNs,
log group, DNS zone all live as tags on the ECS cluster, written by `setup
create`. Image URI + port mappings + role ARNs additionally live on the
task definition. The start command fires `describe_cluster` and
`describe_task_definition` **in parallel** before `run_task` (~50 ms
combined). After that: `run_task` + `describe_tasks` (poll) +
`describe_network_interfaces` (once) + `change_resource_record_sets`
(optional).

## Resolved-config shape (lives on AWS tags + task definition, NOT on disk)

Per decision Q3 (`07__decisions.md`): no persisted config file. The same
field set lives on AWS tags + the latest active task-definition revision.

### Tags written to the ECS cluster during `setup create`

```
Stack                       = sg-vault-app-fargate
VaultApp__Subnets           = subnet-aaa,subnet-bbb
VaultApp__SecurityGroup     = sg-ccc
VaultApp__DnsZone           = sg-compute.sgraph.ai             (optional)
VaultApp__ExecutionRoleArn  = arn:aws:iam::123:role/vault-app-fargate-execution
VaultApp__TaskRoleArn       = arn:aws:iam::123:role/vault-app-fargate-task  (optional)
VaultApp__LogGroup          = /ecs/sg-vault-app-fargate
VaultApp__EcrRepoName       = sg-send-vault
VaultApp__Region            = eu-west-2
VaultApp__CreatedAt         = 2026-05-19T00:00:00Z
```

### Fields carried by the task definition (set during `setup task-def create`)

- `containerDefinitions[0].image`            — pinned ECR URI by SHA
- `containerDefinitions[0].portMappings`     — `[8080/tcp, 443/tcp]`
- `containerDefinitions[0].logConfiguration` — points at the log group above
- `executionRoleArn`                         — from cluster tag
- `taskRoleArn` (optional)                   — from cluster tag

### Discovery cost at start time

Start makes **two parallel describe calls** before `run_task`:

1. `fargate_client.describe_cluster(slug)`           — returns cluster tags
2. `fargate_client.describe_task_definition(family)` — returns latest revision

Both ~50 ms. They populate an in-memory `Schema__VAF__Cluster__Config` for
the duration of the command. No disk I/O on the start hot path.

`sg vault-app fargate setup show` prints the resolved view (cluster tags +
task-def details) so users have a single command to see "what would start
use right now". No config show / set / unset commands.

## Commands intentionally NOT in v1

- `bake` — image baking workflow (current `sg vault-app ami bake` analogue);
  add when we want a faster cold-start path via SOCI / image snapshots
- `extend` — auto-terminate timer; Fargate tasks don't have a "shutdown
  timer" model out of the box (would need an EventBridge schedule + a
  stop-task lambda). Skip for v1.
- `connect` / `exec` — `aws ecs execute-command` is gated on the cluster
  having execute-command enabled at create time; add later.
- `recreate` — same as `restart` for Fargate (no instance lifecycle to fight).

## Reading order

Continue to [`03__orchestrator-design.md`](./03__orchestrator-design.md) for
the service-class layout that backs every command.
