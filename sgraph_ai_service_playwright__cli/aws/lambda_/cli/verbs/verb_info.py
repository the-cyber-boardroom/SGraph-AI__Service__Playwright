# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_info
# `sg aws lambda <name> info` — one-screen function summary.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client        import Lambda__AWS__Client

console = Console()


@click.command('info')
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_info(ctx, as_json):
    """Show basic function metadata: name, ARN, runtime, state, memory, timeout."""
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        client  = Lambda__AWS__Client()
        details = client.get_function_details(fn_name)
        url_info = client.get_function_url(fn_name)
        if as_json:
            data = details.json()
            data['function_url'] = str(url_info.function_url) if url_info.exists else ''
            click.echo(json.dumps(data, indent=2))
            return
        tbl = Table(title=f'Lambda: {fn_name}', show_header=False)
        tbl.add_column('Field', style='dim')
        tbl.add_column('Value', style='cyan')
        tbl.add_row('Name',          str(details.name))
        tbl.add_row('ARN',           str(details.function_arn) or '—')
        tbl.add_row('Runtime',       str(details.runtime))
        tbl.add_row('State',         str(details.state))
        tbl.add_row('Handler',       details.handler or '—')
        tbl.add_row('Memory',        f'{details.memory_size} MB')
        tbl.add_row('Timeout',       f'{details.timeout}s')
        tbl.add_row('Code size',     f'{details.code_size:,} bytes' if details.code_size else '—')
        tbl.add_row('Last modified', details.last_modified or '—')
        if url_info.exists:
            tbl.add_row('URL', str(url_info.function_url))
        console.print(tbl)
