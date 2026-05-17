# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Fargate
# Typer group for `sg aws fargate *` commands. Bodies owned by Slice C.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='fargate', help='ECS Fargate cluster and task management.', no_args_is_help=True)
