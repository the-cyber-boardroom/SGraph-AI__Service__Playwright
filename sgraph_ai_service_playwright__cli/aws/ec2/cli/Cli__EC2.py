# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2
# Typer group for `sg aws ec2 *` commands. Bodies owned by Slice B.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='ec2', help='EC2 instance management.', no_args_is_help=True)
