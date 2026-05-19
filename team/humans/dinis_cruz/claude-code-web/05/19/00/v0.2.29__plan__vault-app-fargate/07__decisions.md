---
title: "`sg vault-app fargate` — final decisions"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
supersedes:
  - sections of 02__cli-design.md flagged "Config file shape" and "Slug semantics"
  - sections of 03__orchestrator-design.md that reference Vault_App__Fargate__Config
---

# Final decisions (answers to `06__open-questions.md`)

User answered all 12 on 2026-05-19. Decisions below are authoritative — where
they conflict with `02__cli-design.md` or `03__orchestrator-design.md` the
decision here wins. Affected paragraphs in those docs have been edited
in-place; this doc is the canonical answer log.

## Q1 — Scope of V1 → **env-only access token, no AWS Secrets Manager ever, no EFS in V1**

Rationale (your words): the eventual plan is to use one of our own vaults
to host these secrets.

**Implementation effect:**
- AWS Secrets Manager integration is **dropped permanently** from this
  plan. The replacement is "fetch from a peer vault at start time" —
  scoped, designed, and planned separately. Not in this document set.
  - Drops `--secret name=arn` flag on `task-def register` (was A4)
  - Drops `sg aws secrets` sub-package proposal (was C3)
- EFS support is **deferred** (not dropped). The "ephemeral disk per
  task" default is fine for V1; persistent storage can land later as a
  separable slice if/when needed.

## Q2 — Mutation gate → **`SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1`**

One env var. The vault-app fargate CLI programmatically sets the underlying
`SG_AWS__FARGATE__ALLOW_MUTATIONS` / `SG_AWS__IAM__ALLOW_MUTATIONS` /
`SG_AWS__LOGS__ALLOW_MUTATIONS` / `SG_AWS__ECR__ALLOW_MUTATIONS` /
`SG_AWS__EC2__ALLOW_MUTATIONS` for the scope of the command, then restores
them. Users see one gate.

**Implementation note:** small `Mutation__Gate__Scope` context manager in
`sg_compute_specs/vault_app/fargate/service/` — sets env vars on enter,
restores on exit (including exception path).

## Q3 — Config file → **REVERSED: no config file. Use AWS tags as the source of truth.**

Your question ("why do we need this config file?") was the right pushback.
On reflection, persisting a JSON cache to `~/.config/sg/` is wrong for this
project because:

1. **Staleness is invisible.** A user runs `setup create` once, six months
   later changes a subnet or rotates a role, runs `start`, and gets a
   confusing failure because `start` is reading a six-month-old snapshot.
2. **AWS is already the source of truth.** Every field we wanted to cache
   (cluster name, subnets, SG, execution-role ARN, log group, image URI)
   is queryable from AWS in one or two calls.
3. **The project pattern is already tag-based.** The recent dev merge
   pulled in commit `65beaf7e` "refactor(vault-publish): remove SSM —
   Slug__Registry backed by EC2 tags" — exact same conclusion for the
   vault-publish slug registry. We should follow that.
4. **It introduces a config-shape compatibility problem** that's pure
   overhead at this scale.

### Replacement: cluster tags + task-def lookups

Setup tags the cluster with everything start needs:

```
Tags on ECS cluster:
  Stack                       = sg-vault-app-fargate
  VaultApp__Subnets           = subnet-aaa,subnet-bbb       (comma-joined)
  VaultApp__SecurityGroup     = sg-ccc
  VaultApp__DnsZone           = sg-compute.sgraph.ai        (optional, only if setup created the zone wiring)
  VaultApp__ExecutionRoleArn  = arn:aws:iam::123:role/vault-app-fargate-execution
  VaultApp__TaskRoleArn       = arn:aws:iam::123:role/vault-app-fargate-task   (optional)
  VaultApp__LogGroup          = /ecs/sg-vault-app-fargate
  VaultApp__EcrRepoName       = sg-send-vault
  VaultApp__Region            = eu-west-2
  VaultApp__CreatedAt         = 2026-05-19T00:00:00Z
```

Image URI + port mappings + execution-role-arn live on the latest active
revision of the task definition (we put them there during `setup`).

### Start command's discovery cost: 2 parallel calls

Both can fire in parallel before `run_task`:

1. `describe_cluster(name)` — returns cluster tags → subnets, SG, log group,
   etc. (~50 ms)
2. `describe_task_definition(family)` — returns latest revision with image,
   port mappings, role ARNs (~50 ms)

Total discovery time: ~50 ms (parallel max), bounded.

That replaces a config-file read (~5 ms) but removes staleness risk and
keeps AWS as the single source of truth. Worth the 45 ms.

### Slug → cluster mapping (related to Q4)

The slug *is* the cluster name (see Q4). No mapping needed. `start --slug
dinis-tue` finds cluster `dinis-tue`, reads its tags, runs a task on it.

## Q4 — Slug naming → **A, with: slug == cluster name; both auto-generated when omitted**

