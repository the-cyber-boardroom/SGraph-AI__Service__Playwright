---
title: "`sg vault-app fargate` — implementation slices"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# Implementation slices

Eight slices, each commit-shaped, each shippable on its own. Order is by
dependency. Sizes are calibrated against the recent ECR / EC2 work:

- "Small" ≈ ECR P1 / EC2 P1 (~600–1000 LOC, ~30 tests)
- "Medium" ≈ ECR P0 / EC2 AMI P0 (~1000–1500 LOC, ~50 tests)
- "Large" ≈ ECR P0 + P1 combined (~2000+ LOC, ~100 tests)

## Pre-work (must land before vault-app fargate work starts)

### Slice 0a — `sg aws fargate` essential flags (Medium)

Adds to `Cli__Fargate.py` + `Fargate__AWS__Client.register_task_definition`:

- `--port-mapping <port>/<proto>` (repeatable)         [A1]
- `--execution-role-arn <arn>`                         [A2]
- `--task-role-arn <arn>` (optional)                   [A3]
- `--log-group <name>`                                 [A6]

And to `Fargate__AWS__Client.run_task` + `Cli__Fargate.task_run`:

- `--launch-type FARGATE|FARGATE_SPOT`                 [A7]
- `--tag k=v` (repeatable)                             [A8]

Per Q1: `--secret` (A4) and `--efs-volume` (A5) DROPPED from V1.
Per Q5 / Q4: `cluster create --tag k=v` is critical for setup writing the
VaultApp__* tag set; ensure it's exposed (A8 covers this too if `create`
gains the same `--tag` shape; if not, add it to `cluster create` too).

Schemas:
- `Schema__ECS__Port_Mapping` (container_port, protocol)
- Extend `Schema__ECS__Task__Definition` with `port_mappings:
  List__Schema__ECS__Port_Mapping`, `execution_role_arn`, `task_role_arn`,
  `log_group`
- Extend `Schema__ECS__Task` with `launch_type`, `tags: dict`

In-memory client `Fargate__AWS__Client__In_Memory` extended to round-trip
these fields. ClientError shapes added for the common failure paths
(`InvalidParameterException` if execution_role_arn is missing when image is
ECR-hosted; `ClientException` for bad port specs).

Tests: ~40 new (every flag, every error path, table + JSON output).

### Slice 0b — `sg aws ec2 eni` CLI (Small)

`sgraph_ai_service_playwright__cli/aws/ec2/cli/Cli__EC2__Eni.py`:

```
sg aws ec2 eni list  [--sg sg-xxx] [--vpc vpc-yyy]    [--json]
sg aws ec2 eni show  <eni-id>                         [--json]
```

`list_network_interfaces` already exists in `EC2__AWS__Client` (added in EC2
SG slice). Add `describe_network_interface(eni_id)` and a new schema
`Schema__EC2__ENI` (eni_id, subnet_id, vpc_id, public_ip, private_ip,
attachment_instance_id, attachment_status, security_group_ids).

Tests: ~15.

### Slice 0c — `sg aws logs` CLI (Medium)

New sub-package:

```
sg aws logs groups list                              [--json]
sg aws logs group describe <name>                    [--json]
sg aws logs group create  <name> [--retention 7]     [SG_AWS__LOGS__ALLOW_MUTATIONS]
sg aws logs group delete  <name>                     [SG_AWS__LOGS__ALLOW_MUTATIONS]
sg aws logs tail <group> [--stream <pat>] [--since 5m] [--follow]
```

Re-use the existing `Logs__Insights__Queries` service class where it fits.
Mirror the ECR slice 1 file layout exactly. Mutation gate
`SG_AWS__LOGS__ALLOW_MUTATIONS`. In-memory client. Tests: ~50.

**Net pre-work: ~2500 LOC, ~105 tests, 3 commits.** This unblocks slice 1.

---

## Vault-app fargate slices

### Slice 1 — `Phase__Timer` + progress renderer + schemas (Medium)

Foundation. Nothing AWS-facing. Pure utility + Type_Safe schemas.

Production code:
- `sg_compute_specs/vault_app/fargate/service/Phase__Timer.py`
- `sg_compute_specs/vault_app/fargate/service/Phase__Progress__Renderer.py`
- `sg_compute_specs/vault_app/fargate/schemas/Schema__Phase__Result.py`
- `sg_compute_specs/vault_app/fargate/collections/List__Schema__Phase__Result.py`
- `sg_compute_specs/vault_app/fargate/enums/Enum__VAF__Phase__Status.py`

