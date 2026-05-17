# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__CloudTrail
# Typer group for `sg aws cloudtrail *` commands. Bodies owned by Slice F.
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app    = typer.Typer(name='cloudtrail', help='CloudTrail events and trail management (read-only).', no_args_is_help=True)
events = typer.Typer(name='events',     help='Query CloudTrail events.',                            no_args_is_help=True)
trail  = typer.Typer(name='trail',      help='Inspect CloudTrail trails.',                          no_args_is_help=True)

app.add_typer(events, name='events')
app.add_typer(trail,  name='trail')
