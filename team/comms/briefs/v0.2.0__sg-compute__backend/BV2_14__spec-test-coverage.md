# BV2.14 — Pad spec test coverage; drop `unittest.mock.patch`

## Goal

Code review (R5) found that 8 specs (`docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox`) have **only `User_Data__Builder` + `Stack__Mapper` + manifest tests** — zero Routes tests, zero Service tests. Only `mitmproxy` (12 tests) is the model.

Code review also found `unittest.mock.patch` violations in `sg_compute__tests/` (8 sites in `test_Routes__Compute__Nodes.py` already addressed by BV2.4; sweep elsewhere).

## Tasks

1. **For each of the 8 under-covered specs**, add at minimum:
   - 1 Routes test — exercises the spec's `Routes__Spec__<Pascal>__Stack` against a fake EC2 platform. Asserts response shape matches `Schema__<Pascal>__Create__Response`.
   - 1 Service test — exercises `<Pascal>__Service.create_node / get_node_info / delete_node` against a fake platform. Asserts the service constructs valid user-data + tags.
2. **Pattern after `mitmproxy` tests** — they are the model. Use in-memory composition, no mocks.
3. **Sweep `sg_compute__tests/` and `sg_compute_specs/<*>/tests/` for `unittest.mock.patch`** — every hit becomes an in-memory composition. Common patterns:
   - Patching `boto3.client` → use `osbot-aws`'s test helpers or pass a fake AWS client through the constructor.
   - Patching HTTP calls → use a fake HTTP handler instance, not a patch.
   - Patching env vars → use Type_Safe constructor injection.
4. **Track coverage delta** — record before/after test counts in the PR description. Target: every spec ≥ 8 tests minimum.
5. Update reality doc.

## Acceptance criteria

- Every of the 12 specs has ≥ 8 tests covering: manifest, schemas, user_data builder, stack mapper, AWS client, service, ≥1 route.
- `grep -rln 'unittest.mock' sg_compute__tests/ sg_compute_specs/` returns zero hits.
- All tests pass.
- Reality doc updated.

## Open questions

None.

## Blocks / Blocked by

- **Blocks:** BV2.18 (TestPyPI publish) — quality bar for release.
- **Blocked by:** BV2.13 (canonical layout) recommended first.

## Notes

Use the mitmproxy test suite as the reference. Don't introduce new test infrastructure if existing patterns work. `register_*__in_memory()` composition is the gold standard.
