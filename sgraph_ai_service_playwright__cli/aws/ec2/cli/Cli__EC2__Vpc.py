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
#   sg aws ec2 vpc create-stack --name <stack> [--cidr CIDR] [--az AZ ...]
#                              [--ingress PORTS] [--yes] [--time] [--json]
#   sg aws ec2 vpc delete-stack <stack> [--yes] [--json]
#   sg aws ec2 vpc show-stack   <stack> [--json]
#
# Mutations require SG_AWS__EC2__ALLOW_MUTATIONS=1.
# Slice 3 (v0.2.34): create-stack / delete-stack / show-stack compose the
# Slice 1/2 primitives into an end-to-end network stack discoverable by
# `Stack=<name>` tag. Idempotent + best-effort rollback.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing import List

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate           import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws._shared.Phase__Progress__Renderer import Phase__Progress__Renderer
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__VPC__Stack__Phase import Enum__VPC__Stack__Phase
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Request       import Schema__VPC__Stack__Request
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Ingress_Rule  import Schema__VPC__Stack__Ingress_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client     import EC2__AWS__Client
from sgraph_ai_service_playwright__cli.aws.ec2.service.VPC__Stack__Provisioner import VPC__Stack__Provisioner


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


# ── stack helpers ─────────────────────────────────────────────────────────────

def _parse_ingress_ports(spec: str) -> list:                                    # 'PORT[/PROTO][@CIDR],...' → list[(proto, port, cidr)]
    rules = []
    for token in (spec or '').split(','):
        token = token.strip()
        if not token:
            continue
        cidr  = '0.0.0.0/0'
        if '@' in token:
            token, cidr = token.split('@', 1)
            cidr = cidr.strip() or '0.0.0.0/0'
        proto = 'tcp'
        if '/' in token:
            token, proto = token.split('/', 1)
            proto = (proto.strip() or 'tcp').lower()
        token = token.strip()
        if not token:
            continue
        try:
            port = int(token)
        except ValueError as exc:
            raise typer.BadParameter(f'Invalid ingress port {token!r}: {exc}')
        rules.append((proto, port, cidr))
    return rules


def _phase_result_to_dict(p) -> dict:
    return {
        'name'       : str(p.name),
        'status'     : str(p.status) if p.status else '',
        'duration_ms': int(p.duration_ms),
        'detail'     : str(p.detail),
    }


def _report_to_dict(report) -> dict:
    return {
        'operation'         : str(report.operation),
        'stack_name'        : str(report.stack_name),
        'ok'                : bool(report.ok),
        'total_ms'          : int(report.total_ms),
        'vpc_id'            : str(report.vpc_id),
        'internet_gateway_id': str(report.internet_gateway_id),
        'route_table_id'    : str(report.route_table_id),
        'security_group_id' : str(report.security_group_id),
        'subnet_ids'        : [str(s) for s in (report.subnet_ids or [])],
        'phases'            : [_phase_result_to_dict(p) for p in (report.phases or [])],
        'error'             : str(report.error),
        'rollback_errors'   : [str(e) for e in (report.rollback_errors or [])],
    }


def _render_stack_summary(report) -> None:
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    t.add_row('stack',          str(report.stack_name))
    t.add_row('vpc',            str(report.vpc_id) or '—')
    t.add_row('igw',            str(report.internet_gateway_id) or '—')
    t.add_row('route table',    str(report.route_table_id) or '—')
    t.add_row('security group', str(report.security_group_id) or '—')
    subnet_text = ', '.join(str(s) for s in (report.subnet_ids or [])) or '—'
    t.add_row('subnets',        subnet_text)
    t.add_row('total ms',       str(report.total_ms))
    ok_label = '[green]ok[/green]' if report.ok else '[red]failed[/red]'
    t.add_row('status',         ok_label)
    console.print()
    console.print(t)
    console.print()


def _render_phase_table(report) -> None:
    t = Table(title='Stack phases', box=None, show_header=True, padding=(0, 2))
    t.add_column('Phase',  style='bold')
    t.add_column('Status', style='')
    t.add_column('ms',     justify='right', style='dim')
    t.add_column('Detail', style='dim')
    for p in (report.phases or []):
        t.add_row(str(p.name), str(p.status) if p.status else '',
                  str(p.duration_ms), str(p.detail))
    console.print(t)


# ── create-stack ──────────────────────────────────────────────────────────────

