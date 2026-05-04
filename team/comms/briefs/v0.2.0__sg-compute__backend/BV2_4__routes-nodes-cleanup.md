# BV2.4 — Refactor `Routes__Compute__Nodes` (no logic, no raw dicts, no mocks)

## Goal

Code review found `Routes__Compute__Nodes` violates three project rules:

- Returns raw dicts (`{'nodes': [...], 'total': N}`) instead of `<schema>.json()` — violates "Type_Safe everywhere".
- Has business logic (the `'credential'` substring check + 503 fallback) — violates "routes have no logic".
- Module-level `_platform()` helper forced the test (`test_Routes__Compute__Nodes.py`) to use `unittest.mock.patch` 8 times — violates "no mocks".

This phase cleans all three.

## Tasks

1. **Add `Schema__Node__List`** if not present, with `nodes: List__Schema__Node__Info`, `total: Safe_Int__Count`, `region: Safe_Str__Region`. Update `EC2__Platform.list_nodes` to return this typed schema (it should already, per BV2.x; verify).
2. **Refactor `Routes__Compute__Nodes`**:
   - Replace `{'nodes': [n.json() for n in listing.nodes], 'total': len(listing.nodes)}` with `listing.json()` — single typed return.
   - Remove the inline `'credential'` substring check. The credentials-error fallback belongs in `EC2__Platform.list_nodes` (or in `Node__Manager` — Architect call) which raises a specific exception type. The route catches the exception type and translates to `HTTPException(503, ...)`. Better: register a FastAPI exception handler on `Fast_API__Compute` for `Exception__AWS__No_Credentials`.
   - Replace the module-level `_platform()` helper with constructor injection: `Routes__Compute__Nodes(platform: Platform)`. The `Fast_API__Compute.setup_routes` wires the singleton platform.
3. **Refactor `test_Routes__Compute__Nodes.py`**:
   - Drop all 8 `unittest.mock.patch` uses.
   - Use in-memory composition: a fake `Platform` instance that returns canned `Schema__Node__List` / `Schema__Node__Info`.
   - Verify exception flow with a fake platform that raises `Exception__AWS__No_Credentials` — assert the route returns 503 via the exception handler, not via inline string-matching.
4. Repeat the test-pattern fix for any other compute-control-plane test that uses `unittest.mock.patch`.

## Acceptance criteria

- `Routes__Compute__Nodes` returns `<schema>.json()` for all three endpoints (list / get / delete).
- No business logic (no exception-string matching, no `if 'credential' in str(e)` patterns).
- `Routes__Compute__Nodes(platform=...)` constructor; no module-level helpers.
- `test_Routes__Compute__Nodes.py` has zero `unittest.mock.patch` — verified by `grep -c 'mock.patch' test_Routes__Compute__Nodes.py` returning `0`.
- Exception handler for `Exception__AWS__No_Credentials` registered on `Fast_API__Compute`.
- All tests green.

## Open questions

- **Exception class location.** `Exception__AWS__No_Credentials` — does it live in `sg_compute/platforms/ec2/exceptions/` or `sg_compute/platforms/exceptions/`? Recommend the latter — credentials problems aren't EC2-specific.

## Blocks / Blocked by

- **Blocks:** none strict.
- **Blocked by:** none. Run any time.

## Notes

This phase establishes the pattern for every subsequent control-plane route refactor. After it lands, BV2.5 (`POST /api/nodes`) and BV2.3 (`Routes__Compute__Pods`) follow the same pattern by construction.