Tests cover:
- Context-manager success / exception paths
- `total_ms` / `cumulative_through` calculations
- Progress callback emission (PENDING → RUNNING → OK / ERROR)
- Renderer state transitions (snapshot-based golden tests, no live ANSI)

~600 LOC, ~30 tests.

### Slice 2 — Spec + Tags__{Reader,Writer} + Slug + Health + Image__Mirror + Mutation__Gate (Medium)

Per Q3, the config classes are dropped and replaced with tag read/write
helpers. Per Q5, the image-mirror helper lives here. Per Q2, the unified
mutation-gate scope lives here.

Production code:
- `Vault_App__Fargate__Spec.py`             constants + env-var builder
- `Schema__VAF__Cluster__Config.py`         in-memory shape from tags (Q3)
- `Vault_App__Fargate__Tags__Reader.py`     describe_cluster → Schema__VAF__Cluster__Config
- `Vault_App__Fargate__Tags__Writer.py`     produce the VaultApp__* tag dict for setup
- `Safe_Str__VAF__Slug.py`                  regex + ECS cluster-name compatibility
- `Vault_App__Fargate__Slug__Resolver.py`   slug → cluster (one describe_cluster); missing-slug auto-resolve
- `Vault_App__Fargate__Health.py`           HTTP poll (extracted from sg vp wake)
- `Vault_App__Fargate__Image__Mirror.py`    docker pull/tag/push to ECR (Q5)
- `Mutation__Gate__Scope.py`                env-var scope for `SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS` (Q2)

Slug auto-generator: locate the helper that `sg vault-app create` uses
for EC2 stack name auto-generation and depend on it directly (do NOT
duplicate the word lists per Q4).

Tests: in-memory `Fargate__AWS__Client` for tags + slug-resolver; HTTP
fixture (httpx, the no-mock rule is about AWS not HTTP) for `Health`;
image-mirror gets a stub subprocess runner.

~900 LOC, ~45 tests.

### Slice 3 — `Vault_App__Fargate__Setup` orchestrator (Large)

The heart of setup mode. One `Setup__VAF` class with the seven `_phase_*`
methods. Returns `Schema__VAF__Setup__Report`. Calls into `ECR__AWS__Client`,
`IAM__AWS__Client`, `Logs__AWS__Client`, `Fargate__AWS__Client` (all from
slice 0).

Production code:
- `Vault_App__Fargate__Setup.py`
- `Schema__VAF__Setup__Report.py`, `Schema__VAF__Setup__Request.py`
- `Enum__VAF__Setup__Phase.py`

Tests:
- Each phase: check / create / update / delete, idempotent (run twice =
  second is SKIPPED)
- Combined `setup create` runs phases in dependency order; stops at first
  ERROR by default; `--continue-on-error` runs through
- `setup delete` runs in reverse order; phases that don't exist are SKIPPED

~1500 LOC, ~60 tests.

### Slice 4 — `Cli__Vault_App__Fargate__Setup` (Medium)

Thin CLI wrapping slice 3. Mounts the live-progress renderer (slice 1) into
the orchestrator (slice 3). Commands: `check`, `status`, `plan`, `create`,
`update`, `delete`, `show`.

Per Q3: NO `config` sub-commands. `setup show` displays the resolved
cluster-tag + task-def view, which is the live equivalent.

~600 LOC, ~35 tests.

### Slice 5 — `Vault_App__Fargate__Starter` (Medium)

The fast-path orchestrator. Pure logic — no Typer. Uses `Phase__Timer`,
`Vault_App__Fargate__Health`, `Vault_App__Fargate__Slug__Resolver`,
`Vault_App__Fargate__Timings__Store`.

Production code:
- `Vault_App__Fargate__Starter.py`
- `Vault_App__Fargate__Timings__Store.py`
- `Schema__VAF__Start__Request.py`, `Schema__VAF__Start__Report.py`
- `Schema__VAF__Timings__Record.py`
- `Enum__VAF__Start__Phase.py`

Tests cover the full happy path + every phase failure (no public IP, HTTP
timeout, DNS failure, task fails to start) against in-memory clients. Time
assertions use the `Phase__Timer` stub.

~1200 LOC, ~50 tests.

### Slice 6 — `Cli__Vault_App__Fargate__Start` (Medium)

Thin CLI wrapping slice 5: `start`, `stop`, `restart`, `health`, `url`,
`open`, `logs`, `list`, `info`, `timings`.

