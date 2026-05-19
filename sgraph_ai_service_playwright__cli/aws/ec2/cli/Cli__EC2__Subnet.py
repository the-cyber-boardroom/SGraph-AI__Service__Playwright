# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Subnet
# Typer CLI surface for `sg aws ec2 subnet *` commands.
#
# Command tree:
#   sg aws ec2 subnet list        [--vpc <vpc-id>] [--az <az>]            [--json]
#   sg aws ec2 subnet show        <subnet-id>                              [--json]
#   sg aws ec2 subnet create      --vpc <vpc-id> --cidr <cidr>
#                                 [--az <az>] [--name <tag>] [--public]
#                                 [--yes] [--json]
#   sg aws ec2 subnet delete      <subnet-id> [--yes] [--json]
#   sg aws ec2 subnet modify-attr <subnet-id> [--public/--no-public] [--json]
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

app = typer.Typer(name='subnet', help='EC2 Subnet inspection and mutation.',
                  no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _subnet_to_dict(s) -> dict:                                                # JSON-safe view of Schema__EC2__Subnet
    return dict(
        subnet_id               = str(s.subnet_id),
        vpc_id                  = str(s.vpc_id),
        cidr_block              = str(s.cidr_block),
        availability_zone       = str(s.availability_zone),
        availability_zone_id    = str(s.availability_zone_id),
        available_ip_count      = int(s.available_ip_count),
        map_public_ip_on_launch = bool(s.map_public_ip_on_launch),
        state                   = str(s.state),
        tags                    = {str(k): str(v) for k, v in s.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def subnet_list(ctx     : typer.Context,
                vpc     : str  = typer.Option('', '--vpc', help='Filter by VPC ID.'),
                az      : str  = typer.Option('', '--az',  help='Filter by availability zone.'),
                as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List subnets, optionally filtered by VPC and/or AZ."""
    client = ctx.obj['ec2_client']
    subs   = client.list_subnets(vpc_id=vpc, az=az)
    if as_json:
        typer.echo(json.dumps([_subnet_to_dict(s) for s in subs], indent=2))
        return
    if not subs:
        console.print('No subnets found.')
        return
    title = 'Subnets'
    if vpc: title += f' (vpc={vpc})'
    if az:  title += f' (az={az})'
    t = Table(title=title)
    t.add_column('Subnet ID', style='cyan')
    t.add_column('VPC',       style='dim')
    t.add_column('CIDR',      style='green')
    t.add_column('AZ',        style='dim')
    t.add_column('Free IPs',  style='dim', justify='right')
    t.add_column('Public',    style='dim')
    t.add_column('State',     style='bold')
    for s in subs:
        t.add_row(str(s.subnet_id),
                  str(s.vpc_id)            or '—',
                  str(s.cidr_block)        or '—',
                  str(s.availability_zone) or '—',
                  str(s.available_ip_count),
                  'yes' if s.map_public_ip_on_launch else 'no',
                  str(s.state)             or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def subnet_show(ctx       : typer.Context,
                subnet_id : str  = typer.Argument(..., help='Subnet ID (subnet-*).'),
                as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one subnet."""
    client = ctx.obj['ec2_client']
    sub    = client.describe_subnet(subnet_id)
    if sub is None:
        console.print(f'[red]Subnet not found:[/red] {subnet_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_subnet_to_dict(sub), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=24)
    t.add_column()
    rows = [
        ('subnet id',          str(sub.subnet_id)),
        ('vpc',                str(sub.vpc_id)               or '—'),
        ('cidr block',         str(sub.cidr_block)           or '—'),
        ('availability zone',  str(sub.availability_zone)    or '—'),
        ('availability zone id', str(sub.availability_zone_id) or '—'),
        ('available ip count', str(sub.available_ip_count)),
        ('map public ip',      'yes' if sub.map_public_ip_on_launch else 'no'),
        ('state',              str(sub.state)                or '—'),
        ('tags',               ', '.join(f'{k}={v}' for k, v in sub.tags.items()) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def subnet_create(ctx     : typer.Context,
                  vpc     : str  = typer.Option(...,  '--vpc',    help='VPC ID (vpc-*).'),
                  cidr    : str  = typer.Option(...,  '--cidr',   help='IPv4 CIDR for the subnet.'),
                  az      : str  = typer.Option('',   '--az',     help='Availability zone (optional).'),
                  name    : str  = typer.Option('',   '--name',   help='Optional Name tag.'),
                  public  : bool = typer.Option(False,'--public', help='Set MapPublicIpOnLaunch after create.'),
                  yes     : bool = typer.Option(False,'--yes',    help='Skip confirmation prompt.'),
                  as_json : bool = typer.Option(False,'--json',   help='Output as JSON.')):
    """Create a new subnet inside a VPC (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Create subnet {cidr} in {vpc}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    tags   = {'Name': name} if name else None
    subnet = client.create_subnet(vpc_id=vpc, cidr=cidr,
                                   availability_zone=az, tags=tags)
    if public:
        client.modify_subnet_attribute(str(subnet.subnet_id),
                                        map_public_ip_on_launch=True)
    if as_json:
        typer.echo(json.dumps({'ok'        : True,
                                'subnet_id' : str(subnet.subnet_id),
                                'vpc_id'    : str(subnet.vpc_id),
                                'cidr_block': str(subnet.cidr_block),
                                'public'    : bool(public)}, indent=2))
        return
    console.print(f'[green]Created[/green] {subnet.subnet_id} ({subnet.cidr_block})')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def subnet_delete(ctx       : typer.Context,
                  subnet_id : str  = typer.Argument(..., help='Subnet ID (subnet-*).'),
                  yes       : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                  as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a subnet (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Delete subnet {subnet_id}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True, 'subnet_id': subnet_id}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    deleted = client.delete_subnet(subnet_id)
    if as_json:
        typer.echo(json.dumps({'ok': bool(deleted), 'subnet_id': subnet_id,
                                'deleted': bool(deleted)}, indent=2))
        return
    if deleted:
        console.print(f'[green]Deleted[/green] {subnet_id}')
    else:
        console.print(f'[yellow]Not deleted[/yellow] {subnet_id} (already gone?)')
        raise typer.Exit(1)


# ── modify-attr ───────────────────────────────────────────────────────────────

@app.command('modify-attr')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def subnet_modify_attr(ctx       : typer.Context,
                       subnet_id : str  = typer.Argument(..., help='Subnet ID (subnet-*).'),
                       public    : bool = typer.Option(None, '--public/--no-public',
                                                        help='Set MapPublicIpOnLaunch.'),
                       as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Modify a subnet's attributes (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if public is None:
        console.print('[red]Nothing to change.[/red] Use --public / --no-public.')
        raise typer.Exit(1)
    client = ctx.obj['ec2_client']
    client.modify_subnet_attribute(subnet_id, map_public_ip_on_launch=public)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'subnet_id': subnet_id,
                                'map_public_ip_on_launch': bool(public)}, indent=2))
        return
    console.print(f'[green]Modified[/green] {subnet_id}')
