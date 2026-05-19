# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Eni
# Typer CLI surface for `sg aws ec2 eni *` commands.
#
# Command tree:
#   sg aws ec2 eni list  [--sg sg-xxx] [--vpc vpc-yyy] [--json]
#   sg aws ec2 eni show  <eni-id>                       [--json]
#
# Read-only commands — no mutation gate required.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client     import EC2__AWS__Client


console = Console()

app = typer.Typer(name='eni', help='EC2 Elastic Network Interface inspection.',
                  no_args_is_help=True)


# ── helpers ───────────────────────────────────────────────────────────────────

@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _eni_to_dict(eni) -> dict:                                               # JSON-safe view of Schema__EC2__ENI
    return dict(
        eni_id                 = str(eni.eni_id),
        subnet_id              = str(eni.subnet_id),
        vpc_id                 = str(eni.vpc_id),
        public_ip              = str(eni.public_ip),
        private_ip             = str(eni.private_ip),
        attachment_instance_id = str(eni.attachment_instance_id),
        attachment_status      = str(eni.attachment_status),
        security_group_ids     = list(eni.security_group_ids or []),
        description            = str(eni.description),
        status                 = str(eni.status),
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def eni_list(ctx    : typer.Context,
             sg     : str  = typer.Option('', '--sg',
                                           help='Filter by security group ID.'),
             vpc    : str  = typer.Option('', '--vpc',
                                           help='Filter by VPC ID.'),
             as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List Elastic Network Interfaces, optionally filtered by SG or VPC."""
    client = ctx.obj['ec2_client']
    enis   = client.list_enis(sg_id=sg, vpc_id=vpc)
    if as_json:
        typer.echo(json.dumps([_eni_to_dict(e) for e in enis], indent=2))
        return
    if not enis:
        console.print('No network interfaces found.')
        return
    title = 'Elastic Network Interfaces'
    if sg:  title += f' (sg={sg})'
    if vpc: title += f' (vpc={vpc})'
    t = Table(title=title)
    t.add_column('ENI ID',     style='cyan')
    t.add_column('Subnet',     style='dim')
    t.add_column('VPC',        style='dim')
    t.add_column('Private IP', style='green')
    t.add_column('Public IP',  style='green')
    t.add_column('Status',     style='bold')
    for eni in enis:
        t.add_row(str(eni.eni_id),
                  str(eni.subnet_id)  or '—',
                  str(eni.vpc_id)     or '—',
                  str(eni.private_ip) or '—',
                  str(eni.public_ip)  or '—',
                  str(eni.status)     or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def eni_show(ctx    : typer.Context,
             eni_id : str  = typer.Argument(..., help='ENI ID (eni-*).'),
             as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one Elastic Network Interface."""
    client = ctx.obj['ec2_client']
    eni    = client.describe_network_interface(eni_id)
    if eni is None:
        console.print(f'[red]Network interface not found:[/red] {eni_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_eni_to_dict(eni), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=24)
    t.add_column()
    rows = [
        ('eni id',              str(eni.eni_id)),
        ('subnet',              str(eni.subnet_id)              or '—'),
        ('vpc',                 str(eni.vpc_id)                 or '—'),
        ('private ip',          str(eni.private_ip)             or '—'),
        ('public ip',           str(eni.public_ip)              or '—'),
        ('status',              str(eni.status)                 or '—'),
        ('attachment instance', str(eni.attachment_instance_id) or '—'),
        ('attachment status',   str(eni.attachment_status)      or '—'),
        ('security groups',     ', '.join(eni.security_group_ids or []) or '(none)'),
        ('description',         str(eni.description)            or '—'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()
