# FV2.6 — Per-spec UI co-location at `sg_compute_specs/<name>/ui/`

## Goal

Each spec's card + detail UI components currently live under `sgraph_ai_service_playwright__api_site/plugins/<name>/` and `components/sp-cli/sp-cli-<name>-detail/`. Move them into the spec's own folder at `sg_compute_specs/<spec_id>/ui/` so:

- A spec installed from a separate package (per the cross-repo policy — `s3_server`) can ship its UI alongside its Python service.
- Per-spec changes don't require touching the dashboard tree.
- The catalogue can describe what UI assets each spec ships.

This phase moves UI for migrated specs **one spec per session**. Don't try to do all 12 in one PR.

## Tasks (per spec — repeat for each migration)

1. **Move card** — `sgraph_ai_service_playwright__api_site/plugins/<name>/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/card/v0/v0.1/v0.1.0/`. Use `git mv`.
2. **Move detail** — `components/sp-cli/sp-cli-<name>-detail/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/detail/v0/v0.1/v0.1.0/`.
3. **Update `admin/index.html`** — script tags for the spec are now loaded from `/api/specs/<id>/ui/card/sp-cli-<name>-card.js` (etc.) instead of relative paths.
4. **Backend dependency** — if the backend doesn't yet serve `GET /api/specs/<id>/ui/<path>`, file a ticket + use a temporary symlink or static-files mount in the meantime. **Open question for Architect: endpoint vs StaticFiles.**
5. **Verify the spec's card + detail still render** in the dashboard.
6. **Update the spec's `README.md`** — note the UI assets are co-located.
7. Update reality doc.

## Recommended migration order

Start with the smallest-surface specs so the pattern stabilises before touching the heavier ones:

1. `mitmproxy` (already canonical; least UI surface)
2. `playwright` (no per-spec UI today; trivial migration — just create `ui/` folders)
3. `docker`, `podman` (similar shape)
4. `vnc`, `neko` (sg-remote-browser pattern)
5. `prometheus`, `opensearch`, `elastic` (data specs, similar shapes)
6. `firefox` (most complex; do last when the pattern is solid)

## Acceptance criteria (per spec)

- `sg_compute_specs/<name>/ui/card/...` + `sg_compute_specs/<name>/ui/detail/...` exist.
- Dashboard tree no longer has `plugins/<name>/...` or `components/sp-cli/sp-cli-<name>-detail/...`.
- The spec's card + detail render correctly in the dashboard.
- Backend serves the UI assets at `/api/specs/<id>/ui/...`.
- Reality doc updated.

## Open questions

- **Backend serving mechanism** — endpoint vs `StaticFiles` mount. Architect + UI Architect call. Recommend an endpoint with caching headers, so per-spec UI can be versioned independently from the dashboard.

## Blocks / Blocked by

- **Blocks:** FV2.13 (eventual dashboard move to `sg_compute/frontend/`).
- **Blocked by:** FV2.3 (catalogue loader) — the catalogue tells the dashboard where to load UI from.

## Notes

This phase is **per-spec, one session per spec**. After all 12 specs are migrated, the dashboard tree no longer holds per-spec UI; everything lives in the spec's folder.
