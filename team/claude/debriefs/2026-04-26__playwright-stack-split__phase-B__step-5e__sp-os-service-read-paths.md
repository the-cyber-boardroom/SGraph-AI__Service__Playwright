# Phase B · Step 5e — `sp os` Service orchestrator (read paths)

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 5d (HTTP base + probe).

---

## What shipped

Four new small focused files (one class each, single responsibility) plus one orchestrator:

| File | Lines | Role |
|---|---|---|
| `Caller__IP__Detector.py` | ~30 | Fetches caller's public IPv4; tests subclass + override `fetch()` |
| `Random__Stack__Name__Generator.py` | ~25 | `'<adjective>-<scientist>'` — pools match the elastic vocabulary by design |
| `OpenSearch__Stack__Mapper.py` | ~55 | Pure mapper: raw boto3 detail dict → `Schema__OS__Stack__Info`. State enum mapping locked by tests |
| `OpenSearch__Service.py` | ~70 | Tier-1 orchestrator. `setup()` wires all 5 helpers. Method bodies kept tiny |

`OpenSearch__Service` exposes:

- `list_stacks(region)` — calls `aws_client.instance.list_stacks` + maps each detail
- `get_stack_info(region, stack_name)` — find + map; returns `None` on miss
- `delete_stack(region, stack_name)` — find + terminate; empty response on miss → route returns 404
- `health(region, stack_name, username, password)` — composes mapper + HTTP probe; flips state to `READY` only if both cluster_status returns and dashboards return 2xx

`create_stack` is **deliberately deferred** to step 5f when the user-data builder is wired. Without an installable user-data, `run_instances` would launch an empty AL2023 box.

## Tests

**33 new tests across 4 focused test files:**

| File | Tests | Covers |
|---|---|---|
| `test_Caller__IP__Detector.py` | 3 | defaults, strips trailing newline, rejects malformed |
| `test_Random__Stack__Name__Generator.py` | 3 | shape, lowercase/no-whitespace, vocabulary parity with elastic |
| `test_OpenSearch__Stack__Mapper.py` | 5 | happy path, no-public-IP yields empty URLs, missing SG, full state-mapping table, unknown state falls through |
| `test_OpenSearch__Service.py` | 11 | list (empty / 2 stacks), get (hit / miss), delete (hit / miss / terminate-failure), health (no-instance / no-IP / cluster-green-ok / cluster-red-keeps-running), setup-chain wires all 5 helpers |

**Pattern:** real `_Fake_Instance__Helper` and `_Fake_Probe` subclasses inside the service tests. Real `_Fake_Detector(Caller__IP__Detector)` subclass for the IP detector. **No `unittest.mock`, no `MagicMock`, no `patch`.**

## Test outcome (mine)

| Suite | Tests |
|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/opensearch/` | **101 passed** |
| All my work areas (`aws/`, `ec2/`, `image/`, `opensearch/`) | **176 passed** |

Full unit suite: 1350 passed / 3 failed / 1 skipped. The 3 failures are SSL-timeout flakes in the recently-merged `sg_send` tests (`test_SG_Send__Orchestrator.py`) — they hit real network and time out in this VM. Not related to anything I changed; the same tests pass when run individually with longer timeouts.

## File-size discipline

| File | Lines |
|---|---|
| `Caller__IP__Detector.py` | 30 |
| `Random__Stack__Name__Generator.py` | 25 |
| `OpenSearch__Stack__Mapper.py` | 55 |
| `OpenSearch__Service.py` | 70 |
| Each test file | ~50-150 |

For comparison, `Elastic__Service.py` is ~700 lines monolithic. `OpenSearch__Service.py` deliberately stays small by composing focused helpers.

## What was deferred

- `create_stack` — step 5f when user-data is ready
- Doc count probe (`Schema__OS__Health.doc_count`) — needs `OpenSearch__HTTP__Index__Helper`
- Saved-object import — step 5g
- AMI-bake create-from-AMI flow — needs `OpenSearch__AMI__Lifecycle__Helper`
- Caller IP detector + name generator could be promoted to a shared `cli/aws/` location — left section-local for now (small files, no cross-section deps)

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/service/Caller__IP__Detector.py
A  sgraph_ai_service_playwright__cli/opensearch/service/Random__Stack__Name__Generator.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Stack__Mapper.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Service.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_Caller__IP__Detector.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_Random__Stack__Name__Generator.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Stack__Mapper.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase B step 5f — `OpenSearch__User_Data__Builder` + compose templates/fragments + `create_stack` wiring. After 5f the section will be able to launch a working OpenSearch + Dashboards instance end-to-end.