Refined: a *slug* and a *cluster name* are the same string in V1. The
cluster IS the slug.

### Cluster name conventions

- User-supplied: `sg vault-app fargate setup create --slug demo-tuesday`
  → cluster name `demo-tuesday`.
- Auto-generated: `sg vault-app fargate setup create` → cluster name
  derived from the same generator that `sg vault-app create` uses for
  EC2 stack names (look at `Vault_App__Service.create_stack` and reuse
  the helper). Pattern: `va-fg-<adjective>-<animal>` or similar
  Heroku-style — match whatever pattern `sg vault-app` uses today so
  the user sees consistent naming across both deployment surfaces.

### Why slug == cluster

- One cluster per "thing the user thinks of as a vault deployment" maps
  cleanly to AWS quotas and IAM trust.
- Eliminates the slug-registry problem (no separate lookup; the cluster
  list IS the deployment list).
- `sg vault-app fargate list` becomes `sg aws fargate cluster list
  --tag Stack=sg-vault-app-fargate` plumbed through.
- When Q8 evolves (multi-tenant, one-cluster-per-tenant), the slug ==
  cluster equivalence still holds.

### Constraint

Validate: slug must satisfy both `^[a-z0-9][a-z0-9-]{1,40}$` AND ECS's
cluster-name rules (alphanumeric + hyphen, 1-255 chars). The 40-char cap
keeps tag values short.

### Validation primitive

`Safe_Str__VAF__Slug` — regex `^[a-z0-9][a-z0-9-]{1,40}$`. Same name in V1,
but with the dual meaning called out in the docstring.

## Q5 — Image source → **A: ECR mirror step in setup**

Slow Docker Hub pulls + rate limits are exactly the problem we want to
remove from the start path. Implementation:

- Setup phase `ecr` creates the ECR repo if missing (already in plan).
- Setup phase `image-mirror` (new — adds to the phase list in
  `02__cli-design.md` and `03__orchestrator-design.md`) shells out to
  `docker pull diniscruz/sg-send-vault:latest && docker tag … && docker
  push <ECR>` — captures the final ECR image URI by SHA and writes it
  into the task definition.

Adds a hard dependency on a local `docker` (or `podman`) binary at setup
time. That's acceptable: setup is a one-time operation; start has no
docker dependency.

**Behaviour:** every `setup update --phase image-mirror` re-mirrors and
registers a new task-def revision pinned to that SHA. Re-running setup
without explicitly choosing `image-mirror` keeps the existing revision.

### Phase order updates

The setup phase list becomes:

```
ecr → iam → logs → cluster → image-mirror → task-def
```

(image-mirror requires the ECR repo to exist and runs before task-def
because the task-def references the immutable image SHA.)

## Q6 — Default storage mode → **A: memory**

`SEND__STORAGE_MODE=memory` is the default `--storage-mode` for `start`.
Disk and S3 modes accepted as flags but don't trigger EFS provisioning
(per Q1). Picking `s3` requires `--task-role-arn` to have been set during
setup; the start command validates and errors clearly if it wasn't.

## Q7 — Networking → **A: public IP, Route 53 upsert per start (ALB dropped entirely)**

Public-IP + Route 53. Per user follow-up: `sg aws elbv2` drops from the
plan **permanently** — there are alternative ingress patterns being
explored that may not need an ALB at all. If an ALB-shaped requirement
later materialises it'll be a fresh proposal, not a resurrection of
this one.

Start phase order stays: `RUN_TASK → WAIT_RUNNING → RESOLVE_ENI → DNS_UPSERT
(optional) → WAIT_HEALTH`.

DNS upsert behaviour:
- If cluster tag `VaultApp__DnsZone` is set, upsert `<slug>.<zone>` → public
  IP, TTL 30s.
- If user passes `--no-dns`, skip even if cluster has the zone configured.
- If neither, just print the public IP and the user accesses by IP.

## Q8 — Multi-tenant shape → **A: one AWS account, one cluster per "deployment", many tasks per cluster**

V1 = each slug is its own ECS cluster (per Q4 above). This is actually
*slightly* more isolated than "one cluster many tenants" — closer to
option B in the original question — and that's a good thing: it means
each customer/demo cluster can be torn down independently with zero risk
of touching another.

Cost impact: ECS clusters are free; the only marginal cost is the running
task. No reason to share clusters in V1.

When we evolve to a SaaS model: clusters per customer are already what we
have. The model survives.

## Q9 — Block + render live progress → **A, with: wake-style multi-phase live status**

Refined per your note: "we want something like what we have done for the
wait in vp — list the multiple tasks/steps and show the status of them."

The `Phase__Progress__Renderer` from `04__timing-instrumentation.md` is
already this pattern, but I want to be explicit:

- **Pending phases are visible** (not hidden until they activate) so the
  user can see the whole roadmap from t=0.
