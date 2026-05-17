# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_aliases
# `sg aws lambda <name> aliases` — list Lambda aliases.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client

console = Console()


@click.command('aliases')
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_aliases(ctx, as_json):
    """List aliases defined for the function."""
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        aliases = Lambda__AWS__Client().list_aliases(fn_name)
        if as_json:
            click.echo(json.dumps([a.json() for a in aliases], indent=2))
            return
        if not aliases:
            console.print('[dim]No aliases found.[/dim]')
            return
        tbl = Table(title=f'Aliases: {fn_name}')
        tbl.add_column('Alias',       style='cyan')
        tbl.add_column('Version')
        tbl.add_column('Description')
        for a in aliases:
            tbl.add_row(a.alias_name, a.function_version, a.description or '—')
        console.print(tbl)
