# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Spec
# CLI subgroup: sg-compute spec
#
# Commands
# ────────
#   sg-compute spec list             — print the full spec catalogue
#   sg-compute spec info <spec-id>   — print one spec entry
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_spec_catalogue, render_spec_entry
from sg_compute.core.spec.Spec__Loader                                        import Spec__Loader


app = typer.Typer(no_args_is_help=True,
                  help='Browse the spec catalogue — list known specs or show one spec in detail.')


def _loader() -> Spec__Loader:
    return Spec__Loader()


@app.command()
def list():
    """List all registered specs."""
    registry  = _loader().load_all()
    catalogue = registry.catalogue()
    render_spec_catalogue(catalogue, Console(highlight=False, width=200))


@app.command()
def info(spec_id: str = typer.Argument(..., help='Spec identifier (e.g. docker, ollama).')):
    """Show details for one spec."""
    registry = _loader().load_all()
    entry    = registry.get(spec_id)
    if entry is None:
        valid = ', '.join(registry.spec_ids())
        raise typer.BadParameter(f'unknown spec {spec_id!r}; registered: {valid}')
    render_spec_entry(entry, Console(highlight=False, width=200))
