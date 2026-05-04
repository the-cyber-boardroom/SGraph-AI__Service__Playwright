# BV2.8 — CI guard + fix `: object = None` Type_Safe bypass

## Goal

Two small but high-leverage cleanups:

1. Add a CI guard that prevents future `sg_compute*` → `sgraph_ai_service_playwright*` imports. After BV2.7, this should already pass; the guard prevents regression.
2. Fix the `: object = None` Type_Safe bypass that code review flagged across 5+ spec services.

## Tasks

### Task 1 — CI guard

Create `tests/ci/test_no_legacy_imports.py`:

```python
import pathlib
import re

def test_sg_compute_does_not_import_legacy():
    legacy_pattern = re.compile(r'from\s+sgraph_ai_service_playwright|import\s+sgraph_ai_service_playwright')
    offenders = []
    for root in [pathlib.Path('sg_compute'), pathlib.Path('sg_compute_specs')]:
        for py_file in root.rglob('*.py'):
            text = py_file.read_text()
            if legacy_pattern.search(text):
                offenders.append(str(py_file))
    assert not offenders, f"Legacy imports found in new tree: {offenders}"
```

This test runs in CI and fails if any new code imports from the legacy tree. Run it locally before pushing.

### Task 2 — Fix `: object = None` Type_Safe bypass

Code review found this pattern across docker, elastic, ollama, firefox, open_design (and possibly more):

```python
class Docker__Service(Type_Safe):
    aws_client: object = None       # ← silently bypasses Type_Safe
    user_data_builder: object = None
    ...
```

Replace `object` with the concrete type:

```python
class Docker__Service(Type_Safe):
    aws_client: Docker__AWS__Client | None = None
    user_data_builder: Docker__User_Data__Builder | None = None
    ...
```

For each spec service:

1. Identify every `: object = None` parameter.
2. Look up what's actually assigned at construction time.
3. Type-annotate properly with the concrete class (or a Type_Safe abstract base if multiple types are expected).
4. Run the spec's tests to confirm no breakage.

## Acceptance criteria

- `tests/ci/test_no_legacy_imports.py` exists and passes.
- `grep -rn ': object = None' sg_compute_specs/` returns zero hits.
- All spec tests still pass.
- Reality doc updated.

## Open questions

None.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** BV2.7 (the guard would currently fail if BV2.7 hasn't broken the cycle).

## Notes

This is a small phase but it's a quality bar that prevents regression. Once shipped, every future PR adding code under `sg_compute*` is checked for the legacy-import escape hatch.