~700 LOC, ~40 tests.

### Slice 7 — Documentation + reality-doc updates (Small)

- `library/docs/specs/v0.2.X__vault-app-fargate.md` — the contract
- `library/onboarding/v0.2.X__vault-app-fargate.md` — "how to run a vault
  on Fargate in 3 commands"
- `team/roles/librarian/reality/cli/vault-app/index.md` — add the fargate
  sub-app
- `team/roles/librarian/reality/aws/fargate/index.md` — note the new flags
- Update `library/catalogue/README.md`

~300 LOC of markdown, no tests.

### Slice 8 (P2, post-V1) — EFS only

AWS Secrets Manager is permanently out of scope (Q1 update). When secrets
need to leave plaintext `--env`, the path is "fetch from a peer vault at
container start" — a separate plan, not this one.

What remains for an eventual slice 8:

- `sg aws efs` sub-package (C1 in extensions)
- `--efs-volume` flag on `task-def register` (A5 in extensions)
- `vault-app fargate setup efs` phase (idempotent fs + mount target)
- `start --storage-mode disk` actually mounts EFS

Lands when persistent vault state on Fargate becomes a real requirement.
Roughly ~1500 LOC / 2 dev-days (vs the ~3000 LOC original estimate that
bundled Secrets in).

---

## Dependency graph

```
slice 0a (fargate flags)  ──┐
slice 0b (eni)        ──────┼─── slice 1 (Phase__Timer)        ──┐
slice 0c (logs)       ──────┘                                      │
                                                                   │
                            slice 2 (Spec/Config/Slug/Health)   ──┤
                                                                   │
                            slice 3 (Setup orchestrator)        ──┼─── slice 4 (Setup CLI)
                                                                   │
                            slice 5 (Starter orchestrator)      ──┼─── slice 6 (Start CLI)
                                                                   │
                            slice 7 (docs / reality)           ────┘
```

Slices 1 and 2 can land in parallel (no overlap). Slices 3 and 5 share the
config + spec but build different things — also parallelizable after 1 + 2.
4 and 6 are thin CLI veneers; can land in parallel after 3 and 5.

## Branching

One feature branch per slice (matches the recent ECR / EC2 cadence):
`claude/vaf-slice-0a-fargate-flags`, `claude/vaf-slice-1-phase-timer`, etc.
PR each to dev. Avoid stacking PRs unless necessary — most slices are
self-contained.

## Effort estimate

| Slice | Size | LOC | Tests | Days (single dev) |
|------:|------|----:|------:|------------------:|
| 0a    | Med  |  800 |  30 | 0.7  (-0.3 after Q1 drops --secret/--efs-volume) |
| 0b    | Sm   |  400 |  15 | 0.5 |
| 0c    | Med  | 1500 |  50 | 1 |
| 1     | Med  |  600 |  30 | 1 |
| 2     | Med  |  900 |  45 | 1   (+0.5 for image-mirror + Mutation__Gate__Scope) |
| 3     | Lg   | 1500 |  60 | 2 |
| 4     | Med  |  600 |  35 | 0.8  (-0.2 after dropping config commands) |
| 5     | Med  | 1200 |  50 | 1.5 |
| 6     | Med  |  700 |  40 | 1 |
| 7     | Sm   |  300 |   0 | 0.3 |
| **V1 total** | | **~8500** | **~355** | **~9.8 dev-days** |
| 8     | DROPPED FROM V1 (Q1) | — | — | — |

Comparable in scope to the ECR + EC2 work that just shipped (~5700 LOC,
234 tests) but ~1.5× larger because of the cross-cutting orchestration and
the pre-work in `sg aws fargate`/`logs`/`eni`.

## What to ship first as the "spike" if we want to validate before
committing to the full plan

If you want a single 2-day spike to prove the end-to-end works before doing
all 10 days of polish:

1. **Slices 0a + 0b** (just the P0 fargate flags + eni). 1.5 days.
2. A minimal `vault-app fargate start` script (no orchestrator class, just a
   single CLI function that imports the clients directly and runs the start
   phases inline). 0.5 days.

That produces a one-shot script that proves the start-path latency. If the
warm-image start is under 15 s, the plan is worth the rest of the slices. If
it's 60+ s, we have a fundamental problem (image size, Fargate platform,
networking) to solve before scaling up.

## Reading order

Continue to [`06__open-questions.md`](./06__open-questions.md) — there are
decisions I need from you before slice 0a kicks off.
