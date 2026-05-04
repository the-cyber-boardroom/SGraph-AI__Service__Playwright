# BV2.17 — Delete `/containers/*` aliases on the sidecar

## Goal

The v0.1.154 sidecar enhancement brief kept `/containers/*` as an alias next to `/pods/*` for the legacy UI panel. Once frontend FV2.8 ships (every UI consumer uses `/pods/*`), the alias is dead weight that confuses the API surface.

## Tasks

1. **Verify FV2.8 has shipped** — `grep -rn '/containers/' sgraph_ai_service_playwright__api_site/` returns zero hits (or only test-data hits, not live URL constructions).
2. **Delete `Routes__Host__Containers`** from `sg_compute/host_plane/fast_api/routes/`.
3. **Remove the alias mount** from `Fast_API__Host__Control.setup_routes()`.
4. **Update `architecture/03__sidecar-contract.md`** §4.4 — remove the "Compatibility aliases" subsection.
5. **Update reality doc.**

## Acceptance criteria

- `Routes__Host__Containers.py` does not exist.
- `Fast_API__Host__Control` mounts only `/pods/*` (and `/containers/*` returns 404).
- Frontend smoke test passes — dashboard works with the alias gone.
- Architecture doc has no mention of the alias.

## Open questions

None.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** **Frontend FV2.8 must ship first.** Backend gates this phase on confirmation that the frontend has migrated to `/pods/*`.

## Notes

This is a small phase that removes confusion. After it lands, the sidecar API surface is clean — no aliases, one URL per resource.
