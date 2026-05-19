# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Route_Table
# Typer CLI surface for `sg aws ec2 route-table *` commands.
#
# Command tree:
#   sg aws ec2 route-table list         [--vpc <vpc-id>] [--json]
#   sg aws ec2 route-table show         <rtb-id>         [--json]
#   sg aws ec2 route-table create       --vpc <vpc-id> [--name <tag>] [--yes] [--json]
#   sg aws ec2 route-table delete       <rtb-id> [--yes] [--json]
#   sg aws ec2 route-table add-route    <rtb-id> --cidr <cidr>
#                                       [--igw <igw-id>] [--nat <nat-id>] [--eni <eni-id>]
#                                       [--json]
#   sg aws ec2 route-table remove-route <rtb-id> --cidr <cidr> [--yes] [--json]
#   sg aws ec2 route-table associate    <rtb-id> --subnet <subnet-id> [--json]
#   sg aws ec2 route-table disassociate <association-id> [--yes] [--json]
#
# Mutations require SG_AWS__EC2__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate           import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client     import EC2__AWS__Client


_MUTATION_ENV = 'SG_AWS__EC2__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='route-table',
                  help='EC2 Route Table inspection and mutation.',
                  no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _route_to_dict(r) -> dict:
    return dict(
        destination_cidr = str(r.destination_cidr),
        gateway_id       = str(r.gateway_id),
        state            = str(r.state),
        origin           = str(r.origin),
    )


def _assoc_to_dict(a) -> dict:
    return dict(
        association_id = str(a.association_id),
        route_table_id = str(a.route_table_id),
        subnet_id      = str(a.subnet_id),
        main           = bool(a.main),
    )


