# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Logs
# Typer CLI surface for `sg aws logs *` commands.
#
# Command tree:
#   sg aws logs groups list                  [--prefix P] [--json]
#   sg aws logs group  describe  <name>      [--json]
#   sg aws logs group  create    <name>      [--retention 7] [--yes]   (mutating)
#   sg aws logs group  delete    <name>      [--yes]                   (mutating)
#   sg aws logs tail   <group>   [--stream <prefix>] [--since 60] [--follow]
#
# Mutating commands require SG_AWS__LOGS__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                   import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate            import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client    import Logs__AWS__Client

_MUTATION_ENV = 'SG_AWS__LOGS__ALLOW_MUTATIONS'

console = Console()

app   = typer.Typer(name='logs',  help='CloudWatch Logs group management and tailing.',
                    no_args_is_help=True)
_grp  = typer.Typer(name='group', help='Single log group operations.',
                    no_args_is_help=True)
_grps = typer.Typer(name='groups', help='Log group listing.',
                    no_args_is_help=True)

app.add_typer(_grps, name='groups')
app.add_typer(_grp,  name='group')


# ── context setup ─────────────────────────────────────────────────────────────

@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('logs_client', Logs__AWS__Client())


# ── groups list ───────────────────────────────────────────────────────────────

@_grps.command('list')
@spec_cli_errors
def groups_list(ctx     : typer.Context,
                prefix  : str  = typer.Option('', '--prefix',
                                               help='Filter by log group name prefix.'),
                as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List CloudWatch log groups, optionally filtered by prefix."""
    client = ctx.obj['logs_client']
    groups = client.list_log_groups(prefix=prefix)
    if as_json:
        typer.echo(json.dumps([dict(name           = g.name,
                                    retention_days = g.retention_days,
                                    arn            = g.arn,
                                    stored_bytes   = g.stored_bytes)
                                for g in groups], indent=2))
        return
    if not groups:
        console.print('No log groups found.')
        return
    t = Table(title='CloudWatch Log Groups')
    t.add_column('Name',             style='cyan')
    t.add_column('Retention',        style='dim',  justify='right')
    t.add_column('Stored (bytes)',   style='dim',  justify='right')
    for g in groups:
        ret = '∞' if g.retention_days == 0 else str(g.retention_days)
        t.add_row(g.name, ret, str(g.stored_bytes))
    console.print(t)


# ── group describe ────────────────────────────────────────────────────────────

@_grp.command('describe')
@spec_cli_errors
def group_describe(ctx     : typer.Context,
                   name    : str  = typer.Argument(..., help='Log group name.'),
                   as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show details for one CloudWatch log group."""
    client = ctx.obj['logs_client']
    group  = client.describe_log_group(name)
    if group is None:
        console.print(f'[red]Log group not found:[/red] {name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(name           = group.name,
                                   retention_days = group.retention_days,
                                   arn            = group.arn,
                                   stored_bytes   = group.stored_bytes), indent=2))
        return
    ret = '∞' if group.retention_days == 0 else str(group.retention_days)
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18)
    t.add_column()
    rows = [
        ('name',      group.name),
        ('retention', ret),
        ('arn',       group.arn      or '—'),
        ('stored',    str(group.stored_bytes)),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── group create ──────────────────────────────────────────────────────────────

@_grp.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def group_create(ctx       : typer.Context,
                 name      : str  = typer.Argument(..., help='Log group name.'),
                 retention : int  = typer.Option(7, '--retention',
                                                  help='Retention in days (0 = no policy).'),
                 yes       : bool = typer.Option(False, '--yes',
                                                  help='Skip confirmation prompt.')):
    """Create a CloudWatch log group (requires SG_AWS__LOGS__ALLOW_MUTATIONS=1)."""
    if not yes and not typer.confirm(f'Create log group {name!r}?', default=True):
        console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client  = ctx.obj['logs_client']
    # check if it already exists before creating
    existing = client.describe_log_group(name)
    created  = client.create_log_group(name, retention_days=retention)
    if existing is not None:
        console.print(f'[yellow]Already exists (skipped):[/yellow] {name}')
    else:
        console.print(f'[green]Created[/green] log group {name}.')


# ── group delete ──────────────────────────────────────────────────────────────

@_grp.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def group_delete(ctx  : typer.Context,
                 name : str  = typer.Argument(..., help='Log group name.'),
                 yes  : bool = typer.Option(False, '--yes',
                                             help='Skip confirmation prompt.')):
    """Delete a CloudWatch log group (requires SG_AWS__LOGS__ALLOW_MUTATIONS=1)."""
    if not yes and not typer.confirm(
        f'Delete log group {name!r}? This cannot be undone.', default=False):
        console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client  = ctx.obj['logs_client']
    deleted = client.delete_log_group(name)
    if deleted:
        console.print(f'[green]Deleted[/green] log group {name}.')
    else:
        console.print(f'[yellow]Not found (skipped):[/yellow] {name}')


# ── tail ──────────────────────────────────────────────────────────────────────

@app.command('tail')
@spec_cli_errors
def logs_tail(ctx    : typer.Context,
              group  : str  = typer.Argument(..., help='Log group name.'),
              stream : str  = typer.Option('',  '--stream',
                                            help='Filter by log stream prefix.'),
              since  : int  = typer.Option(60,  '--since',
                                            help='Look back N minutes (default 60).'),
              follow : bool = typer.Option(False, '--follow',
                                            help='Poll for new events (Ctrl-C to stop).')):
    """Tail a CloudWatch log group; prints [stream] message per line."""
    client = ctx.obj['logs_client']
    events = client.tail_log_group(name=group, stream_prefix=stream,
                                   since_minutes=since, follow=follow)
    if not events:
        console.print('[dim]No log events found.[/dim]')
        return
    for ev in events:
        stream_name = ev.get('stream', '')
        message     = ev.get('message', '')
        typer.echo(f'[{stream_name}] {message}')
