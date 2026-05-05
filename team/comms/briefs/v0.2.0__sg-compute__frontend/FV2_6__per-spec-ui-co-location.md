# FV2.6 — Per-spec UI co-location at `sg_compute_specs/<name>/ui/`

## Goal

Each spec's card + detail UI components currently live under `sgraph_ai_service_playwright__api_site/plugins/<name>/` and `components/sp-cli/sp-cli-<name>-detail/`. Move them into the spec's own folder at `sg_compute_specs/<spec_id>/ui/` so:

- A spec installed from a separate package (per the cross-repo policy — `s3_server`) can ship its UI alongside its Python service.
- Per-spec changes don't require touching the dashboard tree.
- The catalogue can describe what UI assets each spec ships.

This phase moves UI for migrated specs **one spec per session**. Don't try to do all 12 in one PR.

## Architect decisions (2026-05-05)

The open questions from the original brief were resolved:

**1. Serving mechanism → FastAPI `StaticFiles` mount (Option A)**

Mount `sg_compute_specs/<id>/ui/` at `/api/specs/<id>/ui/` via `app.mount(...)`. This is the right choice because:
- Zero route logic; no streaming boilerplate.
- Aligns with the future serving path: CF+S3 or `tools.sgraph.ai` (also CF+S3). Static files mounted this way can be swapped for a CDN origin with no dashboard changes.

Backend slice needed: one `app.mount()` call per registered spec in `Fast_API__Compute`, iterating `Spec__Loader.load_all()`.

**2. Versioning → IFD versioning is correct**

All web assets (`.js`/`.html`/`.css`) keep the `v0/v0.1/v0.1.0` path convention. The `StaticFiles` mount serves them verbatim at `/api/specs/<id>/ui/card/v0/v0.1/v0.1.0/<file>`. Long `Cache-Control` is appropriate since the path is immutable by IFD rules.

**3. Timing → run after FV2.12**

FV2.12 renames all `sp-cli-*` → `sg-compute-*`. Running FV2.6 before FV2.12 would mean the co-located files still carry the old `sp-cli-` prefix, requiring a second rename pass inside `sg_compute_specs/`. Waiting until after FV2.12 means the moved files land with their final names immediately, and the dashboard script-tag paths don't break between phases.

**Updated execution order: FV2.12 → FV2.6**

FV2.12 is therefore un-deferred from v0.3 — it must run before FV2.6 can proceed.

---

## Tasks (per spec — repeat for each migration)

1. **Move card** — `sgraph_ai_service_playwright__api_site/plugins/<name>/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/card/v0/v0.1/v0.1.0/`. Use `git mv`.
2. **Move detail** — `components/sp-cli/sg-compute-<name>-detail/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/detail/v0/v0.1/v0.1.0/`. (Note: uses `sg-compute-` prefix post-FV2.12.)
3. **Update `admin/index.html`** — script tags for the spec are now loaded from `/api/specs/<id>/ui/card/sg-compute-<name>-card.js` etc.
4. **Backend** — `Fast_API__Compute` must already have `StaticFiles` mounts in place (backend slice BV2.x, unblocked by this decision).
5. **Verify the spec's card + detail still render** in the dashboard.
6. Update reality doc.

## Recommended migration order (post-FV2.12)

1. `docker` (pilot — simplest migrated spec with full card+detail)
2. `podman`, `vnc`, `neko`, `prometheus`, `opensearch`, `elastic`, `firefox`

## Acceptance criteria (per spec)

- `sg_compute_specs/<name>/ui/card/...` + `sg_compute_specs/<name>/ui/detail/...` exist with `sg-compute-` prefix names.
- Dashboard tree no longer has `plugins/<name>/...` or `components/sp-cli/sg-compute-<name>-detail/...`.
- The spec's card + detail render correctly in the dashboard via `/api/specs/<id>/ui/...`.
- Reality doc updated.

## Blocks / Blocked by

- **Blocks:** FV2.13 (eventual dashboard move to `sg_compute/frontend/`).
- **Blocked by:** FV2.12 (prefix rename — DONE ✅). Also blocked by backend **BV2.19** (`StaticFiles` mount in `Fast_API__Compute` — see `team/comms/briefs/v0.2.0__sg-compute__backend/BV2_19__spec-ui-static-files.md`).

## Notes

- This phase is **per-spec, one session per spec**.
- The `StaticFiles` mount approach means serving UI assets requires the `sg_compute_specs` package to be importable/accessible by the running control-plane process — confirm this is true in Lambda + local dev + CI before the first spec migration.
