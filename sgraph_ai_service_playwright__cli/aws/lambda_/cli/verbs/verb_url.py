# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_url
# `sg aws lambda <name> url create/show/delete` — Function URL management.
# Replaces `sg aws lambda url create/show/delete <name>` (new shape).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import click
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Url__Auth_Type import Enum__Lambda__Url__Auth_Type
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client        import Lambda__AWS__Client

console = Console()


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise SystemExit(1)


@click.group('url')
def cmd_url():
    """Manage Lambda Function URLs."""


@cmd_url.command('create')
@click.pass_context
@click.option('--auth-type', default='NONE', help='Auth type: NONE or AWS_IAM.')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def url_create(ctx, auth_type, as_json):
    """Create a Function URL."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        try:
            at = Enum__Lambda__Url__Auth_Type(auth_type)
        except ValueError:
            console.print(f'[red]Unknown auth-type: {auth_type}[/red]')
            raise SystemExit(1)
        info = Lambda__AWS__Client().create_function_url(fn_name, auth_type=at)
        if as_json:
            click.echo(json.dumps(info.json(), indent=2))
            return
        console.print(f'[green]URL created[/green]')
        console.print(f'  URL:       {info.function_url}')
        console.print(f'  Auth type: {info.auth_type}')


@cmd_url.command('show')
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def url_show(ctx, as_json):
    """Show the Function URL."""
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        info = Lambda__AWS__Client().get_function_url(fn_name)
        if as_json:
            click.echo(json.dumps(info.json(), indent=2))
            return
        if not info.exists:
            console.print(f'[yellow]No Function URL configured for {fn_name}[/yellow]')
            return
        console.print(f'  URL:       {info.function_url}')
        console.print(f'  Auth type: {info.auth_type}')


@cmd_url.command('delete')
@click.pass_context
@click.option('--yes',  is_flag=True, default=False, help='Skip confirmation.')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def url_delete(ctx, yes, as_json):
    """Delete the Function URL."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    if not yes:
        if not click.confirm(f'Really delete Function URL for {fn_name!r}?'):
            console.print('[yellow]Aborted.[/yellow]')
            return
    with spec_cli_errors():
        resp = Lambda__AWS__Client().delete_function_url(fn_name)
        if as_json:
            click.echo(json.dumps(resp.json(), indent=2))
            return
        if resp.success:
            console.print(f'[green]URL deleted[/green] for {fn_name}')
        else:
            console.print(f'[red]Failed:[/red] {resp.message}')
            raise SystemExit(1)
