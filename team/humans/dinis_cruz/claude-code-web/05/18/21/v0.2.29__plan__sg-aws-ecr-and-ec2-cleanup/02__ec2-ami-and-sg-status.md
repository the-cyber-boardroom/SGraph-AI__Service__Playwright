---
title: "Status — sg aws ec2 (AMI + SG management)"
date: 2026-05-18
author: claude (claude-opus-4-7)
status: AUDIT — these surfaces do NOT exist yet
related:
  - sgraph_ai_service_playwright__cli/aws/ec2/cli/Cli__EC2.py
  - sgraph_ai_service_playwright__cli/aws/ec2/service/EC2__AWS__Client.py
---

# Audit — what's already in `sg aws ec2`, and what's missing for AMI + SG cleanup

## What exists today

`sg aws ec2` covers **instances only**:

| Command          | Op                                                          |
|------------------|-------------------------------------------------------------|
| `list`           | describe_instances (filtered by state/prefix/tag)           |
| `describe`       | describe_instances on one id-or-name                        |
| `ssh-info`       | builds an ssh hint string                                   |
| `tags`           | add/remove tags                                              |
| `instance-types` | describe_instance_types                                      |
| `pricing`        | pricing API lookup                                          |
| `create`         | run_instances                                                |
| `start` / `stop` / `terminate` | start_instances / stop_instances / terminate_instances |
| `wait`           | poll instance state                                          |

Schemas and primitives for AMI (`Safe_Str__EC2__AMI_Id`) and SG (`Safe_Str__EC2__SG_Id`, `Schema__EC2__Security_Group__Ref`) already exist — they're populated when listing instances — but there is **no surface for listing or deleting AMIs or security groups directly**.

So: **no, this section does not currently let you list and clean up AMIs or SGs.** It needs a new slice.

## Proposed `sg aws ec2 ami` surface

```
sg aws ec2 ami list   [--owner self|amazon|all] [--name <substring>] [--json]
sg aws ec2 ami show   <ami-id>                                                    # name, owner, snapshots, attached instances, size
sg aws ec2 ami orphans [--older 30d]                                              # AMIs owned by self with NO running/stopped instances pointing at them
sg aws ec2 ami delete <ami-id> [--with-snapshots] [--yes]                         # deregister + (optionally) delete backing snapshots
```

Key safety choice: `delete` **does not** drop the snapshots by default — separate flag, so you can deregister-now-delete-snapshots-later. `orphans` is the cleanup-friendly killer: list all your AMIs that no instance is using.

## Proposed `sg aws ec2 sg` surface

```
sg aws ec2 sg list    [--vpc <vpc-id>] [--name <substring>] [--json]
sg aws ec2 sg show    <sg-id-or-name>                                             # ingress, egress, attached resources (ENIs, instances)
sg aws ec2 sg orphans [--vpc <vpc-id>]                                            # SGs not attached to any ENI, instance, ELB, RDS, Lambda
sg aws ec2 sg delete  <sg-id-or-name> [--yes]                                     # fails fast if anything still references it (AWS does this for us)
sg aws ec2 sg rules   <sg-id-or-name> [--json]                                    # ingress/egress pretty-printed
```

`orphans` is the cleanup workflow: AWS does not let you delete an SG that's still attached, so the easy mistakes (deleting an in-use SG) are impossible. The risk is the inverse — leaving stale SGs around forever.

## Architecture

Two new sub-packages under the existing `aws/ec2/`:

```
sgraph_ai_service_playwright__cli/aws/ec2/
├── cli/
│   ├── Cli__EC2.py              # existing instance commands (untouched)
│   ├── Cli__EC2__Ami.py         # NEW — typer subapp, mounted under ec2 as 'ami'
│   └── Cli__EC2__Sg.py          # NEW — typer subapp, mounted under ec2 as 'sg'
├── service/
│   ├── EC2__AWS__Client.py      # existing — extend with describe_images, deregister_image,
│   │                              describe_security_groups, delete_security_group,
│   │                              describe_snapshots, delete_snapshot
│   ├── EC2__AMI__Resolver.py    # NEW — pure: maps "ami-id-or-name" → ami-id (mirrors Lambda__Name__Resolver)
│   └── EC2__SG__Resolver.py     # NEW — pure: maps "sg-id-or-name" → sg-id, dedupes by VPC
├── schemas/
│   ├── Schema__EC2__AMI.py      # NEW
│   ├── Schema__EC2__Snapshot.py # NEW
│   └── Schema__EC2__Security_Group.py  # NEW (full schema; current Schema__EC2__Security_Group__Ref is a ref-only summary)
└── collections/
    ├── List__Schema__EC2__AMI.py
    └── List__Schema__EC2__Security_Group.py
```

Mounting in the existing `Cli__EC2.py`:

```python
from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Ami import app as ami_app
from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Sg  import app as sg_app
app.add_typer(ami_app, name='ami')
app.add_typer(sg_app , name='sg')
```

So the existing `sg aws ec2 list/describe/...` keeps working unchanged, and `sg aws ec2 ami list` / `sg aws ec2 sg orphans` slot in next to them.

## Phasing

1. **P0** — `ami list`, `ami show`, `sg list`, `sg show`, `sg rules` (pure reads).
2. **P0** — `ami orphans`, `sg orphans` (reads + in-memory join: list AMIs/SGs, cross-reference with instances/ENIs to find unused).
3. **P1** — `ami delete`, `sg delete` (mutation-gated on `SG_AWS__EC2__ALLOW_MUTATIONS=1`, same gate the existing `terminate` uses).
4. **P2** — bulk cleanup: `ami prune --orphans --older 30d --yes` (depends on P0 orphans + P1 delete).

## Open questions

- "Attached resources" for SG show: ENIs are easy (single API call). ELB, RDS, Lambda associations require cross-service calls — recommend ENI-only for P0 and call it out in the help text, with `--deep` flag in P2 for the full sweep.
- Snapshot ownership: an AMI's snapshots may be shared. `ami delete --with-snapshots` should refuse (or warn loudly) when any snapshot's owner is not the current account.

Estimated work: P0 = ~1 day (~10 commands, ~6 schemas, ~30 tests). P1 = ~half-day. P2 = ~half-day.
