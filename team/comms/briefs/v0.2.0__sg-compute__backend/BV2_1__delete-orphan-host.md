# BV2.1 — Delete orphan `sgraph_ai_service_playwright__host/`

## Goal

Remove the legacy host-control package at the repo root. The 2026-05-04 legacy code review confirmed this directory is **orphaned** — nothing outside it imports it; the host-control Lambda already runs from `sg_compute/host_plane/` (B6 was a copy-not-move and this is the original copy still hanging around). Lowest blast radius cleanup.

## Tasks

1. Run `grep -r "sgraph_ai_service_playwright__host" --include="*.py" --include="*.toml" --include="*.yml" --include="Dockerfile*" .` — confirm the only hits are inside the directory itself. (If you find external references, escalate to Architect — the legacy review may be stale.)
2. `git rm -r sgraph_ai_service_playwright__host/`.
3. Search for any leftover references in `pyproject.toml` (the `packages = [...]` array may list it) and remove.
4. Search for any leftover references in `docker/` and `.github/workflows/` and remove.
5. Run the full test suite — `pytest sg_compute__tests/` and `pytest tests/`. Both green.
6. Update reality doc — append a pointer to `team/roles/librarian/reality/changelog.md`.

## Acceptance criteria

- `sgraph_ai_service_playwright__host/` does not exist on disk.
- `pyproject.toml` does not reference the legacy path.
- `pytest` exits 0 on both test trees.
- A `team/roles/librarian/reality/changelog.md` entry records the deletion with the closing-commit hash.
- The reality doc shard at `team/roles/librarian/reality/host-control/index.md` is updated to remove the migration-shim note (if any) — `sg_compute/host_plane/` is the only authoritative source now.

## Open questions

None — orphan status was confirmed by the 2026-05-04 legacy review.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** none. Run first.

## Notes

The directory has been a copy of `sg_compute/host_plane/` since B6 (commit `c3fc219`). Diff is irrelevant — code review confirmed `host_plane/` is the only one that's been receiving updates (`Routes__Host__Auth`, `Routes__Host__Docs`, the new `pods/` rename). This brief just removes the dead twin.
