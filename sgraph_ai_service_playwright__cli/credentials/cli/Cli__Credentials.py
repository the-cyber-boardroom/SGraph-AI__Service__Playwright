# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Cli__Credentials
# Typer subapp for: sg credentials.*
#
# Commands
# ────────
#   sg credentials list
#   sg credentials add    <role> <access-key> <secret-key> [--region X] [--arn X]
#   sg credentials remove <role>
#   sg credentials switch <role>
#   sg credentials show   <role>
#   sg credentials status
#   sg credentials log    [--n 20]
#   sg credentials trace  <command...>   (v0.2.28: dry-run resolver)
#   sg credentials export <role>
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from typing import List

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region            import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN         import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Audit__Log                         import Audit__Log
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Resolver              import Credentials__Resolver
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                 import Credentials__Store
from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS                   import Keyring__Mac__OS


_CURRENT_ROLE_ENV = 'SG_CREDENTIALS__CURRENT_ROLE'


app = typer.Typer(no_args_is_help=True,
                  help='Manage AWS credentials and roles stored in the macOS Keychain.')


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS())


def _audit() -> Audit__Log:
    return Audit__Log()


@app.command(name='list')
def list_cmd():
    """List all registered roles."""
    store = _store()
    roles = store.role_list()
    if not roles:
        typer.echo('(no roles configured)')
        return
    current = os.environ.get(_CURRENT_ROLE_ENV, '')
    for role in roles:
        marker = ' *' if role == current else ''
        typer.echo(f'  {role}{marker}')
    _audit().log(Enum__Audit__Action.LIST, command_args='list roles')


@app.command()
def add(role       : str = typer.Argument(..., help='Role name (e.g. admin, dev).'),
        access_key : str = typer.Argument(..., help='AWS access key ID.'),
        secret_key : str = typer.Argument(..., help='AWS secret access key.'),
        region     : str = typer.Option('us-east-1', help='Default AWS region.'),
        arn        : str = typer.Option('', help='STS AssumeRole ARN (leave empty to use keys directly.')):
    """Add or update credentials for a role."""
    store  = _store()
    config = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(role)       ,
        region          = Safe_Str__AWS__Region(region)    ,
        assume_role_arn = Safe_Str__AWS__Role__ARN(arn)    ,
        session_name    = Safe_Str__Role__Name(f'sg-{role}'),
    )
    ok_cfg = store.role_set(config)
    ok_aws = store.aws_credentials_set(role, access_key, secret_key)
    if ok_cfg and ok_aws:
        typer.echo(f'[ok] role {role!r} added/updated')
        _audit().log(Enum__Audit__Action.ADD, role=role, command_args=f'credentials add {role} <redacted> <redacted>')
    else:
        typer.echo(f'[error] failed to save credentials for {role!r}', err=True)
        raise typer.Exit(1)


@app.command()
def remove(role: str = typer.Argument(..., help='Role name to remove.')):
    """Remove all credentials for a role."""
    store = _store()
    ok    = store.role_delete(role)
    if ok:
        typer.echo(f'[ok] role {role!r} removed')
        _audit().log(Enum__Audit__Action.REMOVE, role=role, command_args=f'credentials remove {role}')
    else:
        typer.echo(f'[not found] role {role!r}', err=True)
        raise typer.Exit(1)


@app.command()
def switch(role: str = typer.Argument(..., help='Role name to activate for this shell session.')):
    """Print the shell command to activate a role (eval the output)."""
    store = _store()
    creds = store.aws_credentials_get(role)
    if creds is None:
        typer.echo(f'[error] role {role!r} not found', err=True)
        raise typer.Exit(1)
    config = store.role_get(role)
    region = str(config.region) if config else 'us-east-1'
    typer.echo(f'export AWS_ACCESS_KEY_ID={str(creds.access_key)!r}')
    typer.echo(f'export AWS_SECRET_ACCESS_KEY={str(creds.secret_key)!r}')
    typer.echo(f'export AWS_DEFAULT_REGION={region!r}')
    typer.echo(f'export {_CURRENT_ROLE_ENV}={role!r}')
    _audit().log(Enum__Audit__Action.SWITCH, role=role, command_args=f'credentials switch {role}')