- **The currently-running phase shows live in-flight state** in the
  `Detail` column, not just a static "running" — e.g.:
  - `wait-running`: detail field shows `state: PROVISIONING → PENDING → ACTIVATING → RUNNING`, updating as each transition fires
  - `wait-http-health`: detail field shows `attempt 3/30, last 502, retrying in 1.5 s`
  - `dns-upsert`: detail field shows `propagation: 0s … 2s … 4s`
- **Elapsed time per phase updates every 250 ms** so a "stuck" phase
  visibly slows other things from a user's perspective. Reused from the
  rich.live.Live `refresh_per_second=4` pattern in
  `Cli__Setup.py:699`.

This is what your `sg vp wake` does today (`Cli__Vault_Publish.py:145`
prints `[dim] {int(elapsed)}s: state {old} → {new}[/]`). The difference
is that wake prints to a scrolling log; vault-app fargate updates an
in-place table. Both have their place — the table is better for users
glancing at output, the scrolling log is better for tailing in CI.

**Implementation:** every phase function inside `Vault_App__Fargate__Starter`
calls `progress_cb(name, status, detail='…live string…')` at meaningful
state changes (not just enter/exit). The renderer just paints whatever
`detail` is current.

## Q10 — JSON mode → **A: buffer, emit once at end**

No JSONL streaming in V1. The `Schema__VAF__Start__Report` envelope is the
contract.

## Q11 — CloudWatch metrics → **A: skip in V1**

(Your note: "or even better use a vault for it" — agreed, a metrics-vault
or a centralised metrics sink is the right home eventually, not CloudWatch
custom metrics with their fiddly billing.)

## Q12 — Backport `Phase__Timer` to `sg vp` → **A: leave alone**

Phase__Timer ships in slice 1, lives in
`sg_compute_specs/vault_app/fargate/service/`. `sg vp wake` and
`sg vp setup` keep their existing time-tracking. Whoever next changes
those files can adopt it then.

---

## Plan delta — what changes in the implementation slices

### Dropped permanently from the plan (not just V1)

- `sg aws secrets` sub-package (Q1 — we will never use AWS Secrets Manager)
- `--secret` flag on `task-def register` (A4 in extensions)
- `sg aws elbv2` sub-package (post-Q7 update — alternative ingress
  patterns are being explored; if an ALB-shaped requirement does land,
  it'll be a fresh proposal, not a resurrection of this one)
- Persistent config file at `~/.config/sg/` (Q3)
- `Vault_App__Fargate__Config` class (Q3)
- `Schema__VAF__Config` schema (Q3)
- `sg vault-app fargate config show/set/unset` commands (Q3)
- `Cli__Vault_App__Fargate__Config.py` (Q3)

### Deferred (still in the plan, just not V1)

- `sg aws efs` sub-package (Q1)
- `--efs-volume` flag on `task-def register` (A5 in extensions)

### Added to V1

- Setup phase `image-mirror` (Q5)
- `Vault_App__Fargate__Tags__Reader` class — reads cluster tags into a
  resolved Schema__VAF__Cluster__Config in-memory (Q3 replacement)
- `Vault_App__Fargate__Tags__Writer` class — emits the tag set during
  `setup create` (Q3 replacement)
- `Schema__VAF__Cluster__Config` — same fields as the dropped persisted
  config, but populated from AWS tags at start time, not from disk
- `Mutation__Gate__Scope` context manager (Q2)
- Slug auto-generator helper that re-uses `sg vault-app`'s existing name
  generator (Q4) — find the function `sg vault-app` uses and depend on it
  directly; do not duplicate the word lists

### Re-sized

| Slice | Before | After |
|------:|-------|-------|
| 0a (fargate flags) | drop --secret, --efs-volume, --task-role-arn-optional | smaller (~800 LOC, ~30 tests) |
| 0c (logs CLI) | unchanged | unchanged |
| 2 (Spec/Config/Slug/Health) | Config class | drop Config; add Tags__Reader / Tags__Writer; net same size |
| 3 (Setup orchestrator) | + image-mirror phase | slightly larger; ~1700 LOC, ~70 tests |
| 5 (Starter) | unchanged | unchanged |
| 8 (Secrets + EFS) | V1 follow-up | move to "P2, after customer vaults live" |

### Total V1 effort revised

| Original | Revised |
|----------|---------|
| ~10 dev-days | **~8 dev-days** (-2 from dropping secrets/efs surface area) |
| ~8800 LOC  | **~7500 LOC** |
| ~360 tests | **~310 tests** |

## What I'll do next

1. Edit `02__cli-design.md` to drop the config file section and add the
   tag-based discovery pattern.
2. Edit `03__orchestrator-design.md` to drop `Vault_App__Fargate__Config`
   and add `Tags__Reader` / `Tags__Writer`.
3. Edit `05__implementation-slices.md` to reflect the new slice sizes and
   drop slice 8 from V1.
4. Wait for your go-ahead, then start slice 0a (`sg aws fargate` flags).

If anything in this decisions doc surprises you — particularly the Q3
reversal — say so before I edit the rest of the plan, since it has the
biggest cascading effect.
