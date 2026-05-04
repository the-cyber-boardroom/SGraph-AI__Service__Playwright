# Debrief — CI fix: pytest exit-code-5 on placeholder jobs

- **Date:** 2026-04-16
- **Brief sections:** `ci-pipeline.md`, plus operational reality of pytest exit codes

## What was delivered

- Converted four placeholder test files from module-level `pytest.skip(allow_module_level=True)` to function-level `@pytest.mark.skip(reason=...)`:
  - `tests/docker/test_Local__Docker__SGraph-AI__Service__Playwright.py`
  - `tests/docker/test_ECR__Docker__SGraph-AI__Service__Playwright.py`
  - `tests/deploy/test_Deploy__Playwright__Service__to__dev.py`
  - `tests/deploy/test_Smoke__Playwright__Service__dev.py`

## Issue

After the last round of CI fixes, `Run Integration Tests (Docker)` and `Push Docker Image to ECR` jobs both reported `Process completed with exit code 5` with log showing `collected 0 items / 1 skipped`.

Pytest exit codes:
- `0` — all tests pass (or all skipped *at function level*)
- `1` — test failures
- `5` — **no tests collected**

`pytest.skip(..., allow_module_level=True)` skips before collection — pytest counts the module as "1 skipped" but reports 0 items collected, so it exits 5 and CI flags the job red.

## Fix

Function-level `@pytest.mark.skip` keeps pytest's collection step happy: 1 item collected, 1 skipped, exit 0.

## Deviations from brief

- None. Brief assumes these tests exist and pass; the placeholder pattern is a scaffolding concession until infra lands.

## Lessons

- **Module-level `pytest.skip(allow_module_level=True)` is a CI footgun.** Use a function-level `@pytest.mark.skip` decorator for placeholder test files. Only use module-level skip when the module physically cannot be imported (e.g. conditional on a missing platform dep).
- Prefer testing exit codes explicitly: `rc=$?` straight after pytest, before any pipe.

## Rolled-into-guidelines (proposed)

- **Update target:** `.claude/CLAUDE.md` or a new `team/claude/observations/*` note. Add:

  > **Placeholder test files.** When a test file is a scaffolded placeholder, use a function-level `@pytest.mark.skip(reason=...)` decorator, NOT module-level `pytest.skip(allow_module_level=True)`. Module-level skip makes pytest exit 5 ("no tests collected") in CI.

## Follow-up

- AWS credentials are now set (`AWS_ACCESS_KEY_ID`, `AWS_ACCOUNT_ID`, `AWS_DEFAULT_REGION`, `AWS_SECRET_ACCESS_KEY`) — the `check-aws-credentials` gate will flip `has-credentials = true` so `push-to-ecr` runs. Next time I touch these placeholders, they can be replaced with real ECR push + local-container integration logic (using `osbot-aws`, never boto3 directly).
