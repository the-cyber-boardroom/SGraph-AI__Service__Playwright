# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Creds
# Typer group for `sg aws creds *` commands. Bodies owned by Slice G.
# Note: distinct from `sg aws credentials` (long-lived keys store).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app   = typer.Typer(name='creds', help='Scoped STS credential delivery (per-command temporary creds).', no_args_is_help=True)
scope = typer.Typer(name='scope', help='Scope catalogue management.',                                    no_args_is_help=True)
audit = typer.Typer(name='audit', help='Credential assumption audit log.',                               no_args_is_help=True)

app.add_typer(scope, name='scope')
app.add_typer(audit, name='audit')
