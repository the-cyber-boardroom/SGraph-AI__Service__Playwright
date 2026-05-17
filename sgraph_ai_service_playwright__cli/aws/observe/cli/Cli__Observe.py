# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Observe
# Typer group for `sg aws observe *` commands. Bodies owned by Slice H.
# Folder is `observe` (not `observability`) to avoid clash with the existing
# __cli/observability/ AMP/OpenSearch/AMG infra package.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='observe', help='Unified observability REPL (S3, CloudWatch, CloudTrail).', no_args_is_help=True)
