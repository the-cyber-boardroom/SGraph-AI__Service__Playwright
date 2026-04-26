# Phase A · Step 3a — `Ec2__AWS__Client`: naming + lookup helpers

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 2 (`Image__Build__Service`).

---

## Why

Step 3 of Phase A was originally one task: "migrate `provision_ec2.py` userdata/SG/IAM into `Ec2__Service` + `Ec2__AWS__Client`. Reduce typer commands to wrappers." That file is ~3000 lines, 121 functions, 36 typer commands. One commit would be unreviewable, and most of the userdata + compose-rendering code gets dramatically simplified by Phase C (the strip), so moving it now would create rework.

The split breaks step 3 into 5 sub-slices (3a → 3d, plus 3f) targeting only the **stable infrastructure** that survives Phase C. Userdata + compose rendering are deferred to Phase C itself. This slice (3a) is the smallest: pure naming + lookup helpers plus the EC2 boto3 boundary for find/resolve/terminate.

## What shipped

**New module: `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py`**

Mirrors the `Elastic__AWS__Client` pattern (module-level helpers + a Type_Safe class).

| Symbol | Form | What |
|---|---|---|
| `_ADJECTIVES`, `_SCIENTISTS` | Module-level lists | Naming pools (25 + 25 entries) |
| `TAG__SERVICE_KEY`, `TAG__SERVICE_VALUE`, `TAG__DEPLOY_NAME_KEY`, `INSTANCE_STATES_LIVE` | Module-level constants | Tag + state values used by find/resolve/terminate |
| `random_deploy_name()` | Module function | `'<adjective>-<scientist>'` for the `sg:deploy-name` tag |
| `get_creator()` | Module function | git email → `$USER` → `'unknown'` |
| `uptime_str(launch_time)` | Module function | Renders launch_time as `'Nd Nh'` / `'Nh Nm'` / `'Nm'` / `'?'` |
| `instance_tag(details, key)` | Module function | Lowercase-`tags` dict accessor matching osbot-aws's output |
| `instance_deploy_name(details)` | Module function | Convenience wrapper around `instance_tag` for the deploy-name tag |
| `Ec2__AWS__Client` | Type_Safe class | `ec2()` (single seam — tests override), `find_instances()`, `find_instance_ids()`, `resolve_instance_id(target)`, `terminate_instances(nickname='')` |

**Refactored: `scripts/provision_ec2.py`**

- 9 helper definitions deleted (5 pure helpers + 4 AWS-touching).
- `_ADJECTIVES` + `_SCIENTISTS` lists removed (now in the new module).
- 9 underscored alias imports added at the top.
- 4 thin wrapper functions added (`find_instances`, `find_instance_ids`, `_resolve_instance_id`, `terminate_instances`) that match the old signatures (still accept the `ec2: EC2 = None` parameter, now ignored) and delegate to a module-level `_AWS = Ec2__AWS__Client()` instance.

The wrapper functions are an explicit transitional shim — they go away in step 3f when typer commands become thin wrappers over `Ec2__Service`. Documented inline.

Net diff in `provision_ec2.py`: ~80 lines deleted, ~20 lines added.

**Refactored: `sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py`**

- All 5 lazy `from scripts.provision_ec2 import ...` calls for these helpers removed.
- New `aws_client()` seam added (single instance per call; tests override to inject fakes).
- `list_instances`, `get_instance_info`, `delete_instance`, `resolve_target` now go through `self.aws_client()` and call `find_instances` / `instance_deploy_name` / `instance_tag` / `ec2().instance_terminate()` directly.
- `resolve_target()` signature simplified: drops the `find_instances_fn` parameter (was a workaround for the lazy import).

`Ec2__Service` still imports a small set of constants from `scripts.provision_ec2` (`TAG__STAGE_KEY`, `TAG__CREATOR_KEY`, `TAG__API_KEY_NAME_KEY`, `TAG__API_KEY_VALUE_KEY`, `EC2__PLAYWRIGHT_PORT`, `EC2__SIDECAR_ADMIN_PORT`, `EC2__BROWSER_INTERNAL_PORT`) — those will move in 3b/3c/3d.

**Tests:** 24 new unit tests in `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py`:

| Group | Tests |
|---|---|
| `random_deploy_name` | 2 (shape + lowercase/whitespace-free) |
| `get_creator` | 1 (returns non-empty string) |
| `uptime_str` | 8 (None / empty / non-datetime / future / m / h+m / d+h / naive-utc) |
| `instance_tag` / `instance_deploy_name` | 4 (present / missing / no-tags / deploy-name accessor) |
| `Ec2__AWS__Client` class | 9 (find filter shape, None→{}, ids, resolve i-XXX/deploy-name/missing, terminate all/by-nickname/no-match) |

AWS calls exercised through `_Fake_EC2` — a real in-memory subclass that records calls and returns scripted responses. No mocks.

**Reality doc:** `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` updated with a new `ec2/service/Ec2__AWS__Client.py` section.

## Test outcome

| Suite | Before (Step 2 baseline) | After (Step 3a) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1123 passed / 1 failed / 1 skipped | 1147 passed / 1 failed / 1 skipped | +24 passed |

The 1 failing test (`test_S3__Inventory__Lister::test_empty_region_does_not_pass_region_name`) is the same pre-existing unrelated failure.

The pre-existing `tests/unit/scripts/test_provision_ec2.py` still passes — it asserts that the `find_instance_ids` and `terminate_instances` symbols are exported from `provision_ec2` (still true, via the wrapper layer) and monkey-patches `terminate_instances` for one test (works because the wrapper accepts the same single-arg call).

## Failure classification

Type: **good failure**. The refactor surfaced an inconsistency that the old code hid: the old `_resolve_instance_id` raised `ValueError` on a missing deploy-name, but the old `resolve_target` (in `Ec2__Service`) silently returned `(None, None)`. The new `Ec2__AWS__Client.resolve_instance_id` keeps the raise; `Ec2__Service.resolve_target` keeps the silent-None return for HTTP routes (where it maps to a 404). Both behaviours are now explicit and tested. No production change.

## What was deferred

- The 5 helpers `aws_account_id`, `aws_region`, `ecr_registry_host`, `default_playwright_image_uri`, `default_sidecar_image_uri` — Step 3b.
- IAM helpers (`ensure_caller_passrole`, `ensure_instance_profile`) — Step 3c.
- SG + AMI helpers (`ensure_security_group`, `latest_al2023_ami_id`, AMI lifecycle) — Step 3d.
- Userdata + compose rendering — Phase C (after strip).
- Reducing typer commands to thin wrappers — Step 3f.
- Removing the transitional wrapper functions in `provision_ec2.py` (`find_instances`, `find_instance_ids`, `_resolve_instance_id`, `terminate_instances`) — Step 3f.
- `Elastic__Service` has its own copy of the `_ADJECTIVES` list and a `resolve_creator()` method — duplicated logic. Could be unified later by promoting `random_deploy_name` / `get_creator` to a deeper-shared module. Left alone for now (out of scope).

## Files changed

```
A  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py
M  scripts/provision_ec2.py
A  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase A step 3b — AWS context accessors (`aws_account_id`, `aws_region`, `ecr_registry_host`, `default_playwright_image_uri`, `default_sidecar_image_uri`). Pure-data accessors that read from `osbot_aws.AWS_Config` + a couple of constants. Smallest of the remaining sub-slices.
