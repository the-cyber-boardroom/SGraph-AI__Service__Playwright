# B5 Debrief — sg-compute CLI

**Date:** 2026-05-02
**Branch:** `claude/sg-compute-b4-control-plane-xbI4j`
**Commit:** ddd3ff8
**Tests:** 21 new, 190 total (all green)

---

## What shipped

`sg_compute/cli/` — the typer CLI for the `sg-compute` package.

### New files (13)

| File | Purpose |
|------|---------|
| `cli/__init__.py` | Package marker |
| `cli/Cli__Compute.py` | Root typer app; wires 4 subgroups |
| `cli/Cli__Compute__Spec.py` | `spec list` + `spec info <id>` |
| `cli/Cli__Compute__Node.py` | `node list` (placeholder) |
| `cli/Cli__Compute__Pod.py` | `pod list` (placeholder) |
| `cli/Cli__Compute__Stack.py` | `stack list` (placeholder) |
| `cli/Renderers.py` | Rich renderers for all 5 output types |
| `scripts/sg_compute_cli.py` | Entry point for `python -m scripts.sg_compute_cli` |
| `sg_compute__tests/cli/__init__.py` | Test package marker |
| `sg_compute__tests/cli/test_Cli__Compute.py` | 8 root-app integration tests |
| `sg_compute__tests/cli/test_Cli__Compute__Spec.py` | 7 spec subgroup tests |
| `sg_compute__tests/cli/test_Renderers.py` | 6 renderer unit tests |

Also updated `pyproject.toml` to register `sg-compute = "scripts.sg_compute_cli:app"` as a console script.

### CLI surface

```
sg-compute spec list                    → Rich table of all registered specs
sg-compute spec info <spec-id>         → Detail panel for one spec
sg-compute node  list [--region X]     → "No nodes found." (placeholder)
sg-compute pod   list [--region X]     → "No pods found."  (placeholder)
sg-compute stack list [--region X]     → "No stacks found." (placeholder)
```

---

## Key decision: script filename

The entry script was initially `scripts/sg_compute.py`. When run via
`python scripts/sg_compute.py`, Python adds `scripts/` to sys.path, which
causes `sg_compute` to resolve to the script file itself rather than the
`sg_compute/` package. Renamed to `sg_compute_cli.py` — no sys.path
manipulation needed; module path is `scripts.sg_compute_cli:app`.

---

## Failures encountered

### Good failures

**`no_args_is_help=True` exits with code 2**

typer subgroups with `no_args_is_help=True` exit with code 2 when invoked
with no arguments (the standard typer/click behaviour for "missing command").
Test assertion `assert result.exit_code == 0` failed. Fixed by asserting
only on output content, not exit code.

---

## What is NOT here yet

- `node list` / `pod list` / `stack list` return empty placeholders — real
  AWS integration requires `Node__Manager` wiring (B6+)
- `spec info` shows a flat text block — tabular Rich panel is easy to add
  when the field set stabilises
- `sg-compute node create --spec docker` — create path is B6+

## Next steps

- **B6**: Host plane rename (`containers` → `pods`)
