# Phase A · Step 3b — AWS context accessors

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 3a (`Ec2__AWS__Client` naming + lookup helpers).

---

## What shipped

5 module-level functions added to `cli/ec2/service/Ec2__AWS__Client.py`:

- `aws_account_id()` — `AWS_Config().aws_session_account_id()`
- `aws_region()` — `AWS_Config().aws_session_region_name()`
- `ecr_registry_host()` — `<account>.dkr.ecr.<region>.amazonaws.com`
- `default_playwright_image_uri()` — `<registry>/<PLAYWRIGHT_IMAGE_NAME>:latest`
- `default_sidecar_image_uri()` — `<registry>/<SIDECAR_IMAGE_NAME>:latest`

Plus the two `IMAGE_NAME` constants re-exported from the docker base modules.

`scripts/provision_ec2.py` had the 5 functions deleted; alias-imports added at the top so the typer commands keep working unchanged.

`Ec2__Service.create()` now imports them from the new home; `from scripts.provision_ec2 import ...` in `create()` shrinks from 7 imports to 2 (`provision`, `EC2__INSTANCE_TYPE`).

## Tests

4 new unit tests in `test_Ec2__AWS__Client.py` (`test_aws_context_accessors` group):

- `ecr_registry_host` assembled from account + region (with patched accessors)
- `default_playwright_image_uri` uses `PLAYWRIGHT_IMAGE_NAME`
- `default_sidecar_image_uri` uses `SIDECAR_IMAGE_NAME`
- `PLAYWRIGHT_IMAGE_NAME` and `SIDECAR_IMAGE_NAME` are non-empty and distinct

Patching is via module-level monkey-patching of `aws_account_id` / `aws_region` (no `unittest.mock`).

## Test outcome

| Suite | Before (3a) | After (3b) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1147 passed | 1151 passed | +4 |

1 unchanged pre-existing failure.

## Files changed

```
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py
M  scripts/provision_ec2.py
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase A step 3c — IAM helpers (`ensure_caller_passrole`, `ensure_instance_profile`, trust-policy + ARN constants). Side-effecting AWS calls; medium risk.
