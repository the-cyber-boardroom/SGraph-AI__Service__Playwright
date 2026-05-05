# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Pod
# CLI subgroup: sg-compute pod
#
# Commands
# ────────
#   sg-compute pod list [--region X]   — list pods on a node (placeholder)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                    import Optional

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_pod_list
from sg_compute.core.pod.schemas.Schema__Pod__List                           import Schema__Pod__List


app = typer.Typer(no_args_is_help=True,
                  help='Inspect container pods running on a compute node.')


@app.command()
def list(region: Optional[str] = typer.Option('', '--region', '-r', help='AWS region (default: eu-west-2).')):

    render_pod_list(Schema__Pod__List(), Console(highlight=False, width=200))
