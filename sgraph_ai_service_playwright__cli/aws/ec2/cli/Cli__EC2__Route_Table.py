# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Route_Table
# Typer CLI surface for `sg aws ec2 route-table *` commands.
#
# Command tree:
#   sg aws ec2 route-table list  [--vpc <vpc-id>] [--json]
#   sg aws ec2 route-table show  <rtb-id>         [--json]
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

app = typer.Typer(name='route-table',
                  help='EC2 Route Table inspection (read-only).',
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
