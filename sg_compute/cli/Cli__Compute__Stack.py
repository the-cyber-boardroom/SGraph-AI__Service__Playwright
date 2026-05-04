# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Stack
# CLI subgroup: sg-compute stack
#
# Commands
# ────────
#   sg-compute stack list [--region X]   — list multi-node stacks (placeholder)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                    import Optional

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_stack_list
from sg_compute.core.stack.schemas.Schema__Stack__List                       import Schema__Stack__List


app = typer.Typer(no_args_is_help=True,
                  help='Manage multi-node stacks (compose two or more specs together).')


@app.command()
def list(region: Optional[str] = typer.Option('', '--region', '-r', help='AWS region (default: eu-west-2).')):
    """List all active multi-node stacks."""
    render_stack_list(Schema__Stack__List(), Console(highlight=False, width=200))
