---
title: "Reality — cli/aws-ec2"
file: aws-ec2.md
author: Dev (Claude)
date: 2026-05-17
status: LIVE — implemented in v0.2.29 Slice B
parent: cli/index.md
---

# cli/aws-ec2 — `sg aws ec2` Surface

**Last updated:** 2026-05-17
**Slice:** v0.2.29 Slice B
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

- User guide: [`library/docs/cli/sg-aws/10__ec2.md`](../../../../../library/docs/cli/sg-aws/10__ec2.md)
- Brief: [`library/dev_packs/v0.2.29__sg-aws-ec2/README.md`](../../../../../library/dev_packs/v0.2.29__sg-aws-ec2/README.md)
- Legacy reality doc: [`cli/ec2.md`](ec2.md) — FastAPI routes (retired on 2026-05-17) + Lambda deploy
- Parent: [`cli/index.md`](index.md)
