# Phase A · Step 3c — IAM helpers + constants

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 3b (AWS context accessors).

---

## What shipped

Added to `cli/ec2/service/Ec2__AWS__Client.py`:

**8 IAM constants** — `IAM__ROLE_NAME`, `IAM__ECR_READONLY_POLICY_ARN`, `IAM__SSM_CORE_POLICY_ARN`, `IAM__POLICY_ARNS`, `IAM__PROMETHEUS_RW_POLICY_ARN`, `IAM__OBSERVABILITY_POLICY_ARNS`, `IAM__ASSUME_ROLE_SERVICE`, `IAM__PASSROLE_POLICY_NAME`.

**3 module-level functions:**
- `decode_aws_auth_error(exc)` — calls `sts:DecodeAuthorizationMessage` to decode AWS-encoded UnauthorizedOperation blobs. Pure decoder — no Console output.
- `ensure_caller_passrole(account)` — attaches a minimal `iam:PassRole` inline policy to the calling IAM user (idempotent; pinned Resource + service condition for safety). Returns `{ok, action, detail}`.
- `ensure_instance_profile()` — creates the `playwright-ec2` IAM role + instance profile + attaches the SSM/ECR/AMP policy ARNs (idempotent: catches `EntityAlreadyExists`).

**Refactored `provision_ec2.py`:**
- 8 IAM constants deleted; alias-imports added at top
- 3 functions deleted; alias-imports added (with `decode_aws_auth_error as _decode_aws_auth_error` to preserve the underscored name internally)
- The Console-formatted `_print_auth_error` stays in `provision_ec2.py` — it's Tier 2A (CLI rendering), not Tier 1 logic
- **Behavioural change:** `ensure_caller_passrole` no longer calls `_print_auth_error` on auth failure — it just raises. The typer command (`cmd_ensure_passrole`) catches and formats. The old code printed AND raised, so the test suite's monkey-patch (which ignores both) is unaffected.

## Tests

7 new unit tests added to `test_Ec2__AWS__Client.py`:

- `test_iam_constants` — 5 tests locking the constant values (role name doesn't start with `sg-`, passrole policy name shape, assume-role service, ECR/SSM ARNs in `IAM__POLICY_ARNS`, observability ARNs).
- `test_decode_aws_auth_error` — 2 tests covering the no-encoded-blob path and the swallow-on-sts-failure path.

The boto3-touching `ensure_caller_passrole` and `ensure_instance_profile` are exercised by the existing `tests/unit/scripts/test_provision_ec2.py` (which monkey-patches `provision_ec2.ensure_caller_passrole`) and by the deploy-via-pytest integration tests gated on real AWS.

## Test outcome

| Suite | Before (3b) | After (3c) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1151 passed | 1158 passed | +7 |

Same 1 unchanged pre-existing failure.

## Files changed

```
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py
M  scripts/provision_ec2.py
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase A step 3d — SG + AMI helpers (`ensure_security_group`, `latest_al2023_ami_id`, `create_ami`, `wait_ami_available`, `tag_ami`, `latest_healthy_ami`).
