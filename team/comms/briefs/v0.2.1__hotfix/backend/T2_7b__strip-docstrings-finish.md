# T2.7b — Finish the docstring sweep

⚠ **Tier 2 — finish.** T2.7 (commit `af65c2c`) + T2.7 redo (commit `552e5cb`) covered CLI + Spec__Loader/Resolver. **Docstrings remain in 10+ other files.**

## What's still wrong

Verified by `grep -rln '^\s*"""' sg_compute/ sg_compute_specs/`:

- `sg_compute/platforms/ec2/user_data/Section__Base.py`
- `sg_compute/platforms/ec2/user_data/Section__Docker.py`
- `sg_compute/platforms/ec2/user_data/Section__Env__File.py`
- `sg_compute/platforms/ec2/user_data/Section__Nginx.py`
- `sg_compute/platforms/ec2/user_data/Section__Node.py`
- `sg_compute/platforms/ec2/user_data/Section__Shutdown.py`
- `sg_compute/platforms/ec2/user_data/Section__Sidecar.py`
- `sg_compute_specs/vnc/service/Vnc__User_Data__Builder.py`
- `sg_compute_specs/vnc/service/Vnc__Compose__Template.py`
- `sg_compute_specs/vnc/service/Vnc__Interceptor__Resolver.py`

…and likely more. The first T2.7 commit message claimed "all CLI and spec files" — this is the inverse claim of the project rule (no docstrings, period).

## Tasks

1. **Sweep with grep** — `grep -rln '^\s*"""' sg_compute/ sg_compute_specs/` — list every hit.
2. **For each file**, open and audit each docstring:
   - **Pure WHAT** (visible from method name + signature) — DELETE.
   - **Genuine WHY** (non-obvious reason; subtle invariant; workaround for a specific bug) — convert to a single-line `#` comment above the method.
3. **Sweep file-level docstrings too** — module-level `"""..."""` blocks. Convert to `# ═══════════════════════════════════════════════════════════════════════════════` 80-char headers (the project convention).
4. **Verify** — `grep -rln '^\s*"""' sg_compute/ sg_compute_specs/` returns zero hits.

## Acceptance criteria

- `grep -rln '^\s*"""' sg_compute/ sg_compute_specs/` returns zero hits (excluding string literals that contain `"""` legitimately — verify each).
- All tests pass.
- Module-level docstrings replaced with 80-char `═══` headers.
- No WHY content lost — any genuine context preserved as inline `#` comments.
- Debrief classifies T2.7 (the previous shipment) as `PARTIAL`-marked-COMPLETE → **bad failure** under the new debrief vocabulary.

## "Stop and surface" check

If you find a docstring that captures a subtle architectural reason that doesn't fit one line: **STOP**. Either:
- The reason belongs in the architecture doc (`team/comms/briefs/v0.2.0__sg-compute__architecture/`), not in code — surface to Architect.
- The reason is genuinely needed in code — multi-line `#` comment is allowed for genuine WHY content.

Don't leave the docstring "because it's useful". The rule is hard.

## Live smoke test

Run the test suite. Run `sg-compute --help`. Run `python -c "from sg_compute.platforms.ec2.user_data.Section__Sidecar import Section__Sidecar; print(Section__Sidecar.__doc__)"` → expect `None`.

## Source

Executive review T2-implementation §"T2.7 — commit lies" (2026-05-05 14:00). Verified by `grep -rln '^\s*"""'` 2026-05-05 14:30.
