# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Lambda
# Entry point for the `sg aws lambda` subtree.
#
# New command shape (v0.2.26):
#   sg aws lambda list
#   sg aws lambda <name> info|details|config|logs|invocations|invoke|deploy
#                         |delete|url|tags|versions|aliases
#
# Legacy commands kept with deprecation warnings (remove in v0.2.27):
#   sg aws lambda deployment list   → sg aws lambda list
#   sg aws lambda deployment deploy → sg aws lambda <name> deploy
#   sg aws lambda deployment delete → sg aws lambda <name> delete
#   sg aws lambda url create/show/delete <name> → sg aws lambda <name> url ...
#
# Mutations require SG_AWS__LAMBDA__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys

import click
import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                               import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Url__Auth_Type    import Enum__Lambda__Url__Auth_Type
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client           import Lambda__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer              import Lambda__Deployer
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group              import Lambda__App__Group

console = Console()

# ── new Click-based entry point ───────────────────────────────────────────────

lambda_click_app = Lambda__App__Group()                                           # the new `sg aws lambda` root


# ── legacy Typer shim (deprecated) ───────────────────────────────────────────
# These commands still work but print a one-line deprecation warning.
# They will be removed in v0.2.27.

lambda_app     = typer.Typer(name='lambda',     help='Lambda function management (legacy — use new shape).', no_args_is_help=True, hidden=True)
deployment_app = typer.Typer(name='deployment', help='[DEPRECATED] Deploy, update, delete Lambda functions.', no_args_is_help=True, hidden=True)
url_app        = typer.Typer(name='url',        help='[DEPRECATED] Lambda Function URL management.',          no_args_is_help=True, hidden=True)

lambda_app.add_typer(deployment_app, name='deployment')
lambda_app.add_typer(url_app,        name='url')


def _mutation_guard():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow Lambda mutations.[/red]')
        raise typer.Exit(1)


def _deprecation(old: str, new: str):
    console.print(f'[yellow]⚠  DEPRECATED:[/yellow] `{old}` — use `{new}` instead. Will be removed in v0.2.27.', file=sys.stderr)


# ── deployment list ───────────────────────────────────────────────────────────

@deployment_app.command('list')
@spec_cli_errors
def deployment_list(
    as_json: bool = typer.Option(False, '--json', help='Output as JSON.'),
):
    """[DEPRECATED] List all Lambda functions. Use `sg aws lambda list`."""
    _deprecation('sg aws lambda deployment list', 'sg aws lambda list')
    fns = Lambda__AWS__Client().list_functions()
    if as_json:
        typer.echo(json.dumps([f.json() for f in fns], indent=2))
        return
    if not fns:
        console.print('No Lambda functions found.')
        return
    tbl = Table(title='Lambda Functions')
    tbl.add_column('Name',    style='cyan')
    tbl.add_column('Runtime', style='green')
    tbl.add_column('State',   style='yellow')
    tbl.add_column('Handler', style='white')
    tbl.add_column('Memory',  style='dim')
    for f in fns:
        tbl.add_row(str(f.name), str(f.runtime), str(f.state), f.handler, str(f.memory_size))
    console.print(tbl)


# ── deployment deploy ─────────────────────────────────────────────────────────

@deployment_app.command('deploy')
@spec_cli_errors
def deployment_deploy(
    name:      str = typer.Argument(..., help='Lambda function name.'),
    code_path: str = typer.Option(...,  '--code-path', help='Path to folder containing function code.'),
    handler:   str = typer.Option(...,  '--handler',   help='Handler spec e.g. handler:handler.'),
    role_arn:  str = typer.Option('',   '--role-arn',  help='IAM execution role ARN.'),
    runtime:   str = typer.Option('python3.11', '--runtime', help='Lambda runtime.'),
    memory:    int = typer.Option(256,  '--memory',    help='Memory in MB.'),
    timeout:   int = typer.Option(900,  '--timeout',   help='Timeout in seconds.'),
    as_json:   bool= typer.Option(False,'--json',      help='Output as JSON.'),
):
    """[DEPRECATED] Deploy or update a Lambda function. Use `sg aws lambda <name> deploy`."""
    _deprecation('sg aws lambda deployment deploy <name>', f'sg aws lambda {name} deploy')
    _mutation_guard()
    from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime import Enum__Lambda__Runtime
    try:
        rt = Enum__Lambda__Runtime(runtime)
    except ValueError:
        console.print(f'[red]Unknown runtime: {runtime}[/red]')
        raise typer.Exit(1)
    req = Schema__Lambda__Deploy__Request(
        name        = Safe_Str__Lambda__Name(name),
        folder_path = code_path,
        handler     = handler,
        role_arn    = role_arn,
        runtime     = rt,
        memory_size = memory,
        timeout     = timeout,
    )
    resp = Lambda__Deployer().deploy_from_folder(req)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        verb = 'Created' if resp.created else 'Updated'
        console.print(f'[green]{verb}[/green] {name}')
        console.print(f'  ARN: {resp.function_arn}')
    else:
        console.print(f'[red]Failed:[/red] {resp.message}')
        raise typer.Exit(1)


