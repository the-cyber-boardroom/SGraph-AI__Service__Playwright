# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Cli__ALB__LB
# Typer CLI surface for `sg aws alb lb *` commands.
#
# Command tree:
#   sg aws alb lb list                       [--json]
#   sg aws alb lb show   <lb-arn-or-name>    [--json]
#   sg aws alb lb create --name NAME --subnets SN1,SN2 --sg SG1
#                        [--internal] [--yes] [--json]   (mutation-gated)
#   sg aws alb lb delete <lb-arn>            [--yes] [--json]  (mutation-gated)
#   sg aws alb lb tags   <lb-arn>            [--json]
#
# Mutations require SG_AWS__ALB__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing import List

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate   import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client import ALB__AWS__Client


_MUTATION_ENV = 'SG_AWS__ALB__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='lb', help='Load balancer operations.', no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('alb_client', ALB__AWS__Client())


def _lb_to_dict(lb) -> dict:
    return dict(
        lb_arn       = str(lb.lb_arn),
        lb_name      = str(lb.lb_name),
        dns_name     = str(lb.dns_name),
        state        = str(lb.state),
        scheme       = str(lb.scheme),
        vpc_id       = str(lb.vpc_id),
        created_time = str(lb.created_time),
        tags         = {str(k): str(v) for k, v in lb.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def lb_list(ctx     : typer.Context,
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List all ALB load balancers in the current account / region."""
    client = ctx.obj['alb_client']
    lbs    = client.list_load_balancers()
    if as_json:
        typer.echo(json.dumps([_lb_to_dict(lb) for lb in lbs], indent=2))
        return
    if not lbs:
        console.print('No load balancers found.')
        return
    t = Table(title='ALB Load Balancers')
    t.add_column('Name',    style='cyan')
    t.add_column('State',   style='bold')
    t.add_column('Scheme',  style='dim')
    t.add_column('DNS',     style='green')
    t.add_column('VPC',     style='dim')
    for lb in lbs:
        t.add_row(str(lb.lb_name), str(lb.state), str(lb.scheme),
                  str(lb.dns_name) or '—', str(lb.vpc_id) or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def lb_show(ctx              : typer.Context,
            lb_arn_or_name   : str  = typer.Argument(..., help='LB ARN or name.'),
            as_json          : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one load balancer."""
    client = ctx.obj['alb_client']
    lb     = client.describe_load_balancer(lb_arn_or_name)
    if lb is None:
        console.print(f'[red]Load balancer not found:[/red] {lb_arn_or_name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_lb_to_dict(lb), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16)
    t.add_column()
    for label, value in [
        ('name',         str(lb.lb_name)),
        ('arn',          str(lb.lb_arn)),
        ('dns',          str(lb.dns_name) or '—'),
        ('state',        str(lb.state)),
        ('scheme',       str(lb.scheme)),
        ('vpc',          str(lb.vpc_id) or '—'),
        ('created',      str(lb.created_time) or '—'),
        ('tags',         ', '.join(f'{k}={v}' for k, v in lb.tags.items()) or '(none)'),
    ]:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def lb_create(ctx      : typer.Context,
              name     : str       = typer.Option(..., '--name',    help='Load balancer name (max 32 chars).'),
              subnets  : str       = typer.Option(..., '--subnets', help='Comma-separated subnet IDs (at least 2).'),
              sg       : List[str] = typer.Option([],  '--sg',      help='Security group ID (repeat for multiple).'),
              internal : bool      = typer.Option(False, '--internal', help='Internal scheme (default: internet-facing).'),
              yes      : bool      = typer.Option(False, '--yes',   help='Skip confirmation.'),
              as_json  : bool      = typer.Option(False, '--json',  help='Output as JSON.')):
    """Create a new ALB load balancer (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client    = ctx.obj['alb_client']
    scheme    = 'internal' if internal else 'internet-facing'
    subnet_ids = [s.strip() for s in subnets.split(',') if s.strip()]
    if not yes and not typer.confirm(f'Create ALB {name!r} ({scheme})?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    lb = client.create_load_balancer(name=name, subnets=subnet_ids,
                                      security_groups=list(sg), scheme=scheme)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'lb_arn': str(lb.lb_arn),
                                'dns_name': lb.dns_name}, indent=2))
        return
    console.print(f'[green]Created[/green] {lb.lb_arn}')
    console.print(f'  DNS: {lb.dns_name}')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def lb_delete(ctx     : typer.Context,
              lb_arn  : str  = typer.Argument(..., help='Load balancer ARN.'),
              yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
              as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a load balancer (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Delete LB {lb_arn}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client.delete_load_balancer(lb_arn)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'lb_arn': lb_arn}, indent=2))
        return
    console.print(f'[green]Deleted[/green] {lb_arn}')


# ── tags ──────────────────────────────────────────────────────────────────────

@app.command('tags')
@spec_cli_errors
def lb_tags(ctx     : typer.Context,
            lb_arn  : str       = typer.Argument(..., help='Load balancer ARN.'),
            as_json : bool      = typer.Option(False, '--json', help='Output as JSON.')):
    """Show tags on a load balancer."""
    client = ctx.obj['alb_client']
    lb     = client.describe_load_balancer(lb_arn)
    if lb is None:
        console.print(f'[red]Load balancer not found:[/red] {lb_arn}')
        raise typer.Exit(1)
    tags = {str(k): str(v) for k, v in lb.tags.items()}
    if as_json:
        typer.echo(json.dumps({'lb_arn': lb_arn, 'tags': tags}, indent=2))
        return
    if not tags:
        console.print('(no tags)')
        return
    t = Table(title=f'Tags — {lb_arn}')
    t.add_column('Key',   style='bold')
    t.add_column('Value', style='dim')
    for k, v in tags.items():
        t.add_row(k, v)
    console.print(t)
