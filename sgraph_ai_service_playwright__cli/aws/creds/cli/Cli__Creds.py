# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Creds
# Typer group for `sg aws creds *` commands.
# Note: distinct from `sg aws credentials` (long-lived keys store).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import secrets
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm     import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate   import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Audit__Log       import Creds__Audit__Log
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__STS__Client      import Creds__STS__Client
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__TTL__Parser      import Creds__TTL__Parser

app   = typer.Typer(name='creds', help='Scoped STS credential delivery (per-command temporary creds).', no_args_is_help=True)
scope = typer.Typer(name='scope', help='Scope catalogue management.',                                    no_args_is_help=True)
audit = typer.Typer(name='audit', help='Credential assumption audit log.',                               no_args_is_help=True)

app.add_typer(scope, name='scope')
app.add_typer(audit, name='audit')

_console = Console()
_err     = Console(stderr=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('creds_catalogue' , Creds__Scope__Catalogue())
    ctx.obj.setdefault('creds_sts_client', Creds__STS__Client())
    ctx.obj.setdefault('creds_audit_log' , Creds__Audit__Log())


# ── get ───────────────────────────────────────────────────────────────────────

@app.command('get')
def get(ctx:          typer.Context,
        scope_name:   str  = typer.Option(..., '--scope'),
        role_hint:    str  = typer.Option('', '--role-hint'),
        ttl:          str  = typer.Option('1h', '--ttl'),
        shell_export: bool = typer.Option(False, '--shell-export'),
        as_json:      bool = typer.Option(False, '--json')):
    """Get temporary scoped credentials for a named scope."""
    cat   = ctx.obj['creds_catalogue']
    entry = cat.scope_get(scope_name)
    if entry is None:
        _err.print(Panel(f'Scope [bold]{scope_name}[/bold] not found in catalogue.',
                         title='[red]Unknown scope[/red]', border_style='red'))
        raise typer.Exit(1)

    role_arn = role_hint if role_hint else entry['role_arn']
    max_ttl  = entry.get('max_ttl', '1h')

    parser   = Creds__TTL__Parser()
    try:
        ttl_secs     = parser.parse(ttl)
        max_ttl_secs = parser.parse(max_ttl)
    except ValueError as exc:
        _err.print(Panel(str(exc), title='[red]Invalid TTL[/red]', border_style='red'))
        raise typer.Exit(1)

    if ttl_secs > max_ttl_secs:
        _err.print(Panel(
            f'Requested TTL [bold]{ttl}[/bold] exceeds max-TTL [bold]{max_ttl}[/bold] for scope.',
            title='[red]TTL exceeded[/red]', border_style='red',
        ))
        raise typer.Exit(1)

    sts    = ctx.obj['creds_sts_client']
    caller = sts.get_caller_identity()
    sname  = f'sg-creds-{scope_name}-{secrets.token_hex(4)}'

    creds  = sts.assume_role(role_arn, sname, ttl_secs)

    assumption_id = secrets.token_hex(12)
    assumed_at    = datetime.now(timezone.utc).isoformat()

    log_entry = {
        'assumption_id' : assumption_id,
        'scope_name'    : scope_name,
        'role_arn'      : role_arn,
        'caller'        : caller,
        'assumed_at'    : assumed_at,
        'expires_at'    : creds['Expiration'],
        'access_key_id' : creds['AccessKeyId'],
        'session_token' : creds['SessionToken'],
    }
    ctx.obj['creds_audit_log'].append(log_entry)

    export_data = {
        'access_key_id'     : creds['AccessKeyId'],
        'secret_access_key' : creds['SecretAccessKey'],
        'session_token'     : creds['SessionToken'],
        'expiration'        : creds['Expiration'],
        'region'            : os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', '')),
    }

    if as_json:
        typer.echo(json.dumps(export_data))
        return

    if shell_export:
        _console.print(f"export AWS_ACCESS_KEY_ID={export_data['access_key_id']}")
        _console.print(f"export AWS_SECRET_ACCESS_KEY={export_data['secret_access_key']}")
        _console.print(f"export AWS_SESSION_TOKEN={export_data['session_token']}")
        if export_data['region']:
            _console.print(f"export AWS_DEFAULT_REGION={export_data['region']}")
        return

    table = Table(title=f'Scoped credentials — {scope_name}')
    table.add_column('Key',   style='bold cyan')
    table.add_column('Value', style='white')
    table.add_row('AccessKeyId',     export_data['access_key_id'])
    table.add_row('SecretAccessKey', '*' * 16 + ' (hidden)')
    table.add_row('SessionToken',    export_data['session_token'][:32] + '…')
    table.add_row('Expiration',      export_data['expiration'])
    _console.print(table)
    _console.print(f'[dim]assumption_id: {assumption_id}[/dim]')


# ── list-scopes ───────────────────────────────────────────────────────────────

@app.command('list-scopes')
def list_scopes(ctx: typer.Context, as_json: bool = typer.Option(False, '--json')):
    """List all scopes in the catalogue."""
    cat    = ctx.obj['creds_catalogue']
    scopes = cat.scope_list()

    if as_json:
        typer.echo(json.dumps(scopes))
        return

    if not scopes:
        _console.print('[dim]No scopes defined.[/dim]')
        return

    table = Table(title='Creds scopes')
    table.add_column('Name',    style='bold cyan')
    table.add_column('Role ARN', style='white')
    table.add_column('Max TTL', style='yellow')
    table.add_column('Created', style='dim')
    for s in scopes:
        table.add_row(s.get('name', ''), s.get('role_arn', ''),
                      s.get('max_ttl', ''), s.get('created_at', '')[:19])
    _console.print(table)


# ── scope show ────────────────────────────────────────────────────────────────

@scope.command('show')
def scope_show(ctx: typer.Context, name: str = typer.Argument(...), as_json: bool = typer.Option(False, '--json')):
    """Show scope definition."""
    cat   = ctx.obj['creds_catalogue']
    entry = cat.scope_get(name)
    if entry is None:
        _err.print(Panel(f'Scope [bold]{name}[/bold] not found.',
                         title='[red]Not found[/red]', border_style='red'))
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(entry))
        return

    table = Table(title=f'Scope: {name}')
    table.add_column('Field', style='bold cyan')
    table.add_column('Value', style='white')
    for k, v in entry.items():
        table.add_row(k, str(v))
    _console.print(table)


