# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__S3
# Typer group for `sg aws s3 *` commands. Bodies owned by Slice A.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='s3', help='S3 object and bucket management.', no_args_is_help=True)
