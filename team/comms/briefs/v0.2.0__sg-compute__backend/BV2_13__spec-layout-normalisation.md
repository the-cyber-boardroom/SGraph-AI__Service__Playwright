# BV2.13 — Spec layout normalisation; lock `Enum__Spec__Capability` comment

## Goal

Code review found 4 specs (`ollama`, `open_design`, `mitmproxy`, `playwright`) deviate from canonical layout. `mitmproxy` and `playwright` manifests are missing `extends`/`soon`/`create_endpoint_path`. `Spec__Routes__Loader` only finds specific path patterns and silently misses 3 specs.

This phase normalises all 12 specs to canonical layout, fixes the loader, and locks the `Enum__Spec__Capability` header comment (still says "Architect locks before phase 3" — locked since 2026-05-04).

## Tasks

1. **For each of the 12 specs**, verify canonical layout per `architecture/01__architecture.md` §2:
   - `manifest.py` with `MANIFEST` constant including all 10 fields (`spec_id`, `display_name`, `icon`, `version`, `stability`, `nav_group`, `capabilities`, `boot_seconds_typical`, `extends=[]`, `soon`, `create_endpoint_path`).
   - `version` file present.
   - `service/`, `schemas/`, `api/routes/` populated.
   - `tests/` co-located.
2. **Fix the four deviating specs** — bring `ollama`, `open_design`, `mitmproxy`, `playwright` to canonical. Pay attention:
   - `mitmproxy.manifest.py` — add missing fields.
   - `playwright.manifest.py` — add missing fields. Decide whether `playwright/core/` flattens to match the others, or is documented as a justified exception.
3. **Fix `Spec__Routes__Loader`** to discover any `Routes__*` class in `<spec>/api/routes/` (not only `Routes__<Pascal>__Stack.py`). Use module introspection — for each spec, walk `<spec>/api/routes/`, import each module, find any class extending `Fast_API__Routes`, mount it.
4. **Add `manifest.py` validation** to `Spec__Loader.load_all()` — assert every loaded `MANIFEST` is a `Schema__Spec__Manifest__Entry` with all required fields populated. Fail fast on load with a clear error: "Spec X manifest is missing required field Y".
5. **Add a CI test** — `tests/ci/test_spec_canonical_layout.py` that walks `sg_compute_specs/` and asserts every spec is canonical.
6. **Update `Enum__Spec__Capability` header**:
   - Remove the "Architect locks set before phase 3" line.
   - Add: "LOCKED 2026-05-04 — 12 values aligned with the production catalogue. Adding a new value requires Architect sign-off + a brief in `team/comms/briefs/`."
7. Update reality doc.

## Acceptance criteria

- All 12 specs follow canonical layout (verified by `tests/ci/test_spec_canonical_layout.py`).
- `GET /api/specs` returns 12 entries with full manifest data — no missing fields.
- `Spec__Routes__Loader` mounts all 12 specs' routes correctly. Spot-check 3 specs not previously found.
- `Enum__Spec__Capability` header is current.
- Reality doc updated.

## Open questions

- **`playwright/core/` exception.** Does the Playwright spec keep the nested `core/` directory (because the original Playwright service is large) or flatten? Recommend: keep `core/` as a justified exception, documented in the manifest's docstring-equivalent (a header comment on `manifest.py`).

## Blocks / Blocked by

- **Blocks:** BV2.14 (spec test coverage) — easier when layouts are consistent.
- **Blocked by:** BV2.12 (legacy cleanup) — recommended first to reduce noise.

## Notes

This is the spec quality gate. After it lands, every new spec follows the same shape automatically. **Spec authors can stop guessing layout.**
