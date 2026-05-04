# Phase B · Step 5h — `Routes__OpenSearch__Stack` (FastAPI surface)

**Date:** 2026-04-26.
**Commit:** `aef4018`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5f.4b (`create_stack` wired into Service).

---

## What shipped

`Routes__OpenSearch__Stack.py` (~55 lines) — 5 routes mirror the `Routes__Ec2__Playwright` pattern. Each handler is a thin call to `OpenSearch__Service` + `.json()` — zero logic in the route.

| Method | Path | Handler → Service |
|---|---|---|
| POST | `/opensearch/stack` | `service.create_stack(body)` |
| GET | `/opensearch/stacks` | `service.list_stacks(region)` |
| GET | `/opensearch/stack/{name}` | `service.get_stack_info(region, name)` (404 on miss) |
| DELETE | `/opensearch/stack/{name}` | `service.delete_stack(region, name)` (404 on miss) |
| GET | `/opensearch/stack/{name}/health` | `service.health(region, name, username, password)` |

Region defaults to `DEFAULT_REGION` when not provided as a query param.

## Tests

9 new tests via FastAPI `TestClient` using a real `_Fake_Service` subclass of `OpenSearch__Service` (only public methods overridden — no mocks). Mounted onto a stand-alone `Fast_API()` app for the test client.

- list non-empty / empty
- info hit / 404 on miss with `'no opensearch stack'` detail
- create minimal / pinned-stack-name passthrough
- delete hit / 404 on miss
- health forwards `username` + `password` to service

## Wiring deferred

The route module is not yet mounted on `Fast_API__SP__CLI` — that landed alongside the typer commands in step 5i so the Tier-2A + Tier-2B duality is visible in one diff.

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/fast_api/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/fast_api/routes/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/fast_api/routes/Routes__OpenSearch__Stack.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/fast_api/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/fast_api/routes/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/fast_api/routes/test_Routes__OpenSearch__Stack.py
```
