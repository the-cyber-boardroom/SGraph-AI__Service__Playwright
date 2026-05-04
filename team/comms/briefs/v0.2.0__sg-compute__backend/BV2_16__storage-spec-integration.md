# BV2.16 — Storage spec category + `s3_server` cross-repo discovery

## Goal

The v0.27.2 arch brief introduced storage-class specs. The first instance (`s3_server`) lives in its own repo (`sgraph-ai/SG-Compute__Spec__Storage-S3`). This phase wires the SDK side so an installed `sg-compute-spec-storage-s3` package is discovered automatically.

## Tasks

1. **Verify `OBJECT_STORAGE` is in `Enum__Spec__Capability`**. If not, add it (Architect-locked per v0.2 ratification).
2. **Document the storage-spec category** in `architecture/01__architecture.md` §8 ("Storage specs") — already drafted, expand with the `OBJECT_STORAGE` capability requirement and the operation-mode taxonomy reference.
3. **Verify cross-repo discovery works** — install the external spec package locally:
   ```
   pip install -e ../SG-Compute__Spec__Storage-S3
   ```
   Then run `sg-compute spec list` — the `s3_server` spec should appear.
4. **Add a smoke test** at `sg_compute__tests/core/spec/test_Spec__Loader__entry_points.py` — verifies `Spec__Loader._load_from_entry_points` works with a controlled fixture (a fake spec package installed via tox or pytest-plugin).
5. **Document the cross-repo policy** in `architecture/01__architecture.md` §9 ("Cross-repo policy") — already drafted, ratify.
6. **Document the `sg-compute-spec-<name>` PyPI naming convention** for spec repos.
7. Update reality doc.

## Acceptance criteria

- `OBJECT_STORAGE` is in the locked `Enum__Spec__Capability`.
- Architecture doc §8 + §9 finalised.
- A storage spec installed from a separate package is discovered + listed in `GET /api/specs`.
- Cross-repo policy doc is final.
- Reality doc updated.

## Open questions

- **Operation-mode taxonomy generalisation timing.** Brief 1.6 (`v0.1.162__s3-storage-node`) introduces FULL_LOCAL/FULL_PROXY/HYBRID/SELECTIVE. v0.2 lets `s3_server` validate the pattern — does it generalise into the SDK? Defer to v0.3.0; document the deferral here.

## Blocks / Blocked by

- **Blocks:** none — storage specs ship from their own repos and are discovered automatically once installed.
- **Blocked by:** none.

## Notes

This phase is mostly **documentation + discovery validation**. The actual `s3_server` implementation lives in `sgraph-ai/SG-Compute__Spec__Storage-S3` and is not in this brief's scope. Pair with the storage-spec lead for the smoke test.
