---
title: AWS ALB CRUD — `sg aws alb` module
date: 2026-05-19
authors: [claude]
status: proposed
target_version: v0.2.36
companion:
  - sgraph_ai_service_playwright__cli/aws/ec2/                        (mutation surface — slice template)
  - sgraph_ai_service_playwright__cli/aws/ec2/service/VPC__Stack__Provisioner.py  (phased orchestrator template)
  - sgraph_ai_service_playwright__cli/aws/fargate/                    (smaller skeleton template)
---

# Goal

Add full CRUD for AWS Application Load Balancers (boto3 `elbv2`) so an ALB can
be provisioned end-to-end and pointed at the EC2 instances or Fargate tasks
this repo already knows how to create.

The recent EC2 + VPC stack work (3 slices: read foundation → mutation surface →
`VPC__Stack__Provisioner`) produces exactly the substrate an internet-facing
ALB needs:

- 2 public subnets in distinct AZs (already created by `VPC__Stack__Provisioner`)
- `create_security_group` + `authorize_security_group_ingress` already on `EC2__AWS__Client`
- IGW + route table already provisioned

So the ALB module is mostly a new `elbv2` boto3 wrapper + a stack provisioner
that composes existing pieces. **Zero changes to EC2 or VPC provisioner. Zero
changes to Fargate.** One line added to `aws/cli/Cli__Aws.py` to register the
sub-app.

# Surface area (boto3 `elbv2`)

Three resource types:

| Resource       | Calls to wrap                                                                                                  |
|----------------|----------------------------------------------------------------------------------------------------------------|
| Load Balancers | `create`, `describe`, `delete`, `modify_attributes`, `describe_attributes`                                     |
| Target Groups  | `create`, `describe`, `delete`, `modify`, `register_targets`, `deregister_targets`, `describe_target_health`   |
| Listeners      | `create`, `describe`, `delete`, `modify`                                                                       |

Plus elbv2-flavoured `add_tags` / `remove_tags`. Listener rules deferred to v2.

# Two target-type paths

- **`TargetType=instance`** for EC2 — register `instance_id` directly.
- **`TargetType=ip`** for Fargate — resolve the task's ENI private IP via the
  existing `EC2__AWS__Client.describe_network_interface`, then
  `register_targets` with the IP. **No `Fargate__AWS__Client` change required.**

ECS Services (`create_service`/`update_service`) deliberately deferred — direct
`register_targets` is enough for v1 and avoids introducing a whole new ECS
surface.

# Skeleton

Follow the convention used by every other `aws/{domain}/` module:

```
sgraph_ai_service_playwright__cli/aws/alb/
├── primitives/      # Safe_Str__ALB__{LB_Arn,LB_Name,TG_Arn,TG_Name,Listener_Arn,Protocol,...}
├── enums/           # Enum__ALB__{LB_State,LB_Scheme,Target_Health,Protocol,Target_Type}
├── schemas/         # Schema__ALB__{Load_Balancer,Target_Group,Listener,Health_Check,...}
├── collections/     # List__Schema__ALB__*
├── service/         # ALB__AWS__Client.py + (later) ALB__Stack__Provisioner.py
└── cli/             # Cli__ALB.py + per-resource verb files
```

| Concern                | Copy from                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------|
| Layout / per-resource CLI split | `sgraph_ai_service_playwright__cli/aws/ec2/cli/Cli__EC2__{Vpc,Sg,Subnet,Igw,...}.py` |
| Single boto3 seam      | `sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py`            |
| Tag / parse helpers    | `sgraph_ai_service_playwright__cli/aws/ec2/service/EC2__AWS__Client.py`                    |
| Phased stack provisioner | `sgraph_ai_service_playwright__cli/aws/ec2/service/VPC__Stack__Provisioner.py`           |
| In-memory test client  | `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/service/EC2__AWS__Client__In_Memory.py` |
| Mutation gate          | `sgraph_ai_service_playwright__cli/aws/_shared/Mutation__Gate.py` (reuse as-is)            |

CLI sub-app registration: one line in `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`:

```python
app.add_typer(alb_app, name='alb')
```

# Integration touchpoints (zero code changes outside `aws/alb/`)

- **VPC stack** — `VPC__Stack__Provisioner` already returns
  `Schema__VPC__Stack__Report.subnet_ids` (2 subnets, distinct AZs). Feed that
  straight into ALB creation.
- **Security groups** — ALB SG (80/443 from 0.0.0.0/0) and target SG (ingress
  from ALB SG via `UserIdGroupPairs`) are expressible with current
  `EC2__AWS__Client` methods. Naming already respects constraint #14 (no `sg-`
  prefix) via `sg_name_for_stack`.
