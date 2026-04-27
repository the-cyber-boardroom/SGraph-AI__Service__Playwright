# Phase B · Step 5a — `sp os` foundation: folder + primitives + enums + AWS-client skeleton

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Phase A done (foundations: Stack__Naming, Image__Build__Service, Ec2__AWS__Client).

---

## What shipped

First slice of the new `sp os` sister section. Establishes the namespace + the lowest-risk building blocks; AWS-touching methods land in step 5c.

| File | Role |
|---|---|
| `cli/opensearch/__init__.py` | Empty package marker |
| `cli/opensearch/primitives/Safe_Str__OS__Stack__Name.py` | Stack-name primitive (regex matches `Safe_Str__Elastic__Stack__Name`) |
| `cli/opensearch/enums/Enum__OS__Stack__State.py` | Lifecycle vocabulary (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN) — mirrors `Enum__Elastic__State` |
| `cli/opensearch/service/OpenSearch__AWS__Client.py` | Skeleton with `OS_NAMING = Stack__Naming(section_prefix='opensearch')` + 6 tag constants (`sg:purpose=opensearch`, `sg:section=os`, etc.) |

## Why `opensearch/` not `os/`

The plan (doc 4) called for `cli/os/`. **`os` shadows the Python stdlib `os` module** — every `import os` inside `sgraph_ai_service_playwright__cli/` resolved to the local empty package, breaking `os.environ.setdefault(...)` in `lambda_handler.py` and 175 downstream tests. Renamed to `cli/opensearch/`. Doc 4 updated with a note explaining the choice. The typer command alias stays `sp os` / `sp opensearch` — only the Python folder name changed.

## Tests

23 new unit tests:

| Group | Tests |
|---|---|
| `Safe_Str__OS__Stack__Name` (10) | Valid names, lowercases, trims whitespace, rejects starting-with-digit / underscore / too-short / too-long, empty allowed, regex shape matches elastic |
| `Enum__OS__Stack__State` (4) | Exhaustive member set, lowercase values, `__str__` returns value, shape parity with `Enum__Elastic__State` |
| `OS_NAMING` (5) | Is a `Stack__Naming`, section prefix is `opensearch`, `aws_name_for_stack` adds prefix / never doubles, `sg_name_for_stack` appends `-sg` |
| Tag constants (3) | Purpose value is `opensearch`, section value is `os`, all keys are `sg:`-namespaced |
| `OpenSearch__AWS__Client` skeleton (1) | Instantiates cleanly |

## Failure surfaced

Type: **good failure**. Caught the `os` package shadowing immediately when running the full unit suite (175 failed). Without the suite, the issue would have surfaced only at Lambda boot time, when the bootstrap `lambda_entry.py` calls `os.environ.setdefault(...)`. The rename happened in this same slice; the lesson is recorded in the plan doc.

## Test outcome

| Suite | Before (Phase A done) | After (5a) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1176 passed | 1199 passed | +23 |

Same 1 unchanged pre-existing failure.

## What was deferred to subsequent slices

- `Schema__OS__Stack__Create__Request` / `Response` / `Info` / `List` / `Delete__Response` / `Health` and the `List__Schema__OS__*` collections (step 5b)
- `OpenSearch__AWS__Client` AWS-touching methods (find_stacks, create_stack, delete_stack, ensure_security_group, etc.) (step 5c)
- `OpenSearch__HTTP__Client` (REST client against the live instance) (step 5d)
- `OpenSearch__Service` orchestrator (step 5e)
- `OpenSearch__User_Data__Builder` + compose templates (step 5f)
- `Base__Dashboard__Generator` shared base + `OpenSearch__Dashboard__Generator` (step 5g — fulfils OS4 "best of both, not lowest common denominator")
- `Routes__OpenSearch__Stack` FastAPI routes (step 5h)
- `sp os` typer commands (step 5i)

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/primitives/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/primitives/Safe_Str__OS__Stack__Name.py
A  sgraph_ai_service_playwright__cli/opensearch/enums/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/enums/Enum__OS__Stack__State.py
A  sgraph_ai_service_playwright__cli/opensearch/service/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/primitives/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/primitives/test_Safe_Str__OS__Stack__Name.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/enums/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/enums/test_Enum__OS__Stack__State.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
M  team/comms/plans/v0.1.96__playwright-stack-split__04__sp-os__opensearch.md
```

## Next

Phase B step 5b — schemas + collections. Each `Schema__OS__*` class lives in its own file mirroring the elastic schemas folder. Pure data, no logic.
