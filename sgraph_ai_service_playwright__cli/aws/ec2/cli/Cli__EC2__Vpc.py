# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Vpc
# Typer CLI surface for `sg aws ec2 vpc *` commands.
#
# Command tree:
#   sg aws ec2 vpc list  [--vpc-substring TEXT] [--json]
#   sg aws ec2 vpc show  <vpc-id>             [--json]
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

app = typer.Typer(name='vpc', help='EC2 VPC inspection (read-only).',
                  no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _vpc_to_dict(vpc) -> dict:                                                  # JSON-safe view of Schema__EC2__VPC
    return dict(
        vpc_id           = str(vpc.vpc_id),
        cidr_block       = str(vpc.cidr_block),
        is_default       = bool(vpc.is_default),
        state            = str(vpc.state),
        dhcp_options_id  = str(vpc.dhcp_options_id),
        instance_tenancy = str(vpc.instance_tenancy),
        tags             = {str(k): str(v) for k, v in vpc.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def vpc_list(ctx           : typer.Context,
             vpc_substring : str  = typer.Option('', '--vpc-substring',
                                                  help='Client-side filter: keep VPCs whose id contains this substring.'),
             as_json       : bool = typer.Option(False, '--json',
                                                  help='Output as JSON.')):
    """List VPCs visible in the current account / region."""
    client = ctx.obj['ec2_client']
    vpcs   = client.list_vpcs(vpc_id_substring=vpc_substring)
    if as_json:
        typer.echo(json.dumps([_vpc_to_dict(v) for v in vpcs], indent=2))
        return
    if not vpcs:
        console.print('No VPCs found.')
        return
    title = 'VPCs'
    if vpc_substring:
        title += f' (id~{vpc_substring})'
    t = Table(title=title)
    t.add_column('VPC ID',  style='cyan')
    t.add_column('CIDR',    style='green')
    t.add_column('Default', style='dim')
    t.add_column('State',   style='bold')
    t.add_column('Tenancy', style='dim')
    t.add_column('Name',    style='dim')
    for v in vpcs:
        name = str(v.tags.get('Name', '')) if 'Name' in v.tags else ''
        t.add_row(str(v.vpc_id),
                  str(v.cidr_block)       or '—',
                  'yes' if v.is_default else 'no',
                  str(v.state)            or '—',
                  str(v.instance_tenancy) or '—',
                  name                    or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def vpc_show(ctx     : typer.Context,
             vpc_id  : str  = typer.Argument(..., help='VPC ID (vpc-*).'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one VPC."""
    client = ctx.obj['ec2_client']
    vpc    = client.describe_vpc(vpc_id)
    if vpc is None:
        console.print(f'[red]VPC not found:[/red] {vpc_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_vpc_to_dict(vpc), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('vpc id',           str(vpc.vpc_id)),
        ('cidr block',       str(vpc.cidr_block)       or '—'),
        ('default',          'yes' if vpc.is_default else 'no'),
        ('state',            str(vpc.state)            or '—'),
        ('dhcp options',     str(vpc.dhcp_options_id)  or '—'),
        ('instance tenancy', str(vpc.instance_tenancy) or '—'),
        ('tags',             ', '.join(f'{k}={v}' for k, v in vpc.tags.items()) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()
