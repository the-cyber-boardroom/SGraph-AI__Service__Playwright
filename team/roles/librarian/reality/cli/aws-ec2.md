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

## v0.2.33 additions (Slice 0b) — `sg aws ec2 eni`

New sub-command tree under `sg aws ec2`:

| Command | What it does |
|---------|-------------|
| `sg aws ec2 eni list [--sg sg-xxx] [--vpc vpc-yyy] [--json]` | List network interfaces, optionally filtered by security group or VPC |
| `sg aws ec2 eni show <eni-id> [--json]` | Describe one ENI by ID |

New files:

| File | Role |
|------|------|
| `aws/ec2/cli/Cli__EC2__Eni.py` | Typer sub-app with `list` and `show` commands |
| `aws/ec2/schemas/Schema__EC2__ENI.py` | `eni_id`, `subnet_id`, `vpc_id`, `public_ip`, `private_ip`, `attachment_instance_id`, `attachment_status`, `security_group_ids` |
| `aws/ec2/primitives/Safe_Str__EC2__ENI_Id.py` | ENI ID primitive |

Used by `Vault_App__Fargate__Starter` to resolve the public IP after `run_task`
returns an ENI attachment.

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/eni/`

---

## v0.2.34 additions (VPC stack Slice 1 of 3) — read-only `vpc`, `subnet`, `igw`, `route-table`

Slice 1 — read-only foundation. Mutations landed in Slice 2 (below);
the composite `vpc create-stack` provisioning command lands in Slice 3.

New sub-command trees under `sg aws ec2`:

| Command | What it does |
|---------|-------------|
| `sg aws ec2 vpc list [--vpc-substring TEXT] [--json]` | List VPCs (client-side id substring filter) |
| `sg aws ec2 vpc show <vpc-id> [--json]` | Describe one VPC by ID |
| `sg aws ec2 subnet list [--vpc <vpc-id>] [--az <az>] [--json]` | List subnets filtered by VPC and/or AZ |
| `sg aws ec2 subnet show <subnet-id> [--json]` | Describe one subnet by ID |
| `sg aws ec2 igw list [--vpc <vpc-id>] [--json]` | List Internet Gateways filtered by attached VPC |
| `sg aws ec2 igw show <igw-id> [--json]` | Describe one IGW by ID |
| `sg aws ec2 route-table list [--vpc <vpc-id>] [--json]` | List Route Tables filtered by VPC |
| `sg aws ec2 route-table show <rtb-id> [--json]` | Describe one Route Table (routes + associations) |

All 8 commands are read-only — no mutation gate required.

New files:

| File | Role |
|------|------|
| `aws/ec2/cli/Cli__EC2__Vpc.py` | Typer sub-app: `list`, `show` |
| `aws/ec2/cli/Cli__EC2__Subnet.py` | Typer sub-app: `list`, `show` |
| `aws/ec2/cli/Cli__EC2__Igw.py` | Typer sub-app: `list`, `show` |
| `aws/ec2/cli/Cli__EC2__Route_Table.py` | Typer sub-app: `list`, `show` (renders routes + associations sub-tables) |
| `aws/ec2/schemas/Schema__EC2__VPC.py` | `vpc_id`, `cidr_block`, `is_default`, `state`, `dhcp_options_id`, `instance_tenancy`, `tags` |
| `aws/ec2/schemas/Schema__EC2__Subnet.py` | `subnet_id`, `vpc_id`, `cidr_block`, `availability_zone`, `availability_zone_id`, `available_ip_count`, `map_public_ip_on_launch`, `state`, `tags` |
| `aws/ec2/schemas/Schema__EC2__Internet_Gateway.py` | `igw_id`, `vpc_id`, `state`, `tags` |
| `aws/ec2/schemas/Schema__EC2__Route.py` | `destination_cidr`, `gateway_id`, `state`, `origin` |
| `aws/ec2/schemas/Schema__EC2__Route_Table.py` | `route_table_id`, `vpc_id`, `routes`, `associations`, `tags` |
| `aws/ec2/schemas/Schema__EC2__Route_Table_Association.py` | `association_id`, `route_table_id`, `subnet_id`, `main` |
| `aws/ec2/primitives/Safe_Str__EC2__IGW_Id.py` | MATCH — `^igw-[a-f0-9]+$` |
| `aws/ec2/primitives/Safe_Str__EC2__Route_Table_Id.py` | MATCH — `^rtb-[a-f0-9]+$` |
| `aws/ec2/primitives/Safe_Str__EC2__CIDR.py` | MATCH — IPv4 dotted-quad/prefix |
| `aws/ec2/primitives/Safe_Str__EC2__AZ.py` | MATCH — `^[a-z]{2}-[a-z]+-\d[a-z]?$` |
| `aws/ec2/collections/List__Schema__EC2__VPC.py` | Typed list |
| `aws/ec2/collections/List__Schema__EC2__Subnet.py` | Typed list |
| `aws/ec2/collections/List__Schema__EC2__Internet_Gateway.py` | Typed list |
| `aws/ec2/collections/List__Schema__EC2__Route_Table.py` | Typed list |
| `aws/ec2/collections/List__Schema__EC2__Route.py` | Typed list (routes inside a route table) |
| `aws/ec2/collections/List__Schema__EC2__Route_Table_Association.py` | Typed list |

`EC2__AWS__Client` gained 8 read-only methods: `list_vpcs`, `describe_vpc`,
`list_subnets`, `describe_subnet`, `list_internet_gateways`,
`describe_internet_gateway`, `list_route_tables`, `describe_route_table`. Each
uses the boto3 paginator pattern + `ClientError` → `None` fall-through for the
relevant `InvalidXID.NotFound` codes.

`EC2__AWS__Client__In_Memory` extended with `seed_vpc`, `seed_subnet`,
`seed_igw`, `seed_route_table`. The fake boto3 client now serves
`describe_vpcs / describe_subnets / describe_internet_gateways /
describe_route_tables` with filter support (`vpc-id`, `availability-zone`,
`attachment.vpc-id`, `tag:*`).

Tests:

- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/vpc/` — service + CLI
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/subnet/` — service + CLI
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/igw/` — service + CLI
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/route_table/` — service + CLI
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/primitives/test_EC2__Primitives__Network.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/schemas/test_EC2__Schemas__Network.py`

