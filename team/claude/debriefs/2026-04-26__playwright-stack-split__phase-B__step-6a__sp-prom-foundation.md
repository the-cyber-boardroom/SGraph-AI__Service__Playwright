# Phase B · Step 6a — `sp prom` foundation

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/05__sp-prom__prometheus.md`.
**Predecessor:** Phase B step 5 (`sp os` functionally complete).

---

## What shipped

First slice of the Prometheus sister section. Same shape as the `sp os` 5a foundation — folder + naming-shape primitives + lifecycle enum + AWS-client skeleton with tag constants.

| File | Role |
|---|---|
| `cli/prometheus/__init__.py` | Empty package marker |
| `cli/prometheus/primitives/Safe_Str__Prom__Stack__Name.py` | Stack name primitive — regex parity with elastic + opensearch locked by test |
| `cli/prometheus/primitives/Safe_Str__IP__Address.py` | Local copy (sister sections stay self-contained) |
| `cli/prometheus/enums/Enum__Prom__Stack__State.py` | Lifecycle vocabulary — shape parity with elastic + opensearch |
| `cli/prometheus/service/Prometheus__AWS__Client.py` | Skeleton: `PROM_NAMING = Stack__Naming(section_prefix='prometheus')` + 6 tag constants (`sg:purpose=prometheus`, `sg:section=prom`) |

## Naming choice

Folder `prometheus/` (long form) avoids any ambiguity with possible third-party `prom` packages. Typer aliases will be `sp prom` (short, matching `sg:section`) and `sp prometheus` (long, matching `sg:purpose`) — same precedent as `sp os` / `sp opensearch`.

## Tests

19 new tests:

| Group | Tests |
|---|---|
| `Safe_Str__Prom__Stack__Name` | 6 — valid names, lowercases, rejects start-with-digit / underscore, empty allowed, regex parity with elastic + opensearch |
| `Enum__Prom__Stack__State` | 4 — exhaustive set, lowercase values, `__str__`, shape parity |
| `PROM_NAMING` | 5 — Stack__Naming instance, prefix correct, aws_name_for_stack adds/never-doubles, sg_name_for_stack appends `-sg` |
| Tag constants | 3 — purpose value, section value, all sg:-namespaced |
| Skeleton | 1 — instantiates cleanly |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| My work areas (aws/ec2/image/opensearch/prometheus) | 232 | 251 | +19 |

## What was deferred

- 6b — schemas + collections
- 6c — AWS helpers (SG / Instance / Tags / Launch)
- 6d — Prometheus HTTP client (`/-/healthy`, `/api/v1/query`, `/api/v1/targets`)
- 6e — `Prometheus__Service` orchestrator
- 6f — user-data + compose template + create_stack wiring
- 6g — FastAPI routes
- 6h — typer commands

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/primitives/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/primitives/Safe_Str__Prom__Stack__Name.py
A  sgraph_ai_service_playwright__cli/prometheus/primitives/Safe_Str__IP__Address.py
A  sgraph_ai_service_playwright__cli/prometheus/enums/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/enums/Enum__Prom__Stack__State.py
A  sgraph_ai_service_playwright__cli/prometheus/service/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/primitives/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/primitives/test_Safe_Str__Prom__Stack__Name.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/enums/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/enums/test_Enum__Prom__Stack__State.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 6b — schemas + collections. Smaller surface than `sp os` (no admin password, no Dashboards URL).
