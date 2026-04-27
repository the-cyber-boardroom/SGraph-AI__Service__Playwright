# Phase B · Step 5b — `sp os` schemas + collections

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 5a (foundation).

---

## What shipped

**Two new primitives:**

- `Safe_Str__OS__Password` — URL-safe base64, 16–64 chars; same regex as `Safe_Str__Elastic__Password`.
- `Safe_Str__IP__Address` — local copy in `opensearch/primitives/`. Sister sections stay self-contained; future cleanup can promote a shared version when 3+ sections need it.

**Six schemas + one collection:**

| Schema | Purpose |
|---|---|
| `Schema__OS__Stack__Create__Request` | All fields optional; service generates name, detects caller IP, picks defaults |
| `Schema__OS__Stack__Create__Response` | Returned once; carries `admin_password`, `dashboards_url`, `os_endpoint` |
| `Schema__OS__Stack__Info` | Public view; **never includes `admin_password`** (defensive test locks this) |
| `Schema__OS__Stack__List` | Region + `List__Schema__OS__Stack__Info` |
| `Schema__OS__Stack__Delete__Response` | Empty fields ⇒ route returns 404; same shape as elastic |
| `Schema__OS__Health` | `cluster_status` (green/yellow/red), `node_count`, `active_shards`, `doc_count`, `dashboards_ok`, `os_endpoint_ok`. `-1` sentinels mark unreachable probes |
| `List__Schema__OS__Stack__Info` | `Type_Safe__List` collection |

## Tests

19 new unit tests:

- 6 password tests (valid, empty allowed, too-short / too-long / disallowed-chars rejections, regex parity with elastic)
- 6 schema round-trip tests (one per schema; defaults + JSON round-trip)
- 1 defensive test that `Schema__OS__Stack__Info` never includes a `password` field
- Plus the `List` + `Delete` schemas grouped tests

## Test outcome

| Suite | Before (5a) | After (5b) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1199 passed | 1224 passed | +25 |

(+19 from new tests in this slice, +6 from a recently-merged observability-branch slice.) Same 1 unchanged pre-existing failure.

## What was deferred

- AMI lifecycle schemas (`Schema__OS__AMI__Info`, etc.) — added when AMI lifecycle methods land
- Saved-object / dashboard schemas (`Schema__OS__Saved_Object`, `Schema__OS__Dashboard__Result`) — step 5g
- `Schema__AWS__Error__Hint`, `Schema__Exec__Result`, etc. — added on-demand when service methods need them

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/primitives/Safe_Str__OS__Password.py
A  sgraph_ai_service_playwright__cli/opensearch/primitives/Safe_Str__IP__Address.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Stack__Create__Request.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Stack__Create__Response.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Stack__Info.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Stack__List.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Stack__Delete__Response.py
A  sgraph_ai_service_playwright__cli/opensearch/schemas/Schema__OS__Health.py
A  sgraph_ai_service_playwright__cli/opensearch/collections/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/collections/List__Schema__OS__Stack__Info.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/test_Schema__OS__Stack__Create__Request.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/test_Schema__OS__Stack__Create__Response.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/test_Schema__OS__Stack__Info.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/test_Schema__OS__Stack__List_and_Delete.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/schemas/test_Schema__OS__Health.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/collections/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/primitives/test_Safe_Str__OS__Password.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase B step 5c — AWS-touching methods on `OpenSearch__AWS__Client` (find_stacks / create / delete / ensure_security_group / latest_al2023_ami_id / etc.). Reuses `OS_NAMING` for stack-name → AWS-name mapping and the cli/ec2 `Ec2__AWS__Client` patterns.
