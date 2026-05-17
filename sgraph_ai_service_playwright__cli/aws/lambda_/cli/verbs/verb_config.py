# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_config
# `sg aws lambda <name> config` — editable configuration fields.
# `sg aws lambda <name> config set [options]` — mutate config fields.
# Mutations gated by SG_AWS__LAMBDA__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client        import Lambda__AWS__Client

console = Console()


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise SystemExit(1)


@click.group('config', invoke_without_command=True)
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def cmd_config(ctx, as_json):
    """Show or update editable config: handler, runtime, memory, timeout, env vars."""
    if ctx.invoked_subcommand is not None:
        return
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        client  = Lambda__AWS__Client()
        details = client.get_function_details(fn_name)
        if as_json:
            data = {
                'handler'      : details.handler,
                'runtime'      : str(details.runtime),
                'memory_size'  : details.memory_size,
                'timeout'      : details.timeout,
                'architecture' : details.architecture,
                'environment'  : list(details.environment.keys()),
            }
            click.echo(json.dumps(data, indent=2))
            return
        tbl = Table(title=f'Config: {fn_name}', show_header=False)
        tbl.add_column('Field', style='dim')
        tbl.add_column('Value', style='cyan')
        tbl.add_row('Handler',      details.handler or '—')
        tbl.add_row('Runtime',      str(details.runtime))
        tbl.add_row('Memory',       f'{details.memory_size} MB')
        tbl.add_row('Timeout',      f'{details.timeout}s')
        tbl.add_row('Architecture', details.architecture or '—')
        if details.environment:
            tbl.add_row('Env vars', ', '.join(sorted(details.environment.keys())))
        console.print(tbl)


@cmd_config.command('set')
@click.pass_context
@click.option('--memory',  type=int, default=None, help='Memory in MB.')
@click.option('--timeout', type=int, default=None, help='Timeout in seconds.')
@click.option('--handler', default=None, help='Handler spec.')
@click.option('--runtime', default=None, help='Lambda runtime.')
@click.option('--env',     'env_pairs', multiple=True, help='KEY=value env var (repeatable).')
@click.option('--yes',     is_flag=True, default=False, help='Skip confirmation prompt.')
def cmd_config_set(ctx, memory, timeout, handler, runtime, env_pairs, yes):
    """Update editable config fields.  Mutation guard required."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    fields  = {}
    if memory  is not None: fields['MemorySize'] = memory
    if timeout is not None: fields['Timeout']    = timeout
    if handler is not None: fields['Handler']    = handler
    if runtime is not None: fields['Runtime']    = runtime
    if env_pairs:
        env_dict = {}
        for pair in env_pairs:
            if '=' not in pair:
                console.print(f'[red]Bad --env value (expected KEY=value): {pair!r}[/red]')
                raise SystemExit(1)
            k, v = pair.split('=', 1)
            env_dict[k] = v
        fields['Environment'] = {'Variables': env_dict}
    if not fields:
        console.print('[yellow]Nothing to update — specify at least one option.[/yellow]')
        return
    if not yes:
        console.print(f'[bold]Updating config for {fn_name}:[/bold]')
        for k, v in fields.items():
            console.print(f'  {k} = {v}')
        if not click.confirm('Apply?'):
            console.print('[yellow]Aborted.[/yellow]')
            return
    with spec_cli_errors():
        client = Lambda__AWS__Client()
        resp   = client.update_function_configuration(fn_name, **fields)
        if resp.success:
            console.print(f'[green]Updated[/green] {fn_name}')
        else:
            console.print(f'[red]Failed:[/red] {resp.message}')
            raise SystemExit(1)
