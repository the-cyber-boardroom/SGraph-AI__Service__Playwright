# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_details
# `sg aws lambda <name> details` — full GetFunction response.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client        import Lambda__AWS__Client

console = Console()


@click.command('details')
@click.pass_context
@click.option('--json',           'as_json',        is_flag=True, default=False, help='Output as JSON.')
@click.option('--show-env-values','show_env_values', is_flag=True, default=False, help='Show env var values (masked by default).')
def cmd_details(ctx, as_json, show_env_values):
    """Show full function configuration: env vars, layers, VPC, role ARN, tracing."""
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        client  = Lambda__AWS__Client()
        details = client.get_function_details(fn_name)
        if as_json:
            data = details.json()
            if not show_env_values:
                data['environment'] = {k: '***' for k in details.environment}
            click.echo(json.dumps(data, indent=2))
            return
        tbl = Table(title=f'Details: {fn_name}', show_header=False)
        tbl.add_column('Field', style='dim')
        tbl.add_column('Value', style='cyan')
        tbl.add_row('Name',               str(details.name))
        tbl.add_row('ARN',                str(details.function_arn) or '—')
        tbl.add_row('Runtime',            str(details.runtime))
        tbl.add_row('State',              str(details.state))
        tbl.add_row('Handler',            details.handler or '—')
        tbl.add_row('Memory',             f'{details.memory_size} MB')
        tbl.add_row('Timeout',            f'{details.timeout}s')
        tbl.add_row('Role ARN',           details.role_arn or '—')
        tbl.add_row('Architecture',       details.architecture or '—')
        tbl.add_row('Tracing',            details.tracing_mode or '—')
        tbl.add_row('Ephemeral storage',  f'{details.ephemeral_storage} MB')
        tbl.add_row('KMS key',            details.kms_key_arn or '—')
        tbl.add_row('Code size',          f'{details.code_size:,} bytes' if details.code_size else '—')
        tbl.add_row('Last modified',      details.last_modified or '—')
        if details.layers:
            tbl.add_row('Layers', '\n'.join(details.layers))
        if details.environment:
            env_str = '\n'.join(
                f'{k}={v}' if show_env_values else f'{k}=***'
                for k, v in details.environment.items()
            )
            tbl.add_row('Environment', env_str)
        console.print(tbl)
