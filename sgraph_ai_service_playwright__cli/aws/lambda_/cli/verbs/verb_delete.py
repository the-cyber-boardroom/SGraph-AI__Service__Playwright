# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_delete
# `sg aws lambda <name> delete` — delete a Lambda function.
# Replaces `sg aws lambda deployment delete <name>` (new shape).
# Mutation guard required.  Confirmation required unless --yes.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import click
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client

console = Console()


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise SystemExit(1)


@click.command('delete')
@click.pass_context
@click.option('--yes',    is_flag=True, default=False, help='Skip confirmation prompt.')
@click.option('--json',   'as_json',    is_flag=True, default=False, help='Output as JSON.')
def cmd_delete(ctx, yes, as_json):
    """Delete a Lambda function (with confirmation guard)."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    if not yes:
        if not click.confirm(f'Really delete Lambda function {fn_name!r}?'):
            console.print('[yellow]Aborted.[/yellow]')
            return
    with spec_cli_errors():
        resp = Lambda__AWS__Client().delete_function(fn_name)
        if as_json:
            click.echo(json.dumps(resp.json(), indent=2))
            return
        if resp.success:
            console.print(f'[green]Deleted[/green] {fn_name}')
        else:
            console.print(f'[red]Failed:[/red] {resp.message}')
            raise SystemExit(1)
