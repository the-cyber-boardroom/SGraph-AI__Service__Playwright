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

  setup
    check    [--phase ecr|iam|logs|task-def|all] [--json]   read-only drift detection
    status   [--json]                                       what's currently in place
    create   [--phase ecr|iam|logs|task-def|all]            mutation-gated, default all
             [--yes] [--time] [--json]
    update   [--phase ...] [--yes] [--time] [--json]        re-apply (for image bumps)
    delete   [--phase ...] [--yes] [--time] [--json]        teardown, reverse order
    plan     [--phase ...] [--json]                         print what would happen, no calls
    show                                                    show resolved config (image, role arns, log group, …)

  start                                                     THE FAST PATH
           [--storage-mode memory|disk|s3] [--cpu 512]
           [--memory 1024] [--with-aws-dns] [--public-ip|--no-public-ip]
           [--launch-type FARGATE_SPOT|FARGATE]
           [--seed-vault-keys K1,K2] [--access-token T]
           [--time] [--json] [--yes]
  stop     [--task-arn ARN | --slug NAME] [--yes] [--time] [--json]
  restart  [--slug NAME] [--time] [--json]                  stop+start with same task-def
  health   [--slug NAME] [--timeout 30]                     poll /info/health
  logs     [--slug NAME] [--since 30m] [--follow] [--source vault|ecs]
  url      [--slug NAME]                                    print the reachable URL
  open     [--slug NAME]                                    open the URL in browser
  list                                                      tasks + status, like `sg vault-app list`
  info     [--slug NAME]                                    rich task description + last timings
  timings  [--slug NAME] [--last 10] [--json]               historical timings table

  config
    show                                                    resolved config
    set    <key> <value>                                    persist override (in $HOME or repo)
    unset  <key>
```

### Slug semantics

A vault instance on Fargate is identified by a **slug** — a short name like
`dinis-laptop-tue` or `customer-acme-prod`. Slug → ECS task tag
`Vault-App-Slug=<slug>`. `start --slug` is optional; missing → auto-generated
(matches `sg vault-app create` stack naming).

The slug is the bridge between `start` and `stop / logs / health / url`. No
slug means "default — there should be exactly one running vault" (error if
more than one).

## Output format

Every command supports two modes:

### Default (Rich, human-readable)

Live-progress table during setup/start (see `04__timing-instrumentation.md`).
Final summary panel:

```
╭─ vault-app on Fargate ────────────────────────────────╮
│ slug          : dinis-tue                             │
│ task arn      : arn:aws:ecs:eu-west-2:…:task/vault/abc│
│ public ip     : 18.130.45.12                          │
│ vault url     : https://dinis-tue.sg-compute.sgraph.ai│
│ access token  : sg_abc…xyz  (shown ONCE)              │
│ task ready    :  4.2 s  (RunTask → RUNNING)           │
│ vault ready   :  9.7 s  (RunTask → 200 /info/health)  │
│ total         : 11.1 s                                │
╰───────────────────────────────────────────────────────╯
```

### `--json` (machine-readable)

```json
{
  "slug": "dinis-tue",
  "task_arn": "...",
  "task_definition": "vault-app:7",
  "cluster": "vault-app",
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
| `ecr` | `sg aws ecr repo-create`, `sg aws ec2 docker-push` (none — use docker CLI) | ECR repo `sg-send-vault` exists; latest tag mirrored from Docker Hub if asked |
| `iam` | `sg aws iam role create`, `sg aws iam policy attach` | `vault-app-fargate-execution` role (with `AmazonECSTaskExecutionRolePolicy` + Secrets Manager read), `vault-app-fargate-task` role (with `s3:*` on the vault bucket, optional) |
| `logs` | `sg aws logs group create` (B1 from extensions) | `/ecs/vault-app` log group, 7-day retention |
| `cluster` | `sg aws fargate cluster create` | Cluster named `vault-app` |
| `task-def` | `sg aws fargate task-def register` (with extensions A1, A2, A3, A6, A7) | Task definition `vault-app:N` with port mappings (8080/tcp, 443/tcp), execution role, log group, current image SHA |
| `efs` (P1) | `sg aws efs create`, `sg aws efs mount-target create` | Persistent storage if `--storage-mode disk` requested |
| `dns` (optional) | `sg aws dns` (already exists) | Empty A record skeleton in target zone for future starts |

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

**Critical optimization:** subnet IDs, SG IDs, cluster name, task-def family
all live in a config file (`$HOME/.config/sg/vault-app-fargate.json`)
populated by `setup create`. The `start` command never makes a `describe` call
to discover them. Goal: 0 AWS calls during start besides `run-task`,
`describe-tasks` (poll), `describe-network-interfaces` (once), `dns change-resource-record-sets` (optional).

## Config file shape

Persisted at `$HOME/.config/sg/vault-app-fargate.json` (or repo-local
override via `--config`):

```json
{
  "cluster": "vault-app",
  "task_def_family": "vault-app",
  "subnets": ["subnet-aaa", "subnet-bbb"],
  "security_groups": ["sg-ccc"],
  "execution_role_arn": "arn:aws:iam::123:role/vault-app-fargate-execution",
  "task_role_arn":      "arn:aws:iam::123:role/vault-app-fargate-task",
  "log_group": "/ecs/vault-app",
  "image_uri": "123.dkr.ecr.eu-west-2.amazonaws.com/sg-send-vault:latest",
  "dns_zone": "sg-compute.sgraph.ai",
  "default_storage_mode": "memory",
  "default_launch_type":  "FARGATE_SPOT",
  "region": "eu-west-2"
}
```

`sg vault-app fargate config show` prints this. `setup create` writes it.
`start` reads it. `setup delete` removes it.

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
