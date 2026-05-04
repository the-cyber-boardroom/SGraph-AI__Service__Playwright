# Phase A · Step 2 — `Image__Build__Service`: shared Docker build pipeline

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 1 (`Stack__Naming`).

---

## Why

Two builders shipped today — `Build__Docker__SGraph_AI__Service__Playwright` (Playwright EC2 image) and `Docker__SP__CLI` (SP CLI Lambda image) — duplicated ~70% of their code: tempdir staging, `__pycache__` ignore filter, direct docker SDK call (to bypass osbot-docker's `@catch` wrapper), tempdir cleanup. Each used a different path-resolution strategy, returned a different dict shape, and would have been a copy-paste target a third time when `sp os` / `sp prom` / `sp vnc` need their own AMIs.

Doc 2 of the plan called for a single `Image__Build__Service` under `cli/image/` with Type_Safe result schemas. This slice lands it and rewires both existing consumers.

## What shipped

**New module: `sgraph_ai_service_playwright__cli/image/`**

| File | Role |
|------|------|
| `image/schemas/Schema__Image__Stage__Item.py` | One file or directory tree to copy into the build context (`source_path`, `target_name`, `is_tree`, `extra_ignore_names`). |
| `image/collections/List__Schema__Image__Stage__Item.py` | Ordered list of stage items. |
| `image/collections/List__Str.py` | Typed list of strings (used for tags + ignore names). |
| `image/schemas/Schema__Image__Build__Request.py` | Build inputs: `image_folder`, `image_tag`, `stage_items`, `dockerfile_name='dockerfile'`, `requirements_name='requirements.txt'`, `build_context_prefix`. |
| `image/schemas/Schema__Image__Build__Result.py` | Build outputs: `image_id`, `image_tags`, `duration_ms`. |
| `image/service/Image__Build__Service.py` | Orchestrator with two seams: `stage_build_context()` (pure I/O — fully unit-testable) and `build()` (invokes docker SDK directly). Default ignore set augmented per-item via `extra_ignore_names`. |

**Refactored consumers (now thin composers):**

- **`Build__Docker__SGraph_AI__Service__Playwright`** (`sgraph_ai_service_playwright/docker/`) — `build_docker_image()` returns `Schema__Image__Build__Result`. Composes 3 stage items: `lambda_entry.py`, `image_version`, full `sgraph_ai_service_playwright/` tree.
- **`Docker__SP__CLI`** (`sgraph_ai_service_playwright__cli/deploy/`) — `build_and_push()` keeps its dict return shape (`image_uri` / `image_id` / `push`) since the deploy callers consume those keys. Composes 4 stage items: `sgraph_ai_service_playwright__cli` (with `extra_ignore_names=['images']` for the deploy/images folder), `sgraph_ai_service_playwright`, `agent_mitmproxy`, `scripts`. The `stage_build_context()` method is preserved as a thin delegation to the shared service for the existing test seam.

**Removed:**
- `Build__Docker__SGraph_AI__Service__Playwright._ignore_build_noise()` (module-level)
- `Build__Docker__SGraph_AI__Service__Playwright.DOCKERFILE_NAME` constant (now defaulted in the schema)
- `Docker__SP__CLI.ignore_build_noise()` (module-level — the test that asserted on it was redundant with the new `Image__Build__Service` ignore tests)

**Tests:** 15 new unit tests under `tests/unit/sgraph_ai_service_playwright__cli/image/`:

| Test | What it covers |
|---|---|
| 3 schema round-trip + default tests | `Schema__Image__Stage__Item`, `Schema__Image__Build__Request`, `Schema__Image__Build__Result` |
| 5 `stage_build_context` tests | Dockerfile + requirements baseline, single file copy, tree copy + default ignore, per-item `extra_ignore_names`, custom dockerfile/requirements name |
| 2 `build()` tests | Returns Type_Safe result + calls docker SDK with correct args (using in-memory fake docker client — real classes, no mocks); tempdir cleaned even when docker raises |
| 1 `make_ignore_callable` test | Defaults union extras |

Plus 1 new unit test on `Docker__SP__CLI`: `test_build_request__has_all_four_source_trees_with_correct_target_names` locks the SP-CLI image composition.

The deploy-via-pytest integration test `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py` was updated to assert on `Schema__Image__Build__Result` fields instead of the old dict keys.

**Reality doc:** `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` updated with the new `image/` package section.

## Test outcome

| Suite | Before (Step 1 baseline) | After (Step 2) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1070 passed / 1 failed / 1 skipped | 1123 passed / 1 failed / 1 skipped | +53 passed |

The 1 failing test (`test_S3__Inventory__Lister::test_empty_region_does_not_pass_region_name`) is the same pre-existing unrelated failure carried since baseline.

The +53 new passing tests = 15 image tests + 38 from the dev/observability merges that came in as part of syncing.

## Failure classification

Type: **good failure**. The refactor surfaced and the new tests cover an edge case the old code only handled implicitly: tempdir cleanup when `docker.images.build()` raises. Both old builders had `try / finally shutil.rmtree(...)` around the build, but neither tested it. The new `test_build__cleans_up_tempdir_even_when_docker_raises` locks that behaviour in. No production behaviour changed.

## What was deferred

- **`Docker__SP__CLI.build_and_push()` still returns a dict** (with `image_uri` / `image_id` / `push` keys) rather than a Type_Safe schema. The deploy callers (CI workflow + provisioner) consume those exact keys; converting them is a separate, lateral change worth its own slice. The Type_Safe `Schema__Image__Build__Result` is available internally; a thin schema wrapper around build+push (`Schema__Image__Build_And_Push__Result`) can land when the callers are migrated.
- **`agent_mitmproxy` does NOT have a builder class** in the same shape as the other two — its build path lives in CI via `osbot-aws` directly. When it gets a wrapper class, it'll use the same `Image__Build__Service` for free.
- **Build args / cache-from / multi-platform** — none of the existing builders pass these; the schema doesn't model them. Add when needed.

## Files changed

```
A  sgraph_ai_service_playwright__cli/image/__init__.py
A  sgraph_ai_service_playwright__cli/image/schemas/__init__.py
A  sgraph_ai_service_playwright__cli/image/schemas/Schema__Image__Stage__Item.py
A  sgraph_ai_service_playwright__cli/image/schemas/Schema__Image__Build__Request.py
A  sgraph_ai_service_playwright__cli/image/schemas/Schema__Image__Build__Result.py
A  sgraph_ai_service_playwright__cli/image/collections/__init__.py
A  sgraph_ai_service_playwright__cli/image/collections/List__Schema__Image__Stage__Item.py
A  sgraph_ai_service_playwright__cli/image/collections/List__Str.py
A  sgraph_ai_service_playwright__cli/image/service/__init__.py
A  sgraph_ai_service_playwright__cli/image/service/Image__Build__Service.py
M  sgraph_ai_service_playwright/docker/Build__Docker__SGraph_AI__Service__Playwright.py
M  sgraph_ai_service_playwright__cli/deploy/Docker__SP__CLI.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/schemas/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/schemas/test_Schema__Image__Stage__Item.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/schemas/test_Schema__Image__Build__Request.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/schemas/test_Schema__Image__Build__Result.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/service/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/image/service/test_Image__Build__Service.py
M  tests/unit/sgraph_ai_service_playwright__cli/deploy/test_Docker__SP__CLI.py
M  tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase A step 3 — migrate `scripts/provision_ec2.py` userdata / SG / IAM logic into `Ec2__Service` + `Ec2__AWS__Client`. Reduce typer commands to wrappers. This is the largest of Phase A's four steps; it touches the bulky `provision_ec2.py` (~3000 lines) and is a strict prerequisite for the EC2 strip-down (Phase C).
