# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute
# Root typer app for the sg-compute CLI.
#
# Usage
# ─────
#   sg-compute spec list
#   sg-compute spec info <spec-id>
#   sg-compute node list [--region X]
#   sg-compute pod  list [--region X]
#   sg-compute stack list [--region X]
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sg_compute.cli.Cli__Compute__Node  import app as node_app
from sg_compute.cli.Cli__Compute__Pod   import app as pod_app
from sg_compute.cli.Cli__Compute__Spec  import app as spec_app
from sg_compute.cli.Cli__Compute__Stack import app as stack_app


app = typer.Typer(no_args_is_help=True,
                  help='sg-compute — ephemeral EC2 compute nodes managed by spec.')

app.add_typer(spec_app , name='spec' , help='Browse the spec catalogue.')
app.add_typer(node_app , name='node' , help='Manage compute nodes.')
app.add_typer(pod_app  , name='pod'  , help='Inspect container pods on nodes.')
app.add_typer(stack_app, name='stack', help='Manage multi-node stacks.')