def _rtb_to_dict(rtb) -> dict:                                                 # JSON-safe view of Schema__EC2__Route_Table
    return dict(
        route_table_id = str(rtb.route_table_id),
        vpc_id         = str(rtb.vpc_id),
        routes         = [_route_to_dict(r) for r in rtb.routes],
        associations   = [_assoc_to_dict(a) for a in rtb.associations],
        tags           = {str(k): str(v) for k, v in rtb.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def rtb_list(ctx     : typer.Context,
             vpc     : str  = typer.Option('', '--vpc', help='Filter by VPC ID.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List route tables, optionally filtered by VPC."""
    client = ctx.obj['ec2_client']
    rtbs   = client.list_route_tables(vpc_id=vpc)
    if as_json:
        typer.echo(json.dumps([_rtb_to_dict(r) for r in rtbs], indent=2))
        return
    if not rtbs:
        console.print('No route tables found.')
        return
    title = 'Route Tables'
    if vpc:
        title += f' (vpc={vpc})'
    t = Table(title=title)
    t.add_column('Route Table ID', style='cyan')
    t.add_column('VPC',             style='dim')
    t.add_column('Routes',          style='dim', justify='right')
    t.add_column('Associations',    style='dim', justify='right')
    t.add_column('Main',            style='dim')
    for rtb in rtbs:
        is_main = any(a.main for a in rtb.associations)
        t.add_row(str(rtb.route_table_id),
                  str(rtb.vpc_id) or '—',
                  str(len(rtb.routes)),
                  str(len(rtb.associations)),
                  'yes' if is_main else 'no')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def rtb_show(ctx     : typer.Context,
             rtb_id  : str  = typer.Argument(..., help='Route Table ID (rtb-*).'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one route table including routes and associations."""
    client = ctx.obj['ec2_client']
    rtb    = client.describe_route_table(rtb_id)
    if rtb is None:
        console.print(f'[red]Route table not found:[/red] {rtb_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_rtb_to_dict(rtb), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('route table id', str(rtb.route_table_id)),
        ('vpc',            str(rtb.vpc_id) or '—'),
        ('route count',    str(len(rtb.routes))),
        ('assoc count',    str(len(rtb.associations))),
        ('tags',           ', '.join(f'{k}={v}' for k, v in rtb.tags.items()) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()
    # ── routes table ──────────────────────────────────────────────────────
    if rtb.routes:
        rt = Table(title=f'Routes — {rtb.route_table_id}')
        rt.add_column('Destination', style='cyan')
        rt.add_column('Target',      style='green')
        rt.add_column('State',       style='bold')
        rt.add_column('Origin',      style='dim')
        for r in rtb.routes:
            rt.add_row(str(r.destination_cidr) or '—',
                       str(r.gateway_id)       or '—',
                       str(r.state)            or '—',
                       str(r.origin)           or '—')
        console.print(rt)
    # ── associations table ────────────────────────────────────────────────
    if rtb.associations:
        at = Table(title=f'Associations — {rtb.route_table_id}')
        at.add_column('Assoc ID',  style='cyan')
        at.add_column('Subnet',    style='green')
        at.add_column('Main',      style='dim')
        for a in rtb.associations:
            at.add_row(str(a.association_id) or '—',
                       str(a.subnet_id)      or '—',
                       'yes' if a.main else 'no')
        console.print(at)


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_create(ctx     : typer.Context,
               vpc     : str  = typer.Option(..., '--vpc',  help='Owning VPC ID.'),
               name    : str  = typer.Option('',  '--name', help='Optional Name tag.'),
               yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Create a new route table (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Create route table in {vpc}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    tags = {'Name': name} if name else None
    rtb  = client.create_route_table(vpc_id=vpc, tags=tags)
    if as_json:
        typer.echo(json.dumps({'ok': True,
                                'route_table_id': str(rtb.route_table_id),
                                'vpc_id'        : str(rtb.vpc_id)}, indent=2))
        return
    console.print(f'[green]Created[/green] {rtb.route_table_id}')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_delete(ctx     : typer.Context,
               rtb_id  : str  = typer.Argument(..., help='Route Table ID (rtb-*).'),
               yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a route table (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Delete route table {rtb_id}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True, 'route_table_id': rtb_id}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    deleted = client.delete_route_table(rtb_id)
    if as_json:
        typer.echo(json.dumps({'ok': bool(deleted), 'route_table_id': rtb_id,
                                'deleted': bool(deleted)}, indent=2))
        return
    if deleted:
        console.print(f'[green]Deleted[/green] {rtb_id}')
    else:
        console.print(f'[yellow]Not deleted[/yellow] {rtb_id} (already gone?)')
        raise typer.Exit(1)


# ── add-route ─────────────────────────────────────────────────────────────────

@app.command('add-route')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_add_route(ctx     : typer.Context,
                  rtb_id  : str  = typer.Argument(..., help='Route Table ID (rtb-*).'),
                  cidr    : str  = typer.Option(..., '--cidr', help='Destination CIDR.'),
                  igw     : str  = typer.Option('',  '--igw',  help='Target Internet Gateway ID.'),
                  nat     : str  = typer.Option('',  '--nat',  help='Target NAT Gateway ID.'),
                  eni     : str  = typer.Option('',  '--eni',  help='Target Network Interface ID.'),
                  as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Add a route to a route table (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    targets = [t for t in (igw, nat, eni) if t]
    if len(targets) != 1:
        console.print('[red]Specify exactly one target:[/red] --igw OR --nat OR --eni.')
        raise typer.Exit(1)
    client = ctx.obj['ec2_client']
    client.create_route(rtb_id, destination_cidr=cidr,
                         gateway_id=igw, nat_gateway_id=nat,
                         network_interface_id=eni)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'route_table_id': rtb_id,
                                'destination_cidr': cidr,
                                'gateway_id'      : igw or nat or eni}, indent=2))
        return
    console.print(f'[green]Added route[/green] {cidr} → {igw or nat or eni} on {rtb_id}')


# ── remove-route ──────────────────────────────────────────────────────────────

@app.command('remove-route')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_remove_route(ctx     : typer.Context,
                     rtb_id  : str  = typer.Argument(..., help='Route Table ID (rtb-*).'),
                     cidr    : str  = typer.Option(..., '--cidr', help='Destination CIDR to remove.'),
                     yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                     as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Remove a route from a route table (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Remove route {cidr} from {rtb_id}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    removed = client.delete_route(rtb_id, destination_cidr=cidr)
    if as_json:
        typer.echo(json.dumps({'ok': bool(removed), 'route_table_id': rtb_id,
                                'destination_cidr': cidr,
                                'removed': bool(removed)}, indent=2))
        return
    if removed:
        console.print(f'[green]Removed route[/green] {cidr} from {rtb_id}')
    else:
        console.print(f'[yellow]Not removed[/yellow] {cidr} (already gone?)')
        raise typer.Exit(1)


# ── associate ─────────────────────────────────────────────────────────────────

@app.command('associate')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_associate(ctx     : typer.Context,
                  rtb_id  : str  = typer.Argument(..., help='Route Table ID (rtb-*).'),
                  subnet  : str  = typer.Option(..., '--subnet', help='Subnet ID to associate.'),
                  as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Associate a route table with a subnet (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    assoc  = client.associate_route_table(rtb_id, subnet)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'route_table_id': rtb_id,
                                'subnet_id': subnet, 'association_id': assoc}, indent=2))
        return
    console.print(f'[green]Associated[/green] {rtb_id} ↔ {subnet} (id={assoc})')


# ── disassociate ──────────────────────────────────────────────────────────────

@app.command('disassociate')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def rtb_disassociate(ctx            : typer.Context,
                     association_id : str  = typer.Argument(..., help='Association ID (rtbassoc-*).'),
                     yes            : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                     as_json        : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Remove a route-table → subnet association (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Disassociate {association_id}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True,
                                    'association_id': association_id}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    removed = client.disassociate_route_table(association_id)
    if as_json:
        typer.echo(json.dumps({'ok': bool(removed), 'association_id': association_id,
                                'disassociated': bool(removed)}, indent=2))
        return
    if removed:
        console.print(f'[green]Disassociated[/green] {association_id}')
    else:
        console.print(f'[yellow]Not disassociated[/yellow] {association_id}')
        raise typer.Exit(1)
