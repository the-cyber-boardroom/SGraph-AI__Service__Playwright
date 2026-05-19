# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Subnet
# Typer CLI surface for `sg aws ec2 subnet *` commands.
#
# Command tree:
#   sg aws ec2 subnet list  [--vpc <vpc-id>] [--az <az>] [--json]
#   sg aws ec2 subnet show  <subnet-id>                  [--json]
#
# Read-only commands — no mutation gate required (Slice 1 of 3).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client     import EC2__AWS__Client


console = Console()

app = typer.Typer(name='subnet', help='EC2 Subnet inspection (read-only).',
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
