# Observation — `__init__.py` files must be empty

- **Date captured:** 2026-04-16
- **Source:** Dinis Cruz — chat message during phase 1.1/1.2 work.
- **Status:** CAPTURED. Applied. No inline source comment exists — this came via chat.

## Original comment (verbatim)

> "ahh, no, don't put anything on those `__init__.py` files"
>
> "they should all be empty"

## Interpretation

Every `__init__.py` across `sgraph_ai_service_playwright/` and `tests/` must remain empty. No re-exports, no convenience imports, no `__all__`, nothing.

Callers always import from the fully-qualified submodule path:

```python
# YES
from sgraph_ai_service_playwright.schemas.enums.enums import Enum__Browser__Kind

# NO — would require __init__.py to re-export
from sgraph_ai_service_playwright.schemas.enums import Enum__Browser__Kind
```

## Why (inferred)

- Makes the one-class-per-file layout navigable: there's exactly one place each symbol lives.
- Prevents import-time coupling: touching a primitives folder won't cascade-rebuild unrelated modules.
- Keeps module boundaries honest — no hidden facade layer.

## Rolled-into-guidelines

- **Update target:** `.claude/CLAUDE.md` "Code Patterns" section. Add:

  > **All `__init__.py` files are empty.** No re-exports, no `__all__`. Every caller imports from the fully-qualified submodule (or per-class file) path.

## Compliance check (to run before commits)

```bash
find sgraph_ai_service_playwright tests -name __init__.py -not -empty
# must output nothing
```
