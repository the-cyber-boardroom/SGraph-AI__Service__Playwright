# BV2.11 — Lambda packaging cutover; delete legacy `sgraph_ai_service_playwright/`

## Goal

Cut over the Lambda packaging chain to bake from `sg_compute_specs/playwright/core/` instead of the legacy `sgraph_ai_service_playwright/` package. After verification, delete the legacy package.

Today (v0.2.0): `lambda_entry.py` at the repo root imports from the legacy `sgraph_ai_service_playwright` package. Both copies of the Playwright code exist (BV.7.B was a copy not a move). The legacy review confirmed the legacy copy is **load-bearing** because the Dockerfile + `lambda_entry.py` still reference it.

## Tasks

1. **Update `lambda_entry.py`** at the repo root to import from `sg_compute_specs.playwright.core` instead of `sgraph_ai_service_playwright`. Verify the entry point shape (`handler = ...`) is preserved.
2. **Update `docker/playwright/Dockerfile`** (or the equivalent path) to `COPY` from `sg_compute_specs/playwright/core/` instead of `sgraph_ai_service_playwright/`.
3. **Update `pyproject.toml`** — drop `sgraph_ai_service_playwright` from `packages = [...]`. Update install path.
4. **Build and deploy** to a test environment. Verify the Playwright Lambda still serves the same surface (`/playwright/screenshot`, `/playwright/run`, etc.).
5. **Run the smoke test suite** for the Playwright Lambda (`tests/deploy/test_lambda_smoke.py` or equivalent).
6. **Once verified — DELETE `sgraph_ai_service_playwright/`** at the repo root. `git rm -r`.
7. **Update root `pyproject.toml`** — rename the meta-package to `sg-compute-meta` (or similar) that just declares dev dependencies. `sgraph-ai-service-playwright` stays only as a deprecated alias for one release if needed.
8. Update reality doc.

## Acceptance criteria

- `lambda_entry.py` imports from `sg_compute_specs.playwright.core`.
- Playwright Lambda smoke test passes from the new path.
- `sgraph_ai_service_playwright/` directory does not exist on disk.
- `pyproject.toml` does not list the legacy package.
- Tests pass.
- Reality doc updated.

## Open questions

- **`pyproject.toml` meta-package naming.** What does the root `pyproject.toml` declare? Options: (a) keep `sgraph-ai-service-playwright` as a deprecated meta-package, (b) rename to `sg-compute-meta`, (c) delete root `pyproject.toml` entirely (the SDK and catalogue have their own). Recommend (b) for one release, then (c) in v0.3. Architect to ratify.

## Blocks / Blocked by

- **Blocks:** BV2.12 (full cleanup of legacy trees).
- **Blocked by:** BV2.10 (`/legacy/` mount). The dashboard / SP CLI must still serve from the new control plane before this phase removes the legacy Lambda packaging path.

## Notes

This phase is a DELIVERY phase — the cutover is the win. All previous phases have been preparation. **Pair with Architect + DevOps** for the production smoke test.
