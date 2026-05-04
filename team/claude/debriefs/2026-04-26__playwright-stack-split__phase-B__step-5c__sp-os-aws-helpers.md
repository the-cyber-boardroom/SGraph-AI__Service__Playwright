# Phase B · Step 5c — `sp os` AWS helpers (SG / AMI / Instance / Tags)

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 5b (schemas + collections).

---

## Why split?

Operator guidance: "make those new and refactored files smaller so that changes and context use are more optimised". The Elastic equivalent (`Elastic__AWS__Client.py`, ~470 lines, ~20 methods) is monolithic. For OpenSearch, this slice splits the AWS-touching surface into per-concern helpers — each in its own file under ~80 lines, with its own focused test file.

This keeps each future edit narrow (touching one helper) and lets agents/reviewers load only the slice they care about into context.

## What shipped

**Composition shell** (kept tiny):

- `OpenSearch__AWS__Client.py` — exposes `sg` / `ami` / `instance` / `tags` slots wired by `setup()`. Mirrors the `Docker__SP__CLI().setup()` lazy-init pattern. Lazy imports avoid circular module-load when callers import the client first.

**Four per-concern helpers** (one class per file, each ~50 lines):

| Helper | Responsibility |
|---|---|
| `OpenSearch__SG__Helper` | `ensure_security_group(region, stack_name, caller_ip)` (idempotent — duplicate-ingress swallowed); `delete_security_group(region, sg_id)` (returns False on dependency violations) |
| `OpenSearch__AMI__Helper` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=opensearch` + `sg:ami-status=healthy`, returns empty string if none |
| `OpenSearch__Instance__Helper` | `list_stacks(region)` (filtered by `sg:purpose=opensearch` + live states); `find_by_stack_name(region, stack_name)`; `terminate_instance(region, instance_id)` |
| `OpenSearch__Tags__Builder` | Pure mapper — builds the canonical 6-tag list. Name tag uses `OS_NAMING.aws_name_for_stack` so prefix never doubles. Creator falls back to 'unknown' when empty |

**Per-helper test files** (each ~80 lines):

- `test_OpenSearch__SG__Helper.py` (6 tests) — create-when-missing, reuse-existing, duplicate-ingress swallowed, other errors propagate, delete success / failure
- `test_OpenSearch__AMI__Helper.py` (4 tests) — latest AL2023 ordering / no-AMI raises; latest healthy ordering / empty-when-none
- `test_OpenSearch__Instance__Helper.py` (6 tests) — list filters, missing instance-id skipped, find-by-stack-name hit / miss, terminate success / failure
- `test_OpenSearch__Tags__Builder.py` (4 tests) — Name tag prefixed / never doubled, full tag set, creator-empty fallback
- `test_OpenSearch__AWS__Client.py` (composition tests rewritten) — slots are None pre-setup, all 4 helpers wired post-setup, setup chains

Every test uses a real `_Fake_Boto_EC2` subclass (one per helper) — no `unittest.mock`, no `MagicMock`. Records every call so tests can assert on exact kwargs (filter shapes, tag specs, port numbers).

## Bug surfaced + fixed in-flight

Tag spec already preserved the elastic ASCII-only Description fix (the em-dash bug from Phase A step 3d). The `Description` value in `OpenSearch__SG__Helper` is asserted ASCII via `.isascii()` in the create-when-missing test, locking it in.

## Test outcome

| Suite | Before (5b) | After (5c) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1277 passed | 1299 passed | +22 |

Same 1 unchanged pre-existing failure.

## File-size discipline (operator request)

| File | Lines |
|---|---|
| `OpenSearch__AWS__Client.py` (composition shell) | ~50 |
| `OpenSearch__SG__Helper.py` | ~50 |
| `OpenSearch__AMI__Helper.py` | ~40 |
| `OpenSearch__Instance__Helper.py` | ~50 |
| `OpenSearch__Tags__Builder.py` | ~30 |
| Each helper test file | ~70-90 |

For comparison, `Elastic__AWS__Client.py` is ~470 lines in a single file with ~20 methods. The OpenSearch surface trades aggregate LOC for narrower edits per change.

## What was deferred

- AMI lifecycle methods (`create_ami`, `wait_ami_available`, `tag_ami`, `deregister_ami`) — only needed by `sp os ami` subcommands, which are not on the critical path for create/list/info/delete. Will land in their own helper (`OpenSearch__AMI__Lifecycle__Helper.py`) when needed.
- IAM helpers — the section reuses Phase A's playwright-ec2 IAM role. If `sp os` needs a dedicated IAM role later, an `OpenSearch__IAM__Helper.py` will be added.
- SSM run-command — only needed for in-instance `sp os exec` / `harden`; will land in a `OpenSearch__SSM__Helper.py` when those commands are wired.
- `launch_instance` (the actual `run_instances` call) — lands in step 5e (Service) since it composes SG + AMI + IAM + tags.

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__SG__Helper.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__AMI__Helper.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Instance__Helper.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Tags__Builder.py
M  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__SG__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__AMI__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Instance__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Tags__Builder.py
M  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase B step 5d — `OpenSearch__HTTP__Client`: REST calls against the live OS instance (basic auth, self-signed TLS). Same small-file discipline.
