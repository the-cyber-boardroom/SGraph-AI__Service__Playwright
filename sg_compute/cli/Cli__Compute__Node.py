# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Node
# CLI subgroup: sg-compute node
#
# Commands
# ────────
#   sg-compute node list [--region X]   — list compute nodes (placeholder)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                    import Optional

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_node_list
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List


app = typer.Typer(no_args_is_help=True,
                  help='Manage compute nodes — ephemeral EC2 instances running a single spec.')


@app.command()
def list(region: Optional[str] = typer.Option('', '--region', '-r', help='AWS region (default: eu-west-2).')):
    """List all active compute nodes."""
    render_node_list(Schema__Node__List(), Console(highlight=False, width=200))
