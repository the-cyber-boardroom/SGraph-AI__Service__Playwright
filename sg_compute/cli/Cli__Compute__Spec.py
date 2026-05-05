# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Spec
# CLI subgroup: sg-compute spec
#
# Commands
# ────────
#   sg-compute spec list             — print the full spec catalogue
#   sg-compute spec info <spec-id>   — print one spec entry
#   sg-compute spec <spec-id> list   — list stacks for a spec  (via per-spec CLI)
#   sg-compute spec <spec-id> info   — info for a spec stack    (via per-spec CLI)
#   sg-compute spec <spec-id> create — create a spec stack      (via per-spec CLI)
#   sg-compute spec <spec-id> delete — delete a spec stack      (via per-spec CLI)
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_spec_catalogue, render_spec_entry
from sg_compute.cli.Spec__CLI__Loader                                         import Spec__CLI__Loader
from sg_compute.core.spec.Spec__Loader                                        import Spec__Loader


app = typer.Typer(no_args_is_help=True,
                  help='Browse the spec catalogue or manage stacks for a specific spec.')


def _loader() -> Spec__Loader:
    return Spec__Loader()


def _mount_spec_sub_apps() -> None:
    registry  = _loader().load_all()
    spec_ids  = registry.spec_ids()
    cli_apps  = Spec__CLI__Loader().load_all(spec_ids)
    for spec_id, sub_app in cli_apps.items():
        manifest = registry.get(spec_id)
        help_str = f'Manage {spec_id} stacks.'
        if manifest:
            help_str = f'Manage {manifest.display_name} stacks.'
        app.add_typer(sub_app, name=spec_id, help=help_str)


_mount_spec_sub_apps()


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