Total: 112 new tests added.

---

## v0.2.34 additions (VPC stack Slice 2 of 3) — mutation surface

Slice 2 — create / delete / modify CLI commands and client methods for each
EC2 networking domain, plus relational operations (IGW attach/detach,
route-table associate/disassociate, route add/remove). All mutations gated
behind `SG_AWS__EC2__ALLOW_MUTATIONS=1`. **No composite stack provisioner
yet — that's Slice 3.**

### CLI surface (new mutations)

| Command | Mutating | Gate |
|---------|----------|------|
| `sg aws ec2 vpc create [--cidr 10.0.0.0/16] [--name] [--enable-dns] [--enable-dns-hostnames] [--yes] [--json]` | yes | `SG_AWS__EC2__ALLOW_MUTATIONS=1` |
| `sg aws ec2 vpc delete <vpc-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 vpc modify-attr <vpc-id> [--enable-dns/--no-enable-dns] [--enable-dns-hostnames/--no-enable-dns-hostnames] [--json]` | yes | same |
| `sg aws ec2 subnet create --vpc <vpc-id> --cidr <cidr> [--az] [--name] [--public] [--yes] [--json]` | yes | same |
| `sg aws ec2 subnet delete <subnet-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 subnet modify-attr <subnet-id> [--public/--no-public] [--json]` | yes | same |
| `sg aws ec2 igw create [--name] [--yes] [--json]` | yes | same |
| `sg aws ec2 igw delete <igw-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 igw attach <igw-id> --vpc <vpc-id> [--json]` | yes | same |
| `sg aws ec2 igw detach <igw-id> --vpc <vpc-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 route-table create --vpc <vpc-id> [--name] [--yes] [--json]` | yes | same |
| `sg aws ec2 route-table delete <rtb-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 route-table add-route <rtb-id> --cidr <cidr> [--igw \| --nat \| --eni] [--json]` | yes | same |
| `sg aws ec2 route-table remove-route <rtb-id> --cidr <cidr> [--yes] [--json]` | yes | same |
| `sg aws ec2 route-table associate <rtb-id> --subnet <subnet-id> [--json]` | yes | same |
| `sg aws ec2 route-table disassociate <association-id> [--yes] [--json]` | yes | same |
| `sg aws ec2 sg create --name --vpc --description [--json]` | yes | same |
| `sg aws ec2 sg add-ingress <sg-id> --protocol --from --to [--cidr \| --source-sg] [--json]` | yes | same |
| `sg aws ec2 sg add-egress <sg-id> --protocol --from --to [--cidr \| --source-sg] [--json]` | yes | same |
| `sg aws ec2 sg remove-ingress <sg-id> --protocol --from --to [--cidr] [--yes] [--json]` | yes | same |
| `sg aws ec2 sg remove-egress <sg-id> --protocol --from --to [--cidr] [--yes] [--json]` | yes | same |

