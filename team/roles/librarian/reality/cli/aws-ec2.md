---
title: "Reality — cli/aws-ec2"
file: aws-ec2.md
author: Dev (Claude)
date: 2026-05-17
status: LIVE — implemented in v0.2.29 Slice B; updated v0.2.30 Open-2 (typed primitives)
parent: cli/index.md
---

# cli/aws-ec2 — `sg aws ec2` Surface

**Last updated:** 2026-05-17 (v0.2.30 Open-2 — typed primitives)
**Slice:** v0.2.29 Slice B; v0.2.30 Open-2
**Branch:** `claude/aws-primitives-support-uNnZY`

---

## EXISTS (code-verified, 2026-05-17)

### Location

`sgraph_ai_service_playwright__cli/aws/ec2/`

Registered in `Cli__Aws` as `app.add_typer(ec2_app, name='ec2')`.

### CLI verbs

| Verb | Mutating | Gate required |
|------|----------|---------------|
| `list [--state] [--prefix] [--tag K=V] [--json]` | no | — |
| `describe <id-or-name> [--json]` | no | — |
| `ssh-info <id-or-name>` | no | — |
| `tags <id-or-name> [--json]` | no | — |
| `tags <id-or-name> --add K=V [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `tags <id-or-name> --remove K [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `tags <id-or-name> --clear [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `instance-types [--family] [--json]` | no | — |
| `pricing <type> [--region] [--json]` | no | — |
| `create --name --instance-type --ami [opts] [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `start <id-or-name> [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `stop <id-or-name> [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `terminate <id-or-name> [--yes]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `wait <id-or-name> --state STATE [--timeout 300]` | no | — |

### Production files

| File | Role |
|------|------|
| `cli/Cli__EC2.py` | All 11 Typer commands |
| `service/EC2__AWS__Client.py` | boto3 boundary: list / describe / create / start / stop / terminate / tags |
| `service/EC2__Name__Resolver.py` | `<id-or-name>` → concrete instance ID; ambiguity error |
| `service/EC2__Instance__Wait.py` | Polling wait with 2→5→10→15s backoff; default 300s timeout |
| `service/EC2__Pricing__Client.py` | AWS Pricing API (pinned us-east-1) |
| `schemas/Schema__EC2__Instance.py` | Summary schema (list output) |
| `schemas/Schema__EC2__Instance__Detail.py` | Full detail schema (describe output) |
| `schemas/Schema__EC2__Pricing.py` | Pricing schema |
| `schemas/Schema__EC2__Create__Request.py` | Create request parameters |
| `enums/Enum__EC2__Instance__State.py` | pending, running, stopping, stopped, shutting-down, terminated, unknown |
| `primitives/Safe_Str__EC2__Instance_Id.py` | `i-[0-9a-f]{8,17}` |
| `primitives/Safe_Str__EC2__AMI_Id.py` | AMI ID or alias string |
| `primitives/Safe_Str__EC2__Instance__Type.py` | Instance type (e.g. `t3.micro`) |
| `collections/List__Schema__EC2__Instance.py` | Typed list for list output |
| `schemas/Schema__EC2__Security_Group__Ref.py` | `group_id: Safe_Str__EC2__SG_Id`, `group_name: Safe_Str__AWS__Tag_Value` |
| `schemas/Schema__EC2__Block_Device__Mapping.py` | `device_name`, `volume_id`, `volume_size: Safe_Int__EC2__GiB`, `delete_on_termination: bool`, `status` |
| `collections/Dict__EC2__Tag.py` | `Type_Safe__Dict[Safe_Str__AWS__Tag_Key, Safe_Str__AWS__Tag_Value]` |
| `collections/List__Schema__EC2__Security_Group__Ref.py` | `Type_Safe__List[Schema__EC2__Security_Group__Ref]` |
| `collections/List__Schema__EC2__Block_Device__Mapping.py` | `Type_Safe__List[Schema__EC2__Block_Device__Mapping]` |
| `primitives/Safe_Str__EC2__Name.py` | REPLACE — printable ASCII, `allow_empty` |
| `primitives/Safe_Str__EC2__IP_Address.py` | REPLACE — digits, colon, dot (IPv4 + IPv6) |
| `primitives/Safe_Str__EC2__DNS_Name.py` | REPLACE — `[a-zA-Z0-9.\-]` |
| `primitives/Safe_Str__EC2__Launch_Time.py` | REPLACE — printable ASCII (ISO-8601) |
| `primitives/Safe_Str__EC2__Key_Pair.py` | REPLACE — `[A-Za-z0-9_\-]` |
| `primitives/Safe_Str__EC2__VPC_Id.py` | REPLACE — `[a-z0-9\-]` |
| `primitives/Safe_Str__EC2__Subnet_Id.py` | REPLACE — `[a-z0-9\-]` |
| `primitives/Safe_Str__EC2__Architecture.py` | REPLACE — `[a-z0-9_]` |
| `primitives/Safe_Str__EC2__Platform.py` | REPLACE — `[A-Za-z0-9 \-_.]` |
| `primitives/Safe_Str__EC2__Root_Device_Type.py` | REPLACE — `[a-z\-]` (ebs / instance-store) |
| `primitives/Safe_Str__EC2__SG_Id.py` | REPLACE — `[a-z0-9\-]` |
| `primitives/Safe_Str__EC2__Device_Name.py` | REPLACE — `[a-z0-9/\-]` |
| `primitives/Safe_Str__EC2__Volume_Id.py` | REPLACE — `[a-z0-9\-]` |
| `primitives/Safe_Str__EC2__BDM_Status.py` | REPLACE — `[A-Za-z0-9\-_]` |
| `primitives/Safe_Str__EC2__Price.py` | REPLACE — `[0-9.]` |
| `primitives/Safe_Str__EC2__Currency.py` | REPLACE — `[A-Z]` |
| `primitives/Safe_Str__EC2__OS.py` | REPLACE — `[A-Za-z0-9 \-_.]` |
| `primitives/Safe_Str__EC2__User_Data.py` | REPLACE — printable ASCII + tab/LF/CR |
| `primitives/Safe_Str__EC2__SG_Id_List.py` | REPLACE — comma-separated SG IDs |
| `primitives/Safe_Int__EC2__GiB.py` | Safe_Int, min=0 max=65536 |

### Tests

Location: `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/`

| Test file | Coverage |
|-----------|----------|
| `cli/test_Cli__EC2.py` | 13 cases: list empty/populated, filter by state, describe, tags view, mutation gate for create/start/stop/terminate, create with gate set, instance-types, wait invalid state |
| `service/test_EC2__AWS__Client.py` | 11 cases: list, describe, create, start/stop, terminate, tags, instance-types, family filter |
| `service/test_EC2__Name__Resolver.py` | 5 cases: ID pass-through, name resolution, missing error, ambiguity error, prefix match |
| `enums/test_Enum__EC2__Instance__State.py` | 4 cases: all values, str coercion, from-string, invalid raises |
| `primitives/test_EC2__Primitives.py` | 10 cases: instance ID, AMI ID, instance type |
| `schemas/test_EC2__Schemas.py` | 7 cases: defaults, field types, pricing |

Total: 50 unit tests, all green.

### In-memory test helper

`tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/service/EC2__AWS__Client__In_Memory.py`

`EC2__AWS__Client__In_Memory` — real subclass with dict-backed fake boto3 client. No mocks, no patches.
Provides `seed_instance(...)` helper for populating test state.

### v0.2.30 Open-2 — escape-hatch replacement

`Schema__EC2__Instance__Detail` previously carried three JSON-serialised string escape hatches:
- `tags_raw: str` → replaced with `tags: Dict__EC2__Tag`
- `security_groups_raw: str` → replaced with `security_groups: List__Schema__EC2__Security_Group__Ref`
- `block_devices_raw: str` → replaced with `block_devices: List__Schema__EC2__Block_Device__Mapping`

`EC2__AWS__Client._parse_detail` now builds these typed collections directly from boto3 response dicts.
`Cli__EC2.ec2_describe` now iterates the typed collections instead of calling `json.loads`.
`Schema__EC2__Create__Request.extra_tags_raw: str` replaced with `extra_tags: Dict__EC2__Tag`.
`Schema__EC2__Pricing` fields `currency` and `os` had hard-coded string defaults removed (both now empty by default).
`Schema__EC2__Instance` fields `name`, `public_ip`, `private_ip`, `launch_time`, `key_name` → typed.

All 20 new EC2 primitives and the `Safe_Int__EC2__GiB` use REPLACE mode with `allow_empty = True`
so boto3 values are never rejected and no existing string operations break.

### Coexistence with legacy `__cli/ec2/`

The legacy `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py` still owns:
- `ecr_registry_host()`, `aws_account_id()`, `aws_region()`
- IAM profile management helpers
- AMI lifecycle methods for the Playwright image

These are consumed by `Docker__Service`, `Firefox__Service`, and `scripts/doctor.py`. The new `aws/ec2/` surface does **not** duplicate those helpers. A v0.2.30 hygiene pass will consolidate both locations.

---

## NOT implemented in this slice

- `EC2__Ami__Resolver` (alias → AMI ID resolution) — `create` currently accepts a raw AMI ID or alias string passed directly to the API
- Integration tests requiring live AWS credentials (gated on `SG_AWS__EC2__INTEGRATION=1`)
- `scripts/provision_ec2.py` thin-wrapper refactor (the script was deleted ahead of Slice B per the dev pack note)
- Promotion of `Elastic__AWS__Client` EC2-shaped helpers (security-group naming) — those remain in `elastic/service/` and will be promoted in v0.2.30

---

## See also

- User guide: [`library/docs/cli/sg-aws/10__ec2.md`](../../../../library/docs/cli/sg-aws/10__ec2.md)
- Brief: [`library/dev_packs/v0.2.29__sg-aws-ec2/README.md`](../../../../library/dev_packs/v0.2.29__sg-aws-ec2/README.md)
- Legacy reality doc: [`cli/ec2.md`](ec2.md) — FastAPI routes (retired on 2026-05-17) + Lambda deploy
- Parent: [`cli/index.md`](index.md)
