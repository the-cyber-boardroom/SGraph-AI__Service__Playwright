# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Iam__Graph
# Typer group for `sg aws iam graph *` commands. Bodies owned by Slice D.
# Registered in Cli__Iam.py via iam_app.add_typer(graph_app, name='graph').
# ═══════════════════════════════════════════════════════════════════════════════

import typer

graph_app = typer.Typer(name='graph', help='IAM-as-graph discovery, filtering, and cleanup.', no_args_is_help=True)