# ── scope add ─────────────────────────────────────────────────────────────────

@scope.command('add')
@require_mutation_gate('SG_AWS__CREDS__ALLOW_MUTATIONS')
def scope_add(ctx:     typer.Context,
              name:    str  = typer.Option(...,   '--name'),
              role:    str  = typer.Option(...,   '--role'),
              max_ttl: str  = typer.Option('1h',  '--max-ttl'),
              yes:     bool = typer.Option(False, '--yes', '-y'),
              dry_run: bool = typer.Option(False, '--dry-run', help='Print action without executing.'),
              as_json: bool = typer.Option(False, '--json')):
    """Add a scope to the catalogue (gated)."""
    if not confirm_or_abort(f'Add scope {name!r} → {role!r} (max-ttl={max_ttl})?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)

    cat   = ctx.obj['creds_catalogue']
    entry = cat.scope_add(name, role, max_ttl)

    if as_json:
        typer.echo(json.dumps(entry))
        return

    _console.print(Panel(
        f'Scope [bold cyan]{name}[/bold cyan] added.\n'
        f'Role: {role}\nMax-TTL: {max_ttl}',
        title='[green]Added[/green]', border_style='green',
    ))


# ── scope remove ──────────────────────────────────────────────────────────────

@scope.command('remove')
@require_mutation_gate('SG_AWS__CREDS__ALLOW_MUTATIONS')
def scope_remove(ctx:     typer.Context,
                 name:    str  = typer.Argument(...),
                 yes:     bool = typer.Option(False, '--yes', '-y'),
                 dry_run: bool = typer.Option(False, '--dry-run', help='Print action without executing.')):
    """Remove a scope from the catalogue (gated)."""
    if not confirm_or_abort(f'Remove scope {name!r}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)

    cat = ctx.obj['creds_catalogue']
    ok  = cat.scope_remove(name)
    if not ok:
        _err.print(Panel(f'Scope [bold]{name}[/bold] not found.',
                         title='[red]Not found[/red]', border_style='red'))
        raise typer.Exit(1)

    _console.print(f'[green]Scope {name!r} removed.[/green]')


# ── scope update ──────────────────────────────────────────────────────────────

@scope.command('update')
@require_mutation_gate('SG_AWS__CREDS__ALLOW_MUTATIONS')
def scope_update(ctx:     typer.Context,
                 name:    str  = typer.Argument(...),
                 role:    str  = typer.Option('', '--role'),
                 max_ttl: str  = typer.Option('', '--max-ttl'),
                 yes:     bool = typer.Option(False, '--yes', '-y'),
                 dry_run: bool = typer.Option(False, '--dry-run', help='Print action without executing.'),
                 as_json: bool = typer.Option(False, '--json')):
    """Update a scope in the catalogue (gated)."""
    cat   = ctx.obj['creds_catalogue']
    entry = cat.scope_get(name)
    if entry is None:
        _err.print(Panel(f'Scope [bold]{name}[/bold] not found.',
                         title='[red]Not found[/red]', border_style='red'))
        raise typer.Exit(1)

    new_role    = role    if role    else entry['role_arn']
    new_max_ttl = max_ttl if max_ttl else entry['max_ttl']

    if not confirm_or_abort(f'Update scope {name!r}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)

    updated = cat.scope_add(name, new_role, new_max_ttl)

    if as_json:
        typer.echo(json.dumps(updated))
        return

    _console.print(Panel(
        f'Scope [bold cyan]{name}[/bold cyan] updated.\n'
        f'Role: {new_role}\nMax-TTL: {new_max_ttl}',
        title='[green]Updated[/green]', border_style='green',
    ))


# ── audit list ────────────────────────────────────────────────────────────────

@audit.command('list')
def audit_list(ctx:     typer.Context,
               caller:  str  = typer.Option('', '--caller'),
               scope_n: str  = typer.Option('', '--scope'),
               since:   str  = typer.Option('1h', '--since'),
               as_json: bool = typer.Option(False, '--json')):
    """Tail the assumption audit log."""
    log     = ctx.obj['creds_audit_log']
    entries = log.query(caller=caller, scope=scope_n, since=since)

    if as_json:
        typer.echo(json.dumps(entries))
        return

    if not entries:
        _console.print('[dim]No audit entries in window.[/dim]')
        return

    table = Table(title=f'Audit log (since {since})')
    table.add_column('ID',         style='dim')
    table.add_column('Scope',      style='bold cyan')
    table.add_column('Caller',     style='white')
    table.add_column('Assumed At', style='yellow')
    table.add_column('Expires At', style='yellow')
    for e in entries:
        table.add_row(
            e.get('assumption_id', '')[:16],
            e.get('scope_name', ''),
            e.get('caller', '')[-40:],
            e.get('assumed_at', '')[:19],
            e.get('expires_at', '')[:19],
        )
    _console.print(table)


# ── audit show ────────────────────────────────────────────────────────────────

@audit.command('show')
def audit_show(ctx:           typer.Context,
               assumption_id: str  = typer.Argument(...),
               as_json:       bool = typer.Option(False, '--json')):
    """Show a full assumption record."""
    log   = ctx.obj['creds_audit_log']
    entry = log.load_entry(assumption_id)

    if entry is None:
        _err.print(Panel(f'Assumption [bold]{assumption_id}[/bold] not found.',
                         title='[red]Not found[/red]', border_style='red'))
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(entry))
        return

    table = Table(title=f'Assumption: {assumption_id}')
    table.add_column('Field', style='bold cyan')
    table.add_column('Value', style='white')
    for k, v in entry.items():
        if k == 'session_token':
            v = v[:32] + '…' if len(v) > 32 else v
        table.add_row(k, str(v))
    _console.print(table)
