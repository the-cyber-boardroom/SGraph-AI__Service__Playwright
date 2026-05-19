# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Igw
# Typer CLI surface for `sg aws ec2 igw *` commands.
#
# Command tree:
#   sg aws ec2 igw list  [--vpc <vpc-id>] [--json]
#   sg aws ec2 igw show  <igw-id>         [--json]
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

app = typer.Typer(name='igw', help='EC2 Internet Gateway inspection (read-only).',
                  no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _igw_to_dict(igw) -> dict:                                                 # JSON-safe view of Schema__EC2__Internet_Gateway
    return dict(
        igw_id = str(igw.igw_id),
        vpc_id = str(igw.vpc_id),
        state  = str(igw.state),
        tags   = {str(k): str(v) for k, v in igw.tags.items()},
    )


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def igw_list(ctx     : typer.Context,
             vpc     : str  = typer.Option('', '--vpc', help='Filter by attached VPC ID.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List Internet Gateways, optionally filtered by attached VPC."""
    client = ctx.obj['ec2_client']
    igws   = client.list_internet_gateways(vpc_id=vpc)
    if as_json:
        typer.echo(json.dumps([_igw_to_dict(i) for i in igws], indent=2))
        return
    if not igws:
        console.print('No internet gateways found.')
        return
    title = 'Internet Gateways'
    if vpc:
        title += f' (vpc={vpc})'
    t = Table(title=title)
    t.add_column('IGW ID', style='cyan')
    t.add_column('VPC',    style='dim')
    t.add_column('State',  style='bold')
    t.add_column('Name',   style='dim')
    for i in igws:
        name = str(i.tags.get('Name', '')) if 'Name' in i.tags else ''
        t.add_row(str(i.igw_id),
                  str(i.vpc_id) or '(detached)',
                  str(i.state)  or '—',
                  name          or '—')
    console.print(t)


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def igw_show(ctx     : typer.Context,
             igw_id  : str  = typer.Argument(..., help='Internet Gateway ID (igw-*).'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one Internet Gateway."""
    client = ctx.obj['ec2_client']
    igw    = client.describe_internet_gateway(igw_id)
    if igw is None:
        console.print(f'[red]Internet gateway not found:[/red] {igw_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(_igw_to_dict(igw), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('igw id',  str(igw.igw_id)),
        ('vpc',     str(igw.vpc_id) or '(detached)'),
        ('state',   str(igw.state)  or '—'),
        ('tags',    ', '.join(f'{k}={v}' for k, v in igw.tags.items()) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()
