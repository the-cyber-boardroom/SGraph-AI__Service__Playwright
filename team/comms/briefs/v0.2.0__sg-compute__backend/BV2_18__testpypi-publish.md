# BV2.18 — TestPyPI publish + `RELEASE.md`

## Goal

v0.2.0 ships with both wheels building. v0.2.x should validate via TestPyPI before the first real PyPI publish. Document the release workflow.

## Tasks

1. **Build both wheels:**
   ```
   python -m build sg_compute/
   python -m build sg_compute_specs/
   ```
2. **Publish to TestPyPI** (requires TestPyPI token). Use `twine upload --repository testpypi`.
3. **Smoke test in a fresh virtualenv:**
   ```
   python -m venv /tmp/sg-compute-test
   source /tmp/sg-compute-test/bin/activate
   pip install -i https://test.pypi.org/simple/ sg-compute sg-compute-specs
   sg-compute spec list   # → 12 specs
   sg-compute spec validate firefox   # → OK
   ```
4. **Verify wheel contents:**
   ```
   unzip -l dist/sg_compute-*.whl | grep tests   # → 0 hits
   unzip -l dist/sg_compute_specs-*.whl | grep tests   # → 0 hits
   ```
5. **Document release workflow** at `sg_compute/RELEASE.md`:
   - Pre-flight checks (CI green; reality doc up to date; changelog entry).
   - Build commands.
   - TestPyPI publish.
   - Smoke test.
   - Real PyPI publish.
   - Tag the git ref.
   - Update `team/roles/librarian/reality/changelog.md`.
6. **Plan v0.2.1 patch release notes.**
7. Update reality doc.

## Acceptance criteria

- Both packages installable from TestPyPI in a fresh venv.
- `sg-compute spec list` returns 12 specs against the installed catalogue.
- Wheels contain zero test files.
- `sg_compute/RELEASE.md` documents the workflow end-to-end.
- v0.2.1 release notes drafted.

## Open questions

- **Real PyPI publish timing.** Recommend: ship to real PyPI only after BV2.13 + BV2.14 (canonical layout + test coverage) land — first impressions matter.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** BV2.13 (canonical layout) + BV2.14 (test coverage) recommended first.

## Notes

This phase is the deliverable that makes `sg-compute` a usable Python package for outside consumers. Pair with DevOps for the publish credentials.
