# BV2.9 — Migrate `__cli/vault/` → `sg_compute/vault/`

## Goal

The vault layer (Vault primitives + per-plugin writer) has no equivalent under `sg_compute/`. It currently lives at `sgraph_ai_service_playwright__cli/vault/` and is consumed by the dashboard's vault-pickers, the firefox spec's vault-write needs, and the eventual storage-spec call-log persistence.

The original v0.1.140 brief `post-fractal-ui__backend/04__vault-write-contract.md` defined a per-plugin vault-write contract with firefox as the first consumer. Per the v0.2 audit, the first consumer is now ambiguous (sidecar boot artefacts, S3 call-log, firefox secrets all compete). **Architect call before this phase: re-scope the contract to be capability-agnostic — first to ship sets the precedent.**

## Tasks

1. **Migrate `sgraph_ai_service_playwright__cli/vault/`** → `sg_compute/vault/`. Use `git mv` to preserve history.
2. **Replace `Vault__Plugin__Writer`** terminology with `Vault__Spec__Writer` (rename per the v0.2 taxonomy).
3. **Update imports** across `sg_compute_specs/`, the control plane, and any code that depends on vault.
4. **Schema renames:** `Schema__Vault__Plugin__Write__Receipt` → `Schema__Vault__Spec__Write__Receipt`; field `plugin_id` → `spec_id`. Update consumers.
5. **Endpoint path:** if `PUT /vault/plugin/{plugin_id}/...` is exposed, rename to `/api/vault/spec/{spec_id}/...` and mount on `Fast_API__Compute`. Keep old paths as deprecation aliases for 1 release.
6. **Tests:** retarget tests to the new path; **drop any `unittest.mock.patch`** uses; use in-memory composition.
7. **Update vault-related briefs** at `team/comms/briefs/v0.1.140__post-fractal-ui__backend/04__vault-write-contract.md` — mark superseded by this phase.
8. **Update reality doc** — vault is its own domain.

## Acceptance criteria

- `sg_compute/vault/` exists; legacy `__cli/vault/` is a shim or deleted (BV2.12 deletes formally).
- All references to `Vault__Plugin__Writer` / `plugin_id` in vault context are renamed.
- Endpoint paths follow `/api/vault/spec/{spec_id}/...`.
- All vault tests pass; no mocks.
- Reality doc has a `team/roles/librarian/reality/vault/index.md` entry.

## Open questions

- **First consumer.** Architect to lock before this phase. Recommendation: design for binary blobs + metadata receipts; first consumer is whichever spec ships its vault-write feature first.
- **Cross-spec sharing.** Brief 04 used `_global` as a stack-id sentinel for plugin-wide blobs. Keep — rename `_global` to `_shared` to reflect "shared across all nodes of a spec".

## Blocks / Blocked by

- **Blocks:** any spec that wants to ship vault-write functionality (firefox MITM scripts, s3_server call log, etc.).
- **Blocked by:** BV2.7 (Tier-1 migration) — vault depends on `__cli/aws/` and `__cli/core/`, which BV2.7 moves.

## Notes

This phase carries the most "what should the contract really look like?" risk. Pair with Architect for the contract review. The original brief is at `team/comms/briefs/v0.1.140__post-fractal-ui__backend/04__vault-write-contract.md`; treat it as the starting point but don't assume firefox is the first consumer.
