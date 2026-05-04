# Phase B · Step 5f.1 — `OpenSearch__User_Data__Builder` skeleton

**Date:** 2026-04-26.
**Commit:** `363341c`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5e (read-path orchestrator).

---

## Why

Step 5f originally landed as one big slice ("user-data + compose + create_stack wiring"). Per the operator's small-file / single-responsibility guidance, broken into 5 sub-slices: 5f.1 user-data shell, 5f.2 compose template, 5f.3 install-step expansion, 5f.4a launch helper, 5f.4b service wiring.

This one (5f.1) ships ONLY the rendering contract — a tight bash scaffold with substitution placeholders — so subsequent install-step slices grow the template in isolation.

## What shipped

`OpenSearch__User_Data__Builder.py` (~50 lines):
- `USER_DATA_TEMPLATE` — `#!/usr/bin/env bash`, `set -euo pipefail`, canonical `/var/log/sg-opensearch-boot.log`, 3 `{placeholder}`s
- `PLACEHOLDERS = ('stack_name', 'admin_password', 'region')` — locked by test against every `{key}` in the template
- `.render(stack_name, admin_password, region) -> str`

6 unit tests:
- All placeholders substituted
- No `{key}` leftover (regex)
- Starts with shebang (cloud-init treats `#!` as a script vs `#cloud-config`)
- `set -euo pipefail` present
- Logs to `/var/log/sg-opensearch-boot.log`
- `PLACEHOLDERS` constant matches every `{key}` in template

## Failure classification

Type: **good failure** (defensive). The placeholder-equals-PLACEHOLDERS test catches drift on every future slice that adds or removes a `{key}` — the user-data builder gets bigger over the next sub-slices, so this guardrail matters.

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__User_Data__Builder.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__User_Data__Builder.py
```