- **Fargate** — `register_targets` with `TargetType=ip` only needs the task's
  ENI private IP, which `EC2__AWS__Client.describe_network_interface` already
  returns.

# Slices

Mirroring the EC2 mutation work (3 reviewable commits).

## Slice 1 — Read foundation

| Item       | Count / detail                                                                  |
|------------|---------------------------------------------------------------------------------|
| Primitives | ~8 (LB_Arn, LB_Name, TG_Arn, TG_Name, Listener_Arn, Protocol, Health_Status, Target_Type) |
| Enums      | ~5 (LB_State, LB_Scheme, Target_Health, Protocol, Target_Type)                  |
| Schemas    | ~6 (Load_Balancer, Target_Group, Listener, Default_Action, Target_Health_Description, Health_Check) |
| Collections| ~6 `List__Schema__ALB__*`                                                     |
| Client     | `ALB__AWS__Client` with `list_*` + `describe_*` + `describe_target_health` (~400 LOC) |
| In-memory  | `ALB__AWS__Client__In_Memory` (~400 LOC)                                      |
| CLI        | `lb list/show`, `tg list/show`, `listener list/show`                            |
| Tests      | ~15                                                                             |
| Total      | ~25-30 new files                                                                |

## Slice 2 — Mutation surface

| Item            | Count / detail                                                             |
|-----------------|----------------------------------------------------------------------------|
| Client mutations| `create/delete/modify` for all three resource types; `register_targets`, `deregister_targets`; tag add/remove (~350 LOC) |
| Request schemas | ~3 (`Schema__ALB__{LB,TG,Listener}__Create__Request`)                    |
| CLI verbs       | `Cli__ALB__LB.py`, `Cli__ALB__TG.py`, `Cli__ALB__Listener.py` (create/delete/register/deregister) |
| Gating          | Reuse `_shared/Mutation__Gate.py` + `Aws__Confirm.py`                      |
| Tests           | ~20                                                                        |
| Total           | ~15-20 new files                                                           |

## Slice 3 — Stack provisioner + Fargate hook

| Item              | Count / detail                                                                              |
|-------------------|---------------------------------------------------------------------------------------------|
| Provisioner       | `ALB__Stack__Provisioner.py` (~450 LOC) — phased SG → ALB → TG → listener, idempotent re-run via tag matching, rollback on phase failure |
| Phase enum        | `Enum__ALB__Stack__Phase`                                                                   |
| Schemas           | `Schema__ALB__Stack__{Request,Detail,Report}`                                               |
| Fargate hook      | Thin helper: resolves task ENI IP via `EC2__AWS__Client.describe_network_interface`, calls `register_targets` (no `Fargate__AWS__Client` change) |
| CLI               | `Cli__ALB__Stack.py` with `provision/destroy/describe`                                    |
| Tests             | ~10-12 provisioner unit + 1 deploy-via-pytest smoke                                         |
| Total             | ~10-15 new files                                                                            |

# Total estimate

| Metric                    | Estimate                                                       |
|---------------------------|----------------------------------------------------------------|
| New production `.py`      | ~55-65                                                         |
| New test `.py`            | ~30-40 (in-memory + unit + provisioner)                        |
| New tests                 | ~50-60 unit + 1 deploy smoke                                   |
| Production LOC            | ~3,000-3,500                                                   |
| Test LOC                  | ~2,500-3,000                                                   |
| Relative to EC2 effort    | ~70-80% (fewer resource types, but no parser reuse from EC2)   |
| Cross-domain edits        | 1 line in `aws/cli/Cli__Aws.py`                                |

# Independent shippability

Each slice can land and be reviewed on its own.

- **After Slice 1**: read-only `sg aws alb lb/tg/listener list/show` against a
  real account — useful for inventory and debugging existing ALBs.
- **After Slice 2**: one-off `sg aws alb lb create`, `tg create`, `register-targets`
  — usable but requires the operator to compose the steps manually.
- **After Slice 3**: single-command `sg aws alb stack provision` + Fargate
  task target-registration — the "spin up Fargate vault → register with ALB"
  end-to-end path.

# Decisions (resolved 2026-05-19)

1. **HTTP only, port 8080** — no HTTPS/ACM in v1. The vault-app already serves
   HTTP on port 8080 (the ACME-cert path doesn't work for bare-IP direct
   access; that's a separate problem solved by DNS+Let's Encrypt at the
   container level). Slice 2 listener defaults: `Protocol=HTTP`, `Port=80`
   (public-facing) → forward to TG. Target group defaults: `Protocol=HTTP`,
   `Port=8080`. The ACM cert and HTTPS listener path stays out of scope.

