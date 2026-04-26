# Phase A · Step 1 — Promote `Stack__Naming` to a shared `cli/aws/` module

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/` (docs 1–8).
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Scope:** First concrete code change of the v0.1.96 stack-split plan.

---

## Why

Doc 4 of the plan calls for `aws_name_for_stack()` and `sg_name_for_stack()` helpers — currently elastic-only — to graduate to a shared utility so every sister section (`sp el`, `sp os`, `sp prom`, `sp vnc`) uses one implementation. Without this, each new section would duplicate the same two functions with their own hardcoded section prefix.

The two helpers encode CLAUDE.md AWS Resource Naming rules (#14: SG GroupName must not start with `sg-`; #15: AWS Name tag must not be double-prefixed). Drift across sections would silently re-introduce those bugs.

## What shipped

**New module: `sgraph_ai_service_playwright__cli/aws/`**
- `aws/__init__.py` (empty per CLAUDE.md rule #22)
- `aws/Stack__Naming.py` — `Type_Safe` class with `section_prefix : str` attribute and two methods:
  - `aws_name_for_stack(stack_name)` — adds `{prefix}-` unless already present.
  - `sg_name_for_stack(stack_name)` — appends `-sg` regardless of section.

**Refactored: `elastic/service/Elastic__AWS__Client.py`**
- Module-level functions `aws_name_for_stack()` and `sg_name_for_stack()` deleted (clean-cut, no shim per operator's clean-slate stance).
- New module-level constant `ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')`.
- 2 internal call sites switched to `ELASTIC_NAMING.*`.

**Updated callers:**
- `elastic/service/Elastic__Service.py` — import switched from `aws_name_for_stack` to `ELASTIC_NAMING`; 2 call sites updated.
- `tests/unit/.../elastic/service/Elastic__AWS__Client__In_Memory.py` — import + 1 call site updated.

**Tests:** `tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py` — 9 tests covering:
- Prefix added when missing.
- Prefix not doubled when already present.
- Partial match (`elasticfoo`) does not count as already-prefixed.
- Empty input yields bare prefix (caller-error indicator, not silent).
- Per-section isolation (4 different prefixes produce 4 different names).
- SG suffix appended.
- SG name never starts with `sg-` regardless of section.
- SG suffix is section-independent.
- Default `section_prefix` is empty (defensive).

**Reality doc:** `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` updated with the new `aws/` package entry.

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| New `tests/unit/.../aws/` | 0 | 9 | +9 |
| `tests/unit/.../elastic/` (full) | 492 | 492 | 0 (no behavioural change) |
| Full `tests/unit/` | 1061 passed / 1 failed / 1 skipped | 1070 passed / 1 failed / 1 skipped | +9 passed |

The 1 failing test (`test_S3__Inventory__Lister::test_empty_region_does_not_pass_region_name`) is pre-existing and unrelated — failing on the baseline before this work.

## Failure classification

Type: **good failure**. The refactor surfaced — and the new tests cover — a corner case the old elastic-only function did not test explicitly: `aws_name_for_stack('elasticfoo')` would produce `elastic-elasticfoo` (correct: `elasticfoo` does not start with `elastic-`). The new `test_aws_name_for_stack__partial_match_does_not_count` locks that behaviour in. No production behaviour changed.

## What was deferred

- Sister-section `*_NAMING` constants (`OS_NAMING`, `PROM_NAMING`, `VNC_NAMING`) are not added in this slice — they land with their respective sections (Phase B docs 4-6). The shared class is in place ready to be instantiated.
- `Safe_Str__Section__Prefix` validation primitive — `section_prefix` is plain `str` for now. If a typo silently produces `elasitc-foo` we would not catch it; this is acceptable given the small enumerated set of legal prefixes (`elastic`/`opensearch`/`prometheus`/`vnc`) and the fact that a typo would surface immediately on the first AWS call.

## Files changed

```
A  sgraph_ai_service_playwright__cli/aws/__init__.py
A  sgraph_ai_service_playwright__cli/aws/Stack__Naming.py
M  sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py
M  sgraph_ai_service_playwright__cli/elastic/service/Elastic__Service.py
M  tests/unit/sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client__In_Memory.py
A  tests/unit/sgraph_ai_service_playwright__cli/aws/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase A step 2 — `Image__Build__Service` under `cli/image/` with `Type_Safe` result schemas. Reduces the ~70% duplication between `Build__Docker__SGraph_AI__Service__Playwright` and `Docker__SP__CLI` to a single shared service.
