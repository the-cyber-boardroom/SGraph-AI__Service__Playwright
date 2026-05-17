# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_versions
# `sg aws lambda <name> versions` — list published versions.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client

console = Console()


@click.command('versions')
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_versions(ctx, as_json):
    """List published versions of the function."""
    fn_name  = ctx.obj['function_name']
    with spec_cli_errors():
        versions = Lambda__AWS__Client().list_versions(fn_name)
        if as_json:
            click.echo(json.dumps([v.json() for v in versions], indent=2))
            return
        if not versions:
            console.print('[dim]No published versions found.[/dim]')
            return
        tbl = Table(title=f'Versions: {fn_name}')
        tbl.add_column('Version',       style='cyan')
        tbl.add_column('Description')
        tbl.add_column('Code size',     justify='right')
        tbl.add_column('Last modified', style='dim')
        for v in versions:
            tbl.add_row(
                v.version,
                v.description or '—',
                f'{v.code_size:,} bytes' if v.code_size else '—',
                v.last_modified or '—',
            )
        console.print(tbl)
