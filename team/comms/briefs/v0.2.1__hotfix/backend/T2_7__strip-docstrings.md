# T2.7 — Strip 6 docstrings introduced in BV2.6

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

Project rule: **no docstrings**. Single-line inline comments only where the WHY is non-obvious. BV2.6 introduced 6 docstrings in `Cli__Compute__Spec.py` and `Cli__Docker.py`.

## Tasks

1. `grep -rn '"""' --include="*.py" sg_compute/cli/ sg_compute_specs/*/cli/` — list every docstring (triple-quoted block, leading or trailing).
2. For each:
   - If it's just describing what the method does (visible from the name + signature) — **delete**.
   - If it captures a genuinely non-obvious WHY — convert to a single-line `#` comment above the method.
3. Sweep beyond just BV2.6 — there may be other docstrings introduced elsewhere in the recent backend work.

## Acceptance criteria

- `grep -rn '^\s*"""' --include="*.py" sg_compute/ sg_compute_specs/` returns zero hits (or only inside string literals).
- All affected files compile + tests pass.
- Inline `#` comments preserve any genuine WHY content.

## "Stop and surface" check

If a docstring captures a genuine architectural reason that doesn't fit one line: **STOP**. Either the architecture has a missing comment in the architecture doc, or the rule needs amending. Surface to Architect — don't just leave the docstring.

## Live smoke test

Run the CLI: `sg-compute --help` still works. `sg-compute spec docker create --help` still works.

## Source

Executive review Tier-2; backend-early review §"Top contract violation #1".
