# FV2.13 — Move dashboard to `sg_compute/frontend/` (deferred to v0.3)

## Status

**DEFERRED to v0.3.0.** This phase is documented here for completeness but is not on the v0.2.x execution path.

## Goal (when it runs)

Move `sgraph_ai_service_playwright__api_site/` to `sg_compute/frontend/`. After FV2.12, every component is already named `sg-compute-*`; the move is just a directory relocation with import-path updates.

## Tasks (preview)

1. `git mv sgraph_ai_service_playwright__api_site sg_compute/frontend`.
2. Update all `<script src="...">` paths in served HTML.
3. Update `pyproject.toml` package data lists.
4. Update CI / Docker references if any.
5. Smoke test every view.

## Why deferred

- v0.2.x is focused on stabilising the **functional surface** (API, sidecar, lifecycle).
- FV2.12 (cosmetic rename) is already a large-blast-radius sweep; pairing it with a directory move multiplies risk.
- A separate v0.3.0 brief — `team/comms/briefs/v0.3.0__sg-compute__frontend-relocation/` — will own this phase.

## Notes

The rationale for the eventual move: keeping the dashboard inside `sg_compute/` packages it alongside the SDK, which simplifies static-asset serving from the spec catalogue and makes the eventual repo extraction (`sgraph-ai/SG-Compute`) cleaner.

For v0.2.x, the dashboard stays where it is.
