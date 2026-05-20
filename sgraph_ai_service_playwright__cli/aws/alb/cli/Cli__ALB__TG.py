# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Cli__ALB__TG
# Typer CLI surface for `sg aws alb tg *` commands.
#
# Command tree:
#   sg aws alb tg list      [--lb-arn LB_ARN] [--json]
#   sg aws alb tg show      <tg-arn>           [--json]
#   sg aws alb tg create    --name NAME --vpc VPC_ID
#                           [--port 8080] [--target-type instance|ip]
#                           [--yes] [--json]   (mutation-gated)
#   sg aws alb tg delete    <tg-arn>           [--yes] [--json]  (mutation-gated)
#   sg aws alb tg register  <tg-arn> --target TARGET_ID
#                           [--port PORT] [--yes] [--json]  (mutation-gated)
#   sg aws alb tg deregister <tg-arn> --target TARGET_ID
#                            [--yes] [--json]  (mutation-gated)
#   sg aws alb tg health    <tg-arn>           [--json]
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

app = typer.Typer(name='tg', help='Target group operations.', no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('alb_client', ALB__AWS__Client())


def _tg_to_dict(tg) -> dict:
    return dict(
        tg_arn                = str(tg.tg_arn),
        tg_name               = str(tg.tg_name),
        protocol              = str(tg.protocol),
        port                  = int(tg.port),
        vpc_id                = str(tg.vpc_id),
        target_type           = str(tg.target_type),
        health_check_protocol = str(tg.health_check_protocol),
        health_check_port     = str(tg.health_check_port),
        health_check_path     = str(tg.health_check_path),
        tags                  = {str(k): str(v) for k, v in tg.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def tg_list(ctx     : typer.Context,
            lb_arn  : str  = typer.Option('', '--lb-arn', help='Filter by load balancer ARN.'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List target groups (optionally filtered by load balancer)."""
    client = ctx.obj['alb_client']
    tgs    = client.list_target_groups(lb_arn=lb_arn)
    if as_json:
        typer.echo(json.dumps([_tg_to_dict(tg) for tg in tgs], indent=2))
        return
    if not tgs:
        console.print('No target groups found.')
        return
    t = Table(title='ALB Target Groups')
    t.add_column('Name',        style='cyan')
    t.add_column('Protocol',    style='dim')
    t.add_column('Port',        style='bold')
    t.add_column('Target Type', style='dim')
    t.add_column('Health Path', style='green')
    for tg in tgs:
        t.add_row(str(tg.tg_name), str(tg.protocol), str(tg.port),
                  str(tg.target_type), str(tg.health_check_path) or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def tg_show(ctx     : typer.Context,
            tg_arn  : str  = typer.Argument(..., help='Target group ARN.'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one target group."""
    client = ctx.obj['alb_client']
    tg     = client.describe_target_group(tg_arn)
    if tg is None:
        console.print(f'[red]Target group not found:[/red] {tg_arn}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_tg_to_dict(tg), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    for label, value in [
        ('name',                str(tg.tg_name)),
        ('arn',                 str(tg.tg_arn)),
        ('protocol',            str(tg.protocol)),
        ('port',                str(tg.port)),
        ('vpc',                 str(tg.vpc_id) or '—'),
        ('target type',         str(tg.target_type)),
        ('health check proto',  str(tg.health_check_protocol) or '—'),
        ('health check port',   str(tg.health_check_port) or '—'),
        ('health check path',   str(tg.health_check_path) or '—'),
        ('tags',                ', '.join(f'{k}={v}' for k, v in tg.tags.items()) or '(none)'),
    ]:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def tg_create(ctx         : typer.Context,
              name        : str  = typer.Option(..., '--name',        help='Target group name.'),
              vpc         : str  = typer.Option(..., '--vpc',         help='VPC ID.'),
              port        : int  = typer.Option(8080, '--port',       help='Target port.'),
              target_type : str  = typer.Option('instance', '--target-type',
                                                help='instance | ip | lambda'),
              yes         : bool = typer.Option(False, '--yes',       help='Skip confirmation.'),
              as_json     : bool = typer.Option(False, '--json',      help='Output as JSON.')):
    """Create a target group (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Create target group {name!r}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    tg = client.create_target_group(name=name, vpc_id=vpc, port=port,
                                     target_type=target_type)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'tg_arn': str(tg.tg_arn)}, indent=2))
        return
    console.print(f'[green]Created[/green] {tg.tg_arn}')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def tg_delete(ctx     : typer.Context,
              tg_arn  : str  = typer.Argument(..., help='Target group ARN.'),
              yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
              as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a target group (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Delete target group {tg_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client.delete_target_group(tg_arn)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'tg_arn': tg_arn}, indent=2))
        return
    console.print(f'[green]Deleted[/green] {tg_arn}')


# ── register ──────────────────────────────────────────────────────────────────

@app.command('register')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def tg_register(ctx       : typer.Context,
                tg_arn    : str  = typer.Argument(..., help='Target group ARN.'),
                target    : str  = typer.Option(..., '--target', help='Instance ID or IP address.'),
                port      : int  = typer.Option(0,   '--port',   help='Override target port (0 = use TG default).'),
                yes       : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
                as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Register a target in a target group (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client      = ctx.obj['alb_client']
    target_spec = {'Id': target}
    if port:
        target_spec['Port'] = port
    if not yes and not typer.confirm(f'Register {target!r} → {tg_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client.register_targets(tg_arn=tg_arn, targets=[target_spec])
    if as_json:
        typer.echo(json.dumps({'ok': True, 'tg_arn': tg_arn, 'target': target}, indent=2))
        return
    console.print(f'[green]Registered[/green] {target} → {tg_arn}')


# ── deregister ────────────────────────────────────────────────────────────────

@app.command('deregister')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def tg_deregister(ctx     : typer.Context,
                  tg_arn  : str  = typer.Argument(..., help='Target group ARN.'),
                  target  : str  = typer.Option(..., '--target', help='Instance ID or IP.'),
                  yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
                  as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Deregister a target from a target group (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Deregister {target!r} from {tg_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client.deregister_targets(tg_arn=tg_arn, targets=[{'Id': target}])
    if as_json:
        typer.echo(json.dumps({'ok': True, 'tg_arn': tg_arn, 'target': target}, indent=2))
        return
    console.print(f'[green]Deregistered[/green] {target} from {tg_arn}')


# ── health ────────────────────────────────────────────────────────────────────

@app.command('health')
@spec_cli_errors
def tg_health(ctx     : typer.Context,
              tg_arn  : str  = typer.Argument(..., help='Target group ARN.'),
              as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show target health for a target group."""
    client = ctx.obj['alb_client']
    items  = client.describe_target_health(tg_arn)
    if as_json:
        payload = [
            {'target_id': h.target_id, 'target_port': h.target_port,
             'health_status': str(h.health_status),
             'reason_code': h.reason_code, 'description': h.description}
            for h in items
        ]
        typer.echo(json.dumps(payload, indent=2))
        return
    if not items:
        console.print('No registered targets.')
        return
    t = Table(title=f'Target Health — {tg_arn}')
    t.add_column('Target ID', style='cyan')
    t.add_column('Port',      style='dim')
    t.add_column('Status',    style='bold')
    t.add_column('Reason',    style='dim')
    for h in items:
        t.add_row(str(h.target_id), str(h.target_port),
                  str(h.health_status), str(h.reason_code) or '—')
    console.print(t)
