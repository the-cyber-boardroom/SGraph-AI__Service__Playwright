# BV2.6 — Per-spec `cli/` + `sg-compute spec <id> <verb>` dispatcher

## Goal

The audit found no spec has a `cli/` subdirectory and the per-spec dispatcher in B5's CLI cannot work. Per the v0.2 ratified decisions, `cli/` is **optional** — specs without operator-facing verbs skip it. But specs that DO have spec-specific verbs need the contract.

## Tasks

1. **Decide which specs need a `cli/`.** Architect call. Likely candidates (need spec-specific verbs):
   - `firefox` — vault-write commands (set credentials, upload MITM script)
   - `elastic` — import/export saved searches
   - `prometheus` — query helpers
   - Likely skips: `playwright`, `mitmproxy`, `ollama`, `open_design`, `docker`, `podman`, `vnc`, `neko`, `opensearch` (the generic CRUD verbs are sufficient).
2. **For each spec that needs `cli/`** — build `sg_compute_specs/<spec>/cli/<spec>_commands.py` with a Typer sub-app.
3. **Update `sg_compute/cli/Cli__Compute__Spec.py`** — add the dispatcher:
   - `sg-compute spec <spec_id> <verb> ...` looks up the spec's manifest.
   - Imports `sg_compute_specs.<spec_id>.cli.<spec>_commands` if the file exists.
   - Mounts the Typer sub-app dynamically; falls through with a clear error if no `cli/`.
4. **Add `sg-compute spec validate <spec_id>`** — validates a spec's `MANIFEST` against `Schema__Spec__Manifest__Entry`. Useful for spec authors.
5. **Add `sg-compute spec list-verbs <spec_id>`** — lists the spec-specific verbs available; clear "no spec-specific verbs" message if `cli/` is missing.

## Acceptance criteria

- At least 1 spec (e.g. `firefox`) has a real `cli/` with at least 2 working spec-specific verbs.
- `sg-compute spec docker create --instance-size small` (generic verb) still works.
- `sg-compute spec firefox set-credentials --username u --password p <node-id>` (spec-specific verb) works end-to-end.
- `sg-compute spec validate firefox` passes; `sg-compute spec validate <broken>` fails with a clear error.
- `sg-compute spec list-verbs ollama` prints "no spec-specific verbs".

## Open questions

- **CLI argument ordering.** Should it be `sg-compute spec <id> <verb>` or `sg-compute <verb> --spec <id>`? Recommend the former — matches the Typer mounting model.

## Blocks / Blocked by

- **Blocks:** none strict.
- **Blocked by:** none. Independent.

## Notes

Per-spec verbs are an **operator** convenience. Tools that need scripted access continue to use the HTTP API (`POST /api/specs/firefox/credentials/...`). The CLI is sugar.