# ── deployment delete ─────────────────────────────────────────────────────────

@deployment_app.command('delete')
@spec_cli_errors
def deployment_delete(
    name:    str  = typer.Argument(...,  help='Lambda function name.'),
    as_json: bool = typer.Option(False, '--json', help='Output as JSON.'),
):
    """[DEPRECATED] Delete a Lambda function. Use `sg aws lambda <name> delete`."""
    _deprecation('sg aws lambda deployment delete <name>', f'sg aws lambda {name} delete')
    _mutation_guard()
    resp = Lambda__AWS__Client().delete_function(name)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        console.print(f'[green]Deleted[/green] {name}')
    else:
        console.print(f'[red]Failed:[/red] {resp.message}')
        raise typer.Exit(1)


# ── url create ────────────────────────────────────────────────────────────────

@url_app.command('create')
@spec_cli_errors
def url_create(
    name:      str  = typer.Argument(...,  help='Lambda function name.'),
    auth_type: str  = typer.Option('NONE', '--auth-type', help='Auth type: NONE or AWS_IAM.'),
    as_json:   bool = typer.Option(False,  '--json',      help='Output as JSON.'),
):
    """[DEPRECATED] Create a Function URL. Use `sg aws lambda <name> url create`."""
    _deprecation('sg aws lambda url create <name>', f'sg aws lambda {name} url create')
    _mutation_guard()
    try:
        at = Enum__Lambda__Url__Auth_Type(auth_type)
    except ValueError:
        console.print(f'[red]Unknown auth-type: {auth_type}[/red]')
        raise typer.Exit(1)
    info = Lambda__AWS__Client().create_function_url(name, auth_type=at)
    if as_json:
        typer.echo(json.dumps(info.json(), indent=2))
        return
    console.print(f'[green]URL created[/green]')
    console.print(f'  URL:       {info.function_url}')
    console.print(f'  Auth type: {info.auth_type}')


# ── url show ──────────────────────────────────────────────────────────────────

@url_app.command('show')
@spec_cli_errors
def url_show(
    name:    str  = typer.Argument(...,  help='Lambda function name.'),
    as_json: bool = typer.Option(False, '--json', help='Output as JSON.'),
):
    """[DEPRECATED] Show the Function URL. Use `sg aws lambda <name> url show`."""
    _deprecation('sg aws lambda url show <name>', f'sg aws lambda {name} url show')
    info = Lambda__AWS__Client().get_function_url(name)
    if as_json:
        typer.echo(json.dumps(info.json(), indent=2))
        return
    if not info.exists:
        console.print(f'[yellow]No Function URL configured for {name}[/yellow]')
        return
    console.print(f'  URL:       {info.function_url}')
    console.print(f'  Auth type: {info.auth_type}')


# ── url delete ────────────────────────────────────────────────────────────────

@url_app.command('delete')
@spec_cli_errors
def url_delete(
    name:    str  = typer.Argument(...,  help='Lambda function name.'),
    as_json: bool = typer.Option(False, '--json', help='Output as JSON.'),
):
    """[DEPRECATED] Delete the Function URL. Use `sg aws lambda <name> url delete`."""
    _deprecation('sg aws lambda url delete <name>', f'sg aws lambda {name} url delete')
    _mutation_guard()
    resp = Lambda__AWS__Client().delete_function_url(name)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        console.print(f'[green]URL deleted[/green] for {name}')
    else:
        console.print(f'[red]Failed:[/red] {resp.message}')
        raise typer.Exit(1)
