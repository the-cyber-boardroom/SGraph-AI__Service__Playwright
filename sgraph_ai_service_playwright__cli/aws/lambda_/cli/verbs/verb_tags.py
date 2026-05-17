# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_tags
# `sg aws lambda <name> tags list/set/remove` — tag management.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client

console = Console()


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise SystemExit(1)


def _get_arn(fn_name: str) -> str:
    client  = Lambda__AWS__Client()
    details = client.get_function_details(fn_name)
    return str(details.function_arn)


@click.group('tags')
def cmd_tags():
    """Manage Lambda function tags."""


@cmd_tags.command('list')
@click.pass_context
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON.')
def tags_list(ctx, as_json):
    """List all tags on the function."""
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        arn  = _get_arn(fn_name)
        tags = Lambda__AWS__Client().list_tags(arn)
        if as_json:
            click.echo(json.dumps(tags, indent=2))
            return
        if not tags:
            console.print('[dim]No tags.[/dim]')
            return
        tbl = Table(title=f'Tags: {fn_name}')
        tbl.add_column('Key', style='cyan')
        tbl.add_column('Value')
        for k, v in sorted(tags.items()):
            tbl.add_row(k, v)
        console.print(tbl)


@cmd_tags.command('set')
@click.pass_context
@click.option('--kv', 'pairs', multiple=True, required=True, help='Key=Value tag (repeatable).')
def tags_set(ctx, pairs):
    """Set one or more tags (KEY=value format)."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    tags    = {}
    for pair in pairs:
        if '=' not in pair:
            console.print(f'[red]Bad --kv value (expected Key=Value): {pair!r}[/red]')
            raise SystemExit(1)
        k, v = pair.split('=', 1)
        tags[k] = v
    with spec_cli_errors():
        arn  = _get_arn(fn_name)
        ok   = Lambda__AWS__Client().tag_resource(arn, tags)
        if ok:
            console.print(f'[green]Tags set[/green] on {fn_name}')
        else:
            console.print('[red]Failed to set tags.[/red]')
            raise SystemExit(1)


@cmd_tags.command('remove')
@click.pass_context
@click.option('--key', 'keys', multiple=True, required=True, help='Tag key to remove (repeatable).')
def tags_remove(ctx, keys):
    """Remove one or more tags by key."""
    _mutation_guard()
    fn_name = ctx.obj['function_name']
    with spec_cli_errors():
        arn = _get_arn(fn_name)
        ok  = Lambda__AWS__Client().untag_resource(arn, list(keys))
        if ok:
            console.print(f'[green]Tags removed[/green] from {fn_name}')
        else:
            console.print('[red]Failed to remove tags.[/red]')
            raise SystemExit(1)
