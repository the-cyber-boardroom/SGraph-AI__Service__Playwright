# BV2.10 — Fold `Fast_API__SP__CLI` into `control_plane/` with `/legacy/` mount

## Goal

The legacy SP CLI control plane (`sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`) is still load-bearing — it serves `/catalog/types`, `/catalog/stacks`, `/catalog/ec2-info`, the per-spec `/{spec}/stack` endpoints, and others. The dashboard's frontend FV2.2 phase will switch to `/api/*` URLs but operator scripts and external consumers may still hit the legacy URLs for a release window.

This phase folds `Fast_API__SP__CLI`'s routes into `Fast_API__Compute` mounted at `/legacy/...` so:

- The single FastAPI process serves both the modern `/api/*` and legacy `/legacy/*` URLs.
- Operator scripts continue to work via `/legacy/`.
- We can deprecate `/legacy/*` formally in a future release with proper warnings + deadlines.

## Tasks

1. **Move route classes** from `sgraph_ai_service_playwright__cli/fast_api/routes/` to `sg_compute/control_plane/legacy_routes/`. Use `git mv` for history.
2. **Mount the legacy routes** on `Fast_API__Compute` in `setup_routes()` with prefix `/legacy/`. So `/legacy/catalog/types`, `/legacy/catalog/stacks`, etc.
3. **Add a deprecation header** to legacy responses: `X-Deprecated: true; X-Migration-Path: /api/specs (replaces /catalog/types)`.
4. **Update root entry-points** (`scripts/run_sp_cli.py`) to point at `Fast_API__Compute` instead of `Fast_API__SP__CLI`.
5. **Verify the legacy URLs still respond** — smoke test against a running instance: `GET /legacy/catalog/types` returns the same shape as the old `GET /catalog/types`.
6. **Leave `Fast_API__SP__CLI.py` as a thin re-export** of the new path for any code that still imports the class. BV2.12 deletes it.

## Acceptance criteria

- `Fast_API__Compute` serves both `/api/*` and `/legacy/*`.
- Every legacy URL response carries the `X-Deprecated` header.
- `pyproject.toml` script entry-points run via `Fast_API__Compute`.
- Tests pass.
- Reality doc updated.

## Open questions

- **Deprecation deadline.** When does `/legacy/*` go away? Recommend: mark deprecated in v0.2.x, remove in v0.3.0. Document in `RELEASE.md`.

## Blocks / Blocked by

- **Blocks:** BV2.11 (Lambda cutover) — should land first so the new control plane subsumes the old.
- **Blocked by:** BV2.7 (Tier-1 migration).

## Notes

The `/legacy/` mount is a **pragmatic bridge**, not a permanent home. The goal is single-process FastAPI that serves both vocabularies during the migration window.
