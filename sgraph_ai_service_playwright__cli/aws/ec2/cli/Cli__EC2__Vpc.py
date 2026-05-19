# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Vpc
# Typer CLI surface for `sg aws ec2 vpc *` commands.
#
# Command tree:
#   sg aws ec2 vpc list        [--vpc-substring TEXT] [--json]
#   sg aws ec2 vpc show        <vpc-id>                                  [--json]
#   sg aws ec2 vpc create      [--cidr 10.0.0.0/16] [--name <tag>]
#                              [--enable-dns/--no-enable-dns]
#                              [--enable-dns-hostnames/--no-enable-dns-hostnames]
#                              [--yes] [--json]
#   sg aws ec2 vpc delete      <vpc-id> [--yes] [--json]
#   sg aws ec2 vpc modify-attr <vpc-id>
#                              [--enable-dns/--no-enable-dns]
#                              [--enable-dns-hostnames/--no-enable-dns-hostnames]
#                              [--json]
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

app = typer.Typer(name='vpc', help='EC2 VPC inspection and mutation.',
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


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def vpc_create(ctx                  : typer.Context,
               cidr                 : str  = typer.Option('10.0.0.0/16', '--cidr',
                                                           help='IPv4 CIDR block.'),
               name                 : str  = typer.Option('', '--name',
                                                           help='Optional Name tag.'),
               enable_dns           : bool = typer.Option(False, '--enable-dns/--no-enable-dns',
                                                           help='Set EnableDnsSupport after create.'),
               enable_dns_hostnames : bool = typer.Option(False, '--enable-dns-hostnames/--no-enable-dns-hostnames',
                                                           help='Set EnableDnsHostnames after create.'),
               yes                  : bool = typer.Option(False, '--yes', help='Skip confirmation prompt.'),
               as_json              : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Create a new VPC (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Create VPC with CIDR {cidr}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    tags = {'Name': name} if name else None
    vpc  = client.create_vpc(cidr=cidr, tags=tags)
    # Apply attribute toggles after create — typer flag defaults make this an
    # opt-in; we only call modify when the user explicitly used the flag form.
    if enable_dns:
        client.modify_vpc_attribute(str(vpc.vpc_id), enable_dns_support=True)
    if enable_dns_hostnames:
        client.modify_vpc_attribute(str(vpc.vpc_id), enable_dns_hostnames=True)
    if as_json:
        typer.echo(json.dumps({'ok': True, 'vpc_id': str(vpc.vpc_id),
                                'cidr_block': str(vpc.cidr_block)}, indent=2))
        return
    console.print(f'[green]Created[/green] {vpc.vpc_id} ({vpc.cidr_block})')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def vpc_delete(ctx     : typer.Context,
               vpc_id  : str  = typer.Argument(..., help='VPC ID (vpc-*).'),
               yes     : bool = typer.Option(False, '--yes', help='Skip confirmation prompt.'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a VPC (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    if not yes and not typer.confirm(f'Delete VPC {vpc_id}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True, 'vpc_id': vpc_id}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    deleted = client.delete_vpc(vpc_id)
    if as_json:
        typer.echo(json.dumps({'ok': bool(deleted), 'vpc_id': vpc_id,
                                'deleted': bool(deleted)}, indent=2))
        return
    if deleted:
        console.print(f'[green]Deleted[/green] {vpc_id}')
    else:
        console.print(f'[yellow]Not deleted[/yellow] {vpc_id} (already gone?)')
        raise typer.Exit(1)


# ── modify-attr ───────────────────────────────────────────────────────────────

@app.command('modify-attr')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def vpc_modify_attr(ctx                  : typer.Context,
                    vpc_id               : str  = typer.Argument(..., help='VPC ID (vpc-*).'),
                    enable_dns           : bool = typer.Option(None, '--enable-dns/--no-enable-dns',
                                                                help='Set EnableDnsSupport.'),
                    enable_dns_hostnames : bool = typer.Option(None, '--enable-dns-hostnames/--no-enable-dns-hostnames',
                                                                help='Set EnableDnsHostnames.'),
                    as_json              : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Modify a VPC's DNS attributes (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if enable_dns is None and enable_dns_hostnames is None:
        console.print('[red]Nothing to change.[/red] Use --enable-dns / --enable-dns-hostnames.')
        raise typer.Exit(1)
    client = ctx.obj['ec2_client']
    client.modify_vpc_attribute(vpc_id,
                                 enable_dns_support  =enable_dns,
                                 enable_dns_hostnames=enable_dns_hostnames)
    if as_json:
        payload = {'ok': True, 'vpc_id': vpc_id}
        if enable_dns is not None:           payload['enable_dns_support']   = bool(enable_dns)
        if enable_dns_hostnames is not None: payload['enable_dns_hostnames'] = bool(enable_dns_hostnames)
        typer.echo(json.dumps(payload, indent=2))
        return
    console.print(f'[green]Modified[/green] {vpc_id}')
