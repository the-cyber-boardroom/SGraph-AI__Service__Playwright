# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Cli__ALB__Listener
# Typer CLI surface for `sg aws alb listener *` commands.
#
# Command tree:
#   sg aws alb listener list   --lb-arn LB_ARN          [--json]
#   sg aws alb listener show   <listener-arn>            [--json]
#   sg aws alb listener create --lb-arn LB_ARN --tg-arn TG_ARN
#                              [--port 80] [--yes] [--json]  (mutation-gated)
#   sg aws alb listener delete <listener-arn>
#                              [--yes] [--json]  (mutation-gated)
#
# Mutations require SG_AWS__ALB__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate   import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client import ALB__AWS__Client


_MUTATION_ENV = 'SG_AWS__ALB__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='listener', help='Listener operations.', no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('alb_client', ALB__AWS__Client())


def _listener_to_dict(listener) -> dict:
    return dict(
        listener_arn = str(listener.listener_arn),
        lb_arn       = str(listener.lb_arn),
        protocol     = str(listener.protocol),
        port         = int(listener.port),
        default_action = dict(
            action_type = str(listener.default_action.action_type),
            tg_arn      = str(listener.default_action.tg_arn),
        ),
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def listener_list(ctx     : typer.Context,
                  lb_arn  : str  = typer.Option(..., '--lb-arn', help='Load balancer ARN.'),
                  as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List listeners for a load balancer."""
    client    = ctx.obj['alb_client']
    listeners = client.list_listeners(lb_arn=lb_arn)
    if as_json:
        typer.echo(json.dumps([_listener_to_dict(l) for l in listeners], indent=2))
        return
    if not listeners:
        console.print('No listeners found.')
        return
    t = Table(title=f'Listeners — {lb_arn}')
    t.add_column('Protocol', style='dim')
    t.add_column('Port',     style='bold')
    t.add_column('Default TG', style='green')
    t.add_column('ARN',      style='cyan')
    for l in listeners:
        t.add_row(str(l.protocol), str(l.port),
                  str(l.default_action.tg_arn) or '—',
                  str(l.listener_arn))
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def listener_show(ctx          : typer.Context,
                  listener_arn : str  = typer.Argument(..., help='Listener ARN.'),
                  as_json      : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one listener."""
    client   = ctx.obj['alb_client']
    listener = client.describe_listener(listener_arn)
    if listener is None:
        console.print(f'[red]Listener not found:[/red] {listener_arn}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_listener_to_dict(listener), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16)
    t.add_column()
    for label, value in [
        ('arn',         str(listener.listener_arn)),
        ('lb arn',      str(listener.lb_arn)),
        ('protocol',    str(listener.protocol)),
        ('port',        str(listener.port)),
        ('action type', str(listener.default_action.action_type) or '—'),
        ('default tg',  str(listener.default_action.tg_arn) or '—'),
    ]:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def listener_create(ctx     : typer.Context,
                    lb_arn  : str  = typer.Option(..., '--lb-arn', help='Load balancer ARN.'),
                    tg_arn  : str  = typer.Option(..., '--tg-arn', help='Default target group ARN.'),
                    port    : int  = typer.Option(80,  '--port',   help='Listener port (default 80).'),
                    yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
                    as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Create a listener (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Create HTTP:{port} listener on {lb_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    listener = client.create_listener(lb_arn=lb_arn, tg_arn=tg_arn, port=port)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'listener_arn': str(listener.listener_arn)}, indent=2))
        return
    console.print(f'[green]Created[/green] {listener.listener_arn}')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def listener_delete(ctx          : typer.Context,
                    listener_arn : str  = typer.Argument(..., help='Listener ARN.'),
                    yes          : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
                    as_json      : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a listener (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Delete listener {listener_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client.delete_listener(listener_arn)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'listener_arn': listener_arn}, indent=2))
        return
    console.print(f'[green]Deleted[/green] {listener_arn}')
