---
title: AWS ALB CRUD — `sg aws elbv2` module
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
sgraph_ai_service_playwright__cli/aws/elbv2/
├── primitives/      # Safe_Str__ELBv2__{LB_Arn,LB_Name,TG_Arn,TG_Name,Listener_Arn,Protocol,...}
├── enums/           # Enum__ELBv2__{LB_State,LB_Scheme,Target_Health,Protocol,Target_Type}
├── schemas/         # Schema__ELBv2__{Load_Balancer,Target_Group,Listener,Health_Check,...}
├── collections/     # List__Schema__ELBv2__*
├── service/         # ELBv2__AWS__Client.py + (later) ALB__Stack__Provisioner.py
└── cli/             # Cli__ELBv2.py + per-resource verb files
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
app.add_typer(elbv2_app, name='elbv2')
```

# Integration touchpoints (zero code changes outside `aws/elbv2/`)

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
| Collections| ~6 `List__Schema__ELBv2__*`                                                     |
| Client     | `ELBv2__AWS__Client` with `list_*` + `describe_*` + `describe_target_health` (~400 LOC) |
| In-memory  | `ELBv2__AWS__Client__In_Memory` (~400 LOC)                                      |
| CLI        | `lb list/show`, `tg list/show`, `listener list/show`                            |
| Tests      | ~15                                                                             |
| Total      | ~25-30 new files                                                                |

## Slice 2 — Mutation surface

| Item            | Count / detail                                                             |
|-----------------|----------------------------------------------------------------------------|
| Client mutations| `create/delete/modify` for all three resource types; `register_targets`, `deregister_targets`; tag add/remove (~350 LOC) |
| Request schemas | ~3 (`Schema__ELBv2__{LB,TG,Listener}__Create__Request`)                    |
| CLI verbs       | `Cli__ELBv2__LB.py`, `Cli__ELBv2__TG.py`, `Cli__ELBv2__Listener.py` (create/delete/register/deregister) |
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
| CLI               | `Cli__ELBv2__Stack.py` with `provision/destroy/describe`                                    |
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

- **After Slice 1**: read-only `sg aws elbv2 lb/tg/listener list/show` against a
  real account — useful for inventory and debugging existing ALBs.
- **After Slice 2**: one-off `sg aws elbv2 lb create`, `tg create`, `register-targets`
  — usable but requires the operator to compose the steps manually.
- **After Slice 3**: single-command `sg aws elbv2 stack provision` + Fargate
  task target-registration — the "spin up Fargate vault → register with ALB"
  end-to-end path.

# Open questions (for reviewer)

1. **HTTPS / ACM cert**: do we want Slice 2 (or 3) to handle `Protocol=HTTPS`
   listeners with an existing ACM cert ARN? ACM domain already exists in this
   repo (`aws/acm/`). Listener creation just needs `Certificates=[{CertificateArn: ...}]`.
   Recommend: support both HTTP and HTTPS listeners in Slice 2, with HTTPS as
   the default when an ACM cert ARN is passed.

2. **Health check defaults**: ALB target groups default to `HTTP /` on port
   80 with a 30s interval. For the vault-app use case the path is
   `/info/health`. Bake that default into the Fargate-target-group helper, or
   require the caller to pass it?

3. **NLB / Network Load Balancers**: `elbv2` also covers NLBs. v1 scope is
   ALB-only — but the module name `elbv2` lets us add NLB later without
   restructuring. Confirm we want to keep that door open.