@app.command('create-stack')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def vpc_create_stack(ctx     : typer.Context,
                     name    : str       = typer.Option(...,                   '--name',
                                                          help='Stack name. Used for Stack=<name> tag and resource Name= prefixes.'),
                     cidr    : str       = typer.Option('10.0.0.0/16',         '--cidr',
                                                          help='IPv4 CIDR block for the VPC.'),
                     az      : List[str] = typer.Option([],                    '--az',
                                                          help='Availability zone (repeat for multiple). Default: first 2 from region.'),
                     ingress : str       = typer.Option('80,443,8080',         '--ingress',
                                                          help='Comma-separated TCP ingress ports (or "PORT/PROTO@CIDR"). Default: 80,443,8080.'),
                     yes     : bool      = typer.Option(False,                 '--yes',
                                                          help='Skip confirmation prompt.'),
                     time_   : bool      = typer.Option(False,                 '--time',
                                                          help='Show per-phase timing table after the run.'),
                     as_json : bool      = typer.Option(False,                 '--json',
                                                          help='Machine-readable JSON output.')):
    """Provision a full VPC + IGW + RT + 2 public subnets + SG stack."""
    client = ctx.obj['ec2_client']
    rules  = []
    for proto, port, cidr_block in _parse_ingress_ports(ingress):
        rules.append(Schema__VPC__Stack__Ingress_Rule(
            protocol   = proto,
            from_port  = port,
            to_port    = port,
            cidr_block = cidr_block,
        ))

    request = Schema__VPC__Stack__Request(stack_name=name, cidr=cidr)
    for a in (az or []):
        a_clean = (a or '').strip()
        if a_clean:
            request.availability_zones.append(a_clean)
    for r in rules:
        request.ingress_rules.append(r)

    if not yes and not as_json:
        if not typer.confirm(f'Create VPC stack {name!r} ({cidr})?', default=True):
            console.print('[yellow]Aborted.[/yellow]')
            raise typer.Exit(0)

    provisioner = VPC__Stack__Provisioner(ec2_client=client)
    phase_names = [p.value for p in Enum__VPC__Stack__Phase]

    if as_json:
        report = provisioner.create_stack(request)
        typer.echo(json.dumps(_report_to_dict(report), indent=2))
        if not report.ok:
            raise typer.Exit(1)
        return

    with Phase__Progress__Renderer(title=f'create-stack — {name}',
                                    phases=phase_names) as renderer:
        provisioner.progress_cb = renderer.as_progress_cb()
        report = provisioner.create_stack(request)

    _render_stack_summary(report)
    if time_:
        _render_phase_table(report)
    if report.ok:
        # Friendly hint mentioning the vault-app auto-resolve flow.
        console.print(Panel(
            f'Stack [bold]{report.stack_name}[/bold] is provisioned.\n\n'
            f'  vpc: [cyan]{report.vpc_id}[/cyan]\n'
            f'  subnets: [cyan]{", ".join(report.subnet_ids)}[/cyan]\n'
            f'  sg: [cyan]{report.security_group_id}[/cyan]\n\n'
            f'Next: [dim]sg vault-app fargate setup create --yes[/dim] '
            f'will auto-resolve these when --subnets/--sg are omitted.',
            title='[green]VPC stack ready[/green]',
            border_style='green',
        ))
    else:
        console.print(f'[red]Stack creation failed:[/red] {report.error}')
        if report.rollback_errors:
            console.print('[yellow]Rollback errors:[/yellow]')
            for e in report.rollback_errors:
                console.print(f'  {e}')
        raise typer.Exit(1)


# ── delete-stack ──────────────────────────────────────────────────────────────

@app.command('delete-stack')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def vpc_delete_stack(ctx     : typer.Context,
                     name    : str  = typer.Argument(..., help='Stack name (Stack=<name> tag).'),
                     yes     : bool = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                     as_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    """Tear down a VPC stack and all its resources (idempotent)."""
    client = ctx.obj['ec2_client']
    if not yes and not as_json:
        if not typer.confirm(f'Delete VPC stack {name!r} and ALL its resources?',
                              default=False):
            console.print('[yellow]Aborted.[/yellow]')
            raise typer.Exit(0)
    provisioner = VPC__Stack__Provisioner(ec2_client=client)
    report      = provisioner.delete_stack(name)
    if as_json:
        typer.echo(json.dumps(_report_to_dict(report), indent=2))
        if not report.ok:
            raise typer.Exit(1)
        return
    _render_stack_summary(report)
    _render_phase_table(report)
    if not report.ok:
        console.print(f'[red]Stack deletion failed:[/red] {report.error}')
        raise typer.Exit(1)


# ── show-stack ────────────────────────────────────────────────────────────────

@app.command('show-stack')
@spec_cli_errors
def vpc_show_stack(ctx     : typer.Context,
                   name    : str  = typer.Argument(..., help='Stack name (Stack=<name> tag).'),
                   as_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    """Show resources currently owned by a named stack (read-only)."""
    client = ctx.obj['ec2_client']
    detail = VPC__Stack__Provisioner(ec2_client=client).describe_stack(name)
    if detail is None:
        if as_json:
            typer.echo(json.dumps({'found': False, 'stack_name': name}, indent=2))
        else:
            console.print(f'[yellow]No stack found with Stack={name!r}.[/yellow]')
        raise typer.Exit(1)
    payload = {
        'found'              : True,
        'stack_name'         : str(detail.stack_name),
        'vpc_id'             : str(detail.vpc_id),
        'internet_gateway_id': str(detail.internet_gateway_id),
        'route_table_id'     : str(detail.route_table_id),
        'security_group_id'  : str(detail.security_group_id),
        'subnet_ids'         : [str(s) for s in (detail.subnet_ids or [])],
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    t.add_row('stack',          payload['stack_name'])
    t.add_row('vpc',            payload['vpc_id'] or '—')
    t.add_row('igw',            payload['internet_gateway_id'] or '—')
    t.add_row('route table',    payload['route_table_id'] or '—')
    t.add_row('security group', payload['security_group_id'] or '—')
    t.add_row('subnets',        ', '.join(payload['subnet_ids']) or '—')
    console.print()
    console.print(t)
    console.print()
