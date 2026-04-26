# Phase A · Step 3f — `cmd_list` / `cmd_info` / `cmd_delete` reduced to thin wrappers

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 3d (SG + AMI helpers).

---

## What shipped

**Schema extension:** `Schema__Ec2__Instance__Info` gained `instance_type : Safe_Str__Text` so the cmd_list table can render directly off the schema. `Ec2__Service.build_instance_info()` reads the `sg:instance-type` tag (fallback: AWS-side `instance_type`).

**New service method:** `Ec2__Service.delete_all_instances() -> Schema__Ec2__Delete__Response` — terminates every `sg:service=playwright-ec2` instance in one call. `target` and `deploy_name` empty on the response (no single target); `terminated_instance_ids` carries the full list.

**Typer commands reduced:**

- **`cmd_info`** (~60 lines → ~10). Calls `Ec2__Service().get_instance_info(target)`. The Rich rendering moved to a new `_render_info()` Tier-2A helper. JSON output uses `info.json_str()`.
- **`cmd_delete`** — both single and `--all` paths now call the service. Single path uses `service.delete_instance(target)`; `--all` uses the new `delete_all_instances()`. Confirmation prompt + per-instance preview unchanged.
- **`cmd_list`** — basic instance data comes from `service.list_instances()`. Two presentation enrichments stay inline (project AMI map + launch-time fetch via raw boto3 for osbot's `LauchTime` typo workaround); the table is now built off `Schema__Ec2__Instance__Info` fields rather than raw `details` dicts.

**New shared helper:** `_resolve_typer_target(target)` handles the "auto-pick when only one instance" UX. Used by the reduced `cmd_info` and `cmd_delete`. The older `_resolve_target` (which returns raw details) stays for the 12 commands that still need it.

## Tests

2 new unit tests for `Ec2__Service.delete_all_instances`:

- Empty world returns an empty response with no AWS calls.
- Multiple instances are terminated in one pass; the response carries every terminated instance ID.

The fake EC2 is a real `Ec2__AWS__Client` subclass (not a mock) — only `ec2()` is overridden to return an in-memory recorder. Caught a real-world test issue: `Safe_Str__Instance__Id` validates against `^i-[0-9a-f]{17}$`, so test fixtures must use realistic IDs.

## Test outcome

| Suite | Before (3d) | After (3f) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1172 passed | 1174 passed | +2 |

Same 1 unchanged pre-existing failure. The existing `tests/unit/sgraph_ai_service_playwright__cli/deploy/test_Ec2__Service.py` continues to pass — the schema extension is backwards-compatible (default empty string for `instance_type`).

## What was deferred

- 12 other typer commands (`cmd_connect`, `cmd_shell`, `cmd_env`, `cmd_logs`, `cmd_diagnose`, `cmd_forward`, `cmd_clean`, `cmd_open`, AMI commands, etc.) still call the old `_resolve_target(ec2, target)` helper directly. Reducing them is mechanical but out of scope for step 3f — most don't fit cleanly into a single service method (vault flow, SSM session, port forwarding, etc.).
- `cmd_list` still does inline raw boto3 calls for AMI source + launch times. Both could become service methods (`list_project_ami_ids()`, `fetch_launch_times(instance_ids)`) — left as a follow-up since they're presentation-only enrichments that don't affect API surface.

## Files changed

```
M  sgraph_ai_service_playwright__cli/ec2/schemas/Schema__Ec2__Instance__Info.py
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py
M  scripts/provision_ec2.py
A  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Phase A status

| Step | Status |
|---|---|
| 3a Naming + lookup helpers | ✅ |
| 3b AWS context accessors | ✅ |
| 3c IAM helpers | ✅ |
| 3d SG + AMI helpers | ✅ |
| 3f Typer wrappers (list / info / delete) | ✅ |
| Step 4 — missing FastAPI routes for CLI-only EC2 ops | next |

## Next

Phase A step 4 — add FastAPI routes for any EC2 op currently CLI-only. Survey current `Routes__Ec2__Playwright` coverage vs. typer surface; add the missing pieces. Likely a small addition since the bulk of EC2 ops (create/list/info/delete) are already routed.