@app.command()
def show(role: str = typer.Argument(..., help='Role name to inspect.')):
    """Show config for a role (secrets redacted)."""
    store  = _store()
    config = store.role_get(role)
    if config is None:
        typer.echo(f'[not found] role {role!r}', err=True)
        raise typer.Exit(1)
    creds  = store.aws_credentials_get(role)
    typer.echo(f'role          : {config.name}')
    typer.echo(f'region        : {config.region}')
    typer.echo(f'assume_role   : {config.assume_role_arn or "(direct)"}')
    typer.echo(f'session_name  : {config.session_name}')
    if creds is not None:
        typer.echo(f'access_key    : {str(creds.access_key)[:8]}…  (redacted)')
        typer.echo(f'secret_key    : ****  (redacted)')
    else:
        typer.echo('access_key    : (not set)')
        typer.echo('secret_key    : (not set)')
    _audit().log(Enum__Audit__Action.SHOW, role=role, command_args=f'credentials show {role}')


@app.command()
def status():
    """Show the currently active role."""
    current = os.environ.get(_CURRENT_ROLE_ENV, '')
    if current:
        typer.echo(f'active role: {current}')
    else:
        typer.echo('no role active  (use: eval $(sg credentials switch <role>))')
    _audit().log(Enum__Audit__Action.STATUS, command_args='credentials status')


@app.command()
def log(n: int = typer.Option(20, help='Number of recent audit events to show.')):
    """Show recent audit log entries."""
    audit  = _audit()
    events = audit.tail(n)
    if not events:
        typer.echo('(audit log is empty)')
        return
    for event in events:
        typer.echo(f"{event.get('timestamp','')}  {event.get('action',''):8}  {event.get('role',''):12}  {event.get('command_args','')}")


@app.command()
def trace(command: List[str] = typer.Argument(None, help='Command path to trace, e.g. aws lambda waker info')):
    """Dry-run: show which role would handle this command path. No AWS calls."""
    command_path = list(command) if command else []
    store    = _store()
    resolver = Credentials__Resolver(store=store)
    result   = resolver.trace(command_path)
    typer.echo(f'[trace] command path:    {" ".join(result.command_path) or "(empty)"}')
    typer.echo(f'[trace] routing match:   {result.matched_route or "(no match)"}  →  role: {result.matched_role or "(none)"}')
    chain_str = ' → '.join(result.role_chain)
    typer.echo(f'[trace] role chain:      {chain_str or "(empty)"}')
    typer.echo(f'[trace] would assume:    {result.would_assume_arn or "(direct creds — no assume)"}')
    typer.echo(f'[trace] session name:    {result.session_name_tmpl or "(n/a)"} (dry-run; not generated)')
    typer.echo(f'[trace] effective creds: source={result.source_creds}')


@app.command()
def export(role: str = typer.Argument(..., help='Role to export as shell environment variables.')):
    """Export credentials as shell env-var assignments (no keyring service names exposed)."""
    store  = _store()
    creds  = store.aws_credentials_get(role)
    config = store.role_get(role)
    if creds is None:
        typer.echo(f'[error] no credentials for role {role!r}', err=True)
        raise typer.Exit(1)
    region = str(config.region) if config else 'us-east-1'
    typer.echo(f'# credentials export for role: {role}')
    typer.echo(f'export AWS_ACCESS_KEY_ID={str(creds.access_key)!r}')
    typer.echo(f'export AWS_SECRET_ACCESS_KEY={str(creds.secret_key)!r}')
    typer.echo(f'export AWS_DEFAULT_REGION={region!r}')
    _audit().log(Enum__Audit__Action.EXPORT, role=role, command_args=f'credentials export {role}')