### Client mutation methods (new on `EC2__AWS__Client`)

- VPC: `create_vpc`, `delete_vpc`, `modify_vpc_attribute`
- Subnet: `create_subnet`, `delete_subnet`, `modify_subnet_attribute`
- IGW: `create_internet_gateway`, `delete_internet_gateway`, `attach_internet_gateway`, `detach_internet_gateway`
- Route Table: `create_route_table`, `delete_route_table`, `associate_route_table`, `disassociate_route_table`, `create_route`, `delete_route`
- SG: `create_security_group`, `authorize_security_group_ingress` / `authorize_security_group_egress`, `revoke_security_group_ingress` / `revoke_security_group_egress`

All are idempotent-friendly: not-found / already-applied → `False`; ClientError reasons (`InvalidVpcID.NotFound`, `Resource.AlreadyAssociated`, `Gateway.NotAttached`, `InvalidPermission.Duplicate`, `InvalidPermission.NotFound`, etc.) are translated to bool returns rather than raised. `create_route` raises `ValueError` when zero or multiple targets are specified — programmer-bug detection, not an AWS error.

### In-memory client extensions

`EC2__AWS__Client__In_Memory` (the test seam) extended with fake-boto3 methods for every mutation above. IDs are produced from a deterministic per-prefix counter (`vpc-00000001`, `subnet-00000001`, …), enabling stable assertions in tests. Boto3-style `TagSpecifications` are parsed into the same `tags` dict the seed helpers accept.

### Tests added in this slice (Slice 2)

- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/vpc/service/test_EC2__AWS__Client__VPC__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/vpc/cli/test_Cli__EC2__Vpc__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/subnet/service/test_EC2__AWS__Client__Subnet__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/subnet/cli/test_Cli__EC2__Subnet__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/igw/service/test_EC2__AWS__Client__IGW__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/igw/cli/test_Cli__EC2__Igw__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/route_table/service/test_EC2__AWS__Client__Route_Table__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/route_table/cli/test_Cli__EC2__Route_Table__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/sg/service/test_EC2__AWS__Client__SG__mutations.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/sg/cli/test_Cli__EC2__Sg__slice2.py`

Total: 143 new tests added in Slice 2.

---

## NOT implemented in this slice

- `EC2__Ami__Resolver` (alias → AMI ID resolution) — `create` currently accepts a raw AMI ID or alias string passed directly to the API
- Integration tests requiring live AWS credentials (gated on `SG_AWS__EC2__INTEGRATION=1`)
- `scripts/provision_ec2.py` thin-wrapper refactor (the script was deleted ahead of Slice B per the dev pack note)
- Promotion of `Elastic__AWS__Client` EC2-shaped helpers (security-group naming) — those remain in `elastic/service/` and will be promoted in v0.2.30
- **VPC stack Slice 3** — composite `sg aws ec2 vpc create-stack / delete-stack` orchestration and vault-app auto-resolve — PROPOSED, does not exist yet

---

## See also

- User guide: [`library/docs/cli/sg-aws/10__ec2.md`](../../../../../library/docs/cli/sg-aws/10__ec2.md)
- Brief: [`library/dev_packs/v0.2.29__sg-aws-ec2/README.md`](../../../../../library/dev_packs/v0.2.29__sg-aws-ec2/README.md)
- Legacy reality doc: [`cli/ec2.md`](ec2.md) — FastAPI routes (retired on 2026-05-17) + Lambda deploy
- Parent: [`cli/index.md`](index.md)