2. **Health check defaults baked in** — target groups default to:
   - `HealthCheckProtocol=HTTP`
   - `HealthCheckPort=8080`
   - `HealthCheckPath=/info/health`
   - Default interval / threshold / timeout (30s / 5 / 5s — boto3 defaults)
   
   Callers can override via the CLI; the Fargate target-group helper hardcodes
   these for the vault-app contract.

3. **ALB only, no NLB** — module is named `alb` (not `elbv2`). If NLB support
   is ever added it goes alongside as a sibling module (`aws/nlb/`). No
   over-engineering for that case in v1.

# Cost & lifecycle

## AWS lifecycle facts

| What                  | Reality                                                                                       |
|-----------------------|-----------------------------------------------------------------------------------------------|
| Start/stop API        | Doesn't exist. ALBs only have `create` and `delete`. No paused state.                         |
| Per-day create limit  | None published. API rate limits exist (~5/sec sustained on elbv2 `CreateLoadBalancer`) but no daily cap. |
| Account-level limit   | Soft: **50 ALBs per region per account** (raisable via support ticket).                       |
| Create → Active time  | **~3-5 minutes** for the ALB to reach `active`. Slower than Fargate task startup.             |
| Delete → Gone time    | Near-instant from your side; AWS reclaims IPs / DNS over ~60s.                                |
| DNS propagation       | ALB DNS name uses 60s TTL multi-A records; Route53 alias to ALB is instant + free.            |
| Target group churn    | No limit on `register_targets`/`deregister_targets`. Targets become healthy in ~30-60s (default health-check timing). |

## Pricing (eu-west-2, retail, late-2025)

| Resource                          | Unit            | Price                  | Notes                                                |
|-----------------------------------|-----------------|------------------------|------------------------------------------------------|
| Application LB                    | per ALB-hour    | **$0.02475/hr** (~$18/mo) | Charged the moment the ALB exists, idle or busy.  |
| LCU (Load Balancer Capacity Unit) | per LCU-hour    | **$0.008/LCU-hr**      | Variable — see LCU dimensions below.                 |
| Target Group                      | —               | **Free**               | Zero charge for the TG itself.                       |
| Listener                          | —               | **Free**               | Zero charge — same for listener rules.               |
| Health checks                     | —               | **Free**               | Probes and `describe_target_health` API calls.       |
| ACM cert (public)                 | —               | **Free** with ALB      | Out of scope for v1 anyway.                          |
| Route53 A-alias → ALB             | —               | **Free**               | Alias to AWS resource isn't metered like CNAMEs.     |
| Data transfer out to internet     | per GB          | $0.09/GB (first 10 TB) | Same as direct task egress — not ALB-specific.       |
| Cross-AZ data transfer            | per GB          | $0.01/GB in + $0.01/GB out | Triggered when ALB routes to a target in a different AZ than entry. |

### LCU breakdown

An LCU is the **max** across four dimensions, billed per hour. You pay for the
highest of these, summed across the hour:

| Dimension          | 1 LCU covers                |
|--------------------|-----------------------------|
| New connections    | 25 new connections / second |
| Active connections | 3,000 active conn / minute  |
| Processed bytes    | 1 GB / hour                 |
| Rule evaluations   | 1,000 / second              |

For an idle dev-vault ALB with one user: well under 1 LCU/hour.

## Real-world cost estimate

Single persistent ALB serving up to 5 ephemeral vault target groups, light dev
traffic:

| Line item                          | Monthly (eu-west-2, retail) |
|------------------------------------|-----------------------------|
| ALB base (1 × $0.02475 × 730h)     | **$18.07**                  |
| LCU (~0.1 LCU avg × 730h × $0.008) | **$0.58**                   |
| Target groups (any count)          | $0                          |
| Listeners (HTTP)                   | $0                          |
| Route53 hosted zone                | $0.50                       |
| Route53 A-alias queries            | $0                          |
| Cross-AZ traffic (light)           | <$1                         |
| **Total**                          | **~$20/month**              |

## Lifecycle pattern recommendation

For ephemeral vault containers, **do not create/delete an ALB per session** —
the ALB takes 3-5 minutes to come up and per-hour billing applies regardless
of how briefly it runs. Instead:

- **One persistent ALB** (long-lived, idempotent provisioning via tag-matching,
  same pattern as `VPC__Stack__Provisioner`).
- **One target group per vault session** (free, instant create).
- **Register/deregister tasks** on the target group as sessions start/stop.

`ALB__Stack__Provisioner` should mirror `VPC__Stack__Provisioner`:
re-runs are no-ops when the ALB tag matches; only `destroy` mode tears down.

Per-session create/delete only makes sense for < ~1 session/day. For anything
more frequent, persistent ALB + ephemeral target groups wins on both cost
(amortised) and latency (no 3-5 min startup).
