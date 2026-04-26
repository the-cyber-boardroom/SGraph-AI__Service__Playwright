# Phase A · Step 3d — SG + AMI helpers

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 3c (IAM helpers).

---

## What shipped

Added to `cli/ec2/service/Ec2__AWS__Client.py`:

**9 constants** — `SG__NAME`, `SG__DESCRIPTION`, `EC2__AMI_OWNER_AMAZON`, `EC2__AMI_NAME_AL2023`, `EC2__PLAYWRIGHT_PORT`, `EC2__SIDECAR_ADMIN_PORT`, `EC2__BROWSER_INTERNAL_PORT`, `SG_INGRESS_PORTS` (a tuple of the three ports), `TAG__AMI_STATUS_KEY`.

**6 class methods** on `Ec2__AWS__Client`:

- `ensure_security_group()` — idempotent SG create + ingress authorisation for the canonical port set
- `latest_al2023_ami_id()` — most recent AL2023 base AMI by `CreationDate`
- `create_ami(instance_id, name)` — creates an AMI with `sg:ami-status='untested'` tag
- `wait_ami_available(ami_id, timeout=900)` — poll until `available` / `failed` / timeout
- `tag_ami(ami_id, status)` — set `sg:ami-status` (untested / healthy / unhealthy)
- `latest_healthy_ami()` — most recently created healthy sg-playwright AMI

**Refactored `provision_ec2.py`:**
- 9 constant definitions deleted; alias-imports added at top
- 6 function definitions deleted; thin wrapper functions kept matching the old `(ec2: EC2, ...)` signatures so the typer commands work unchanged
- Wrapper functions delegate to the module-level `_AWS = Ec2__AWS__Client()` instance from step 3a

**Refactored `Ec2__Service`:**
- `build_instance_info()` — port constants now come from `Ec2__AWS__Client` instead of the `from scripts.provision_ec2 import ...` block. The remaining lazy import shrinks to 4 tag-name constants.

## Bug fix surfaced

`SG__DESCRIPTION` previously contained an em-dash (`—`, U+2014) which AWS rejects as a non-ASCII `GroupDescription`. The new `test__sg_description_is_ascii_only` test caught it. Replaced with a hyphen. Same precedent existed in the Elastic SG description; this brings the Playwright SG description into compliance.

## Tests

14 new unit tests:

| Group | Tests |
|---|---|
| `ensure_security_group` (3 tests) | creates when missing / reuses existing / ingress failure swallowed |
| AMI lifecycle (6 tests) | `latest_al2023_ami_id` ordering / no-AMI raise; `create_ami` tag shape; `tag_ami` overwrite; `latest_healthy_ami` ordering / no-match returns None |
| `test_sg_and_ami_constants` (5 tests) | SG name doesn't start with `sg-`; description ASCII-only; ingress ports canonical; AMI name filter targets AL2023; AMI status tag namespaced |

The fake EC2 boto3 client (`_Fake_Boto3_Client`) is a real in-memory subclass — no mocks. Records every call; tests assert on the call shape (kwargs, tag specifications, filter values).

## Test outcome

| Suite | Before (3c) | After (3d) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1158 passed | 1172 passed | +14 |

Same 1 unchanged pre-existing failure.

## Files changed

```
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py
M  scripts/provision_ec2.py
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## What was deferred

- `EC2__BROWSER_INTERNAL_PORT` is still in `SG_INGRESS_PORTS` — Phase C will drop it as part of the strip (the VNC container moves to `sp vnc`).
- The wrapper functions in `provision_ec2.py` (still ~9 functions) get removed in step 3f when typer commands become thin wrappers over `Ec2__Service`.

## Next

Phase A step 3f — reduce the simplest typer commands (`list`, `info`, `delete`) to thin wrappers over `Ec2__Service`. This unblocks dropping the wrapper layer in `provision_ec2.py` for the migrated commands.
