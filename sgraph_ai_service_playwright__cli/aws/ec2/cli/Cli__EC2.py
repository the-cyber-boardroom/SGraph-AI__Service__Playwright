# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2
# Typer CLI surface for `sg aws ec2 *` commands.
#
# Command tree:
#   sg aws ec2 list           [--state running|stopped|all] [--prefix NAME] [--tag K=V] [--json]
#   sg aws ec2 describe       <id-or-name> [--json]
#   sg aws ec2 ssh-info       <id-or-name>
#   sg aws ec2 tags           <id-or-name> [--json] [--add K=V ...] [--remove K ...] [--clear]
#   sg aws ec2 instance-types [--family FAMILY] [--json]
#   sg aws ec2 pricing        <instance-type> [--region R] [--json]
#   sg aws ec2 create         --name NAME --instance-type TYPE --ami AMI [--key KEY]
#                             [--subnet SN] [--sg SG] [--tags k=v ...] [--wait] [--yes]
#   sg aws ec2 start          <id-or-name> [--yes]
#   sg aws ec2 stop           <id-or-name> [--yes]
#   sg aws ec2 terminate      <id-or-name> [--yes]
#   sg aws ec2 wait           <id-or-name> --state STATE [--timeout 300]
#
# Read-only commands always allowed.
# Mutations require SG_AWS__EC2__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from typing import List, Optional

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm                import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate              import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Ami               import app as ami_app
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id          import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type  import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Create__Request      import Schema__EC2__Create__Request
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client         import EC2__AWS__Client
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__Instance__Wait      import EC2__Instance__Wait
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__Name__Resolver      import EC2__Name__Resolver
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__Pricing__Client     import EC2__Pricing__Client
from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors

_MUTATION_ENV = 'SG_AWS__EC2__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='ec2', help='EC2 instance management.', no_args_is_help=True)

app.add_typer(ami_app, name='ami')


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())
    ctx.obj.setdefault('ec2_resolver', EC2__Name__Resolver(ec2_client=ctx.obj['ec2_client']).setup())


def _resolve(ctx: typer.Context, target: str) -> str:                          # Resolves <id-or-name> → concrete instance ID; exits 1 on error
    try:
        return ctx.obj['ec2_resolver'].resolve(target)
    except ValueError as exc:
        console.print(f'[red]{exc}[/red]')
        raise typer.Exit(1)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def ec2_list(ctx    : typer.Context,
             state  : str  = typer.Option('all', '--state', '-s',
                                           help='Filter by state: running, stopped, all.'),
             prefix : str  = typer.Option('',    '--prefix', '-p',
                                           help='Filter by Name tag prefix.'),
             tag    : List[str] = typer.Option([], '--tag',
                                           help='Filter by tag K=V (repeatable).'),
             as_json: bool = typer.Option(False,  '--json', help='Output as JSON.')):
    """List EC2 instances, optionally filtered by state / name prefix / tags."""
    client  = ctx.obj['ec2_client']
    tf      = []
    for kv in tag:
        if '=' in kv:
            k, v = kv.split('=', 1)
            tf.append({'Name': f'tag:{k}', 'Values': [v]})
    instances = client.list_instances(state=state, name_prefix=prefix, tag_filters=tf or None)
    if as_json:
        typer.echo(json.dumps([dict(instance_id  = str(i.instance_id),
                                    name         = str(i.name),
                                    instance_type= str(i.instance_type),
                                    state        = str(i.state),
                                    public_ip    = str(i.public_ip),
                                    private_ip   = str(i.private_ip),
                                    launch_time  = str(i.launch_time),
                                    key_name     = str(i.key_name)) for i in instances], indent=2))
        return
    if not instances:
        console.print('No instances found.')
        return
    t = Table(title='EC2 Instances')
    t.add_column('ID',           style='cyan')
    t.add_column('Name',         style='green')
    t.add_column('Type',         style='dim')
    t.add_column('State',        style='bold')
    t.add_column('Public IP',    style='dim')
    t.add_column('Key',          style='dim')
    for i in instances:
        state_style = 'green' if str(i.state) == 'running' else ('yellow' if str(i.state) == 'stopped' else 'dim')
        t.add_row(str(i.instance_id), str(i.name), str(i.instance_type),
                  f'[{state_style}]{i.state}[/]', str(i.public_ip) or '—', str(i.key_name) or '—')
    console.print(t)


# ── describe ──────────────────────────────────────────────────────────────────

@app.command('describe')
@spec_cli_errors
def ec2_describe(ctx    : typer.Context,
                 target : str  = typer.Argument(..., help='Instance ID or Name tag.'),
                 as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for an EC2 instance."""
    iid    = _resolve(ctx, target)
    detail = ctx.obj['ec2_client'].describe_instance(iid)
    if detail is None:
        console.print(f'[red]Instance not found:[/red] {target}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            instance_id          = str(detail.instance_id),
            name                 = str(detail.name),
            instance_type        = str(detail.instance_type),
            state                = str(detail.state),
            ami_id               = str(detail.ami_id),
            public_ip            = str(detail.public_ip),
            public_dns           = str(detail.public_dns),
            private_ip           = str(detail.private_ip),
            private_dns          = str(detail.private_dns),
            key_name             = str(detail.key_name),
            launch_time          = str(detail.launch_time),
            vpc_id               = str(detail.vpc_id),
            subnet_id            = str(detail.subnet_id),
            architecture         = str(detail.architecture),
            platform             = str(detail.platform),
            iam_instance_profile = str(detail.iam_instance_profile),
            root_device_type     = str(detail.root_device_type),
            tags                 = {str(k): str(v) for k, v in detail.tags.items()},
            security_groups      = [{'group_id': str(sg.group_id), 'group_name': str(sg.group_name)}
                                    for sg in detail.security_groups],
        ), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('id',              str(detail.instance_id)),
        ('name',            str(detail.name)               or '—'),
        ('type',            str(detail.instance_type)),
        ('state',           str(detail.state)),
        ('ami',             str(detail.ami_id)),
        ('public ip',       str(detail.public_ip)          or '—'),
        ('public dns',      str(detail.public_dns)         or '—'),
        ('private ip',      str(detail.private_ip)         or '—'),
        ('key name',        str(detail.key_name)           or '—'),
        ('launched',        str(detail.launch_time)        or '—'),
        ('vpc',             str(detail.vpc_id)             or '—'),
        ('subnet',          str(detail.subnet_id)          or '—'),
        ('architecture',    str(detail.architecture)       or '—'),
        ('platform',        str(detail.platform)           or '—'),
        ('iam profile',     str(detail.iam_instance_profile) or '—'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── ssh-info ──────────────────────────────────────────────────────────────────

@app.command('ssh-info')
@spec_cli_errors
def ec2_ssh_info(ctx   : typer.Context,
                 target: str = typer.Argument(..., help='Instance ID or Name tag.')):
    """Print SSH connection information (public DNS, key name, default user)."""
    iid    = _resolve(ctx, target)
    detail = ctx.obj['ec2_client'].describe_instance(iid)
    if detail is None:
        console.print(f'[red]Instance not found:[/red] {target}')
        raise typer.Exit(1)
    if not str(detail.public_ip) and not str(detail.public_dns):
        console.print('[yellow]No public IP or DNS — instance may be in a private subnet or stopped.[/yellow]')
        raise typer.Exit(1)
    host     = str(detail.public_dns) or str(detail.public_ip)
    key_name = str(detail.key_name) or '<key-name>'
    user     = 'ec2-user'                                                      # Amazon Linux / AL2023 default
    if 'ubuntu' in str(detail.ami_id).lower() or 'ubuntu' in str(detail.name).lower():
        user = 'ubuntu'
    console.print()
    console.print(f'  [bold]Host :[/bold]  {host}')
    console.print(f'  [bold]Key  :[/bold]  ~/.ssh/{key_name}.pem  (key never stored here — retrieve from vault)')
    console.print(f'  [bold]User :[/bold]  {user}')
    console.print()
    console.print(f'  [dim]ssh -i ~/.ssh/{key_name}.pem {user}@{host}[/dim]')
    console.print()


# ── tags ──────────────────────────────────────────────────────────────────────

@app.command('tags')
@spec_cli_errors
def ec2_tags(ctx     : typer.Context,
             target  : str       = typer.Argument(..., help='Instance ID or Name tag.'),
             add     : List[str] = typer.Option([], '--add',      help='Add tag K=V (repeatable, mutating).'),
             remove  : List[str] = typer.Option([], '--remove',   help='Remove tag by key (repeatable, mutating).'),
             clear   : bool      = typer.Option(False, '--clear',   help='Remove all tags (mutating).'),
             yes     : bool      = typer.Option(False, '--yes',     help='Skip confirmation for mutations.'),
             dry_run : bool      = typer.Option(False, '--dry-run', help='Print action without executing.'),
             as_json : bool      = typer.Option(False, '--json',    help='Output current tags as JSON.')):
    """View and optionally modify tags on an EC2 instance."""
    is_mutating = bool(add or remove or clear)
    if is_mutating:
        if os.environ.get(_MUTATION_ENV) != '1':
            console.print(f'[red]Set {_MUTATION_ENV}=1 to allow tag mutations.[/red]')
            raise typer.Exit(1)
        if not confirm_or_abort(f'Modify tags on {target!r}?', yes=yes, dry_run=dry_run):
            raise typer.Exit(0)
    iid    = _resolve(ctx, target)
    client = ctx.obj['ec2_client']
    if clear:
        current = client.get_instance_tags(iid)
        client.remove_tags(iid, list(current.keys()))
    if add:
        add_dict = {}
        for kv in add:
            if '=' in kv:
                k, v = kv.split('=', 1)
                add_dict[k] = v
        if add_dict:
            client.add_tags(iid, add_dict)
    if remove:
        client.remove_tags(iid, list(remove))
    current = client.get_instance_tags(iid)
    if as_json:
        typer.echo(json.dumps(current, indent=2))
        return
    if not current:
        console.print('(no tags)')
        return
    t = Table(title=f'Tags — {iid}')
    t.add_column('Key',   style='cyan')
    t.add_column('Value', style='dim')
    for k, v in sorted(current.items()):
        t.add_row(k, v)
    console.print(t)


# ── instance-types ────────────────────────────────────────────────────────────

@app.command('instance-types')
@spec_cli_errors
def ec2_instance_types(ctx    : typer.Context,
                       family : str  = typer.Option('', '--family', '-f',
                                                     help='Filter by family prefix, e.g. m5, t3.'),
                       as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List EC2 instance types available in the current region."""
    types = ctx.obj['ec2_client'].list_instance_types(family=family)
    if as_json:
        typer.echo(json.dumps(types, indent=2))
        return
    if not types:
        console.print('No instance types found.')
        return
    t = Table(title='EC2 Instance Types')
    t.add_column('Instance Type', style='cyan')
    for itype in types:
        t.add_row(itype)
    console.print(t)


# ── pricing ───────────────────────────────────────────────────────────────────

@app.command('pricing')
@spec_cli_errors
def ec2_pricing(instance_type: str  = typer.Argument(..., help='Instance type, e.g. t3.micro.'),
                region       : str  = typer.Option('us-east-1', '--region', '-r',
                                                   help='AWS region (default: us-east-1).'),
                as_json      : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Look up on-demand pricing for an EC2 instance type."""
    pricing = EC2__Pricing__Client().get_price(instance_type=instance_type, region=region)
    if as_json:
        typer.echo(json.dumps(dict(instance_type   = str(pricing.instance_type),
                                   region          = str(pricing.region),
                                   price_per_hour  = str(pricing.price_per_hour),
                                   price_per_second= str(pricing.price_per_second),
                                   currency        = str(pricing.currency),
                                   os              = str(pricing.os)), indent=2))
        return
    if not str(pricing.price_per_hour):
        console.print(f'[yellow]No pricing data found for {instance_type!r} in {region!r}.[/yellow]')
        return
    console.print()
    console.print(f'  [bold]{instance_type}[/bold] — {region} ({pricing.os})')
    console.print(f'  Per hour   : [green]{pricing.price_per_hour} {pricing.currency}[/green]')
    console.print(f'  Per second : [dim]{pricing.price_per_second} {pricing.currency}[/dim]')
    console.print()


# ── create ────────────────────────────────────────────────────────────────────

@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ec2_create(ctx           : typer.Context,
               name          : str       = typer.Option(...,   '--name',          help='Instance name (becomes Name tag).'),
               instance_type : str       = typer.Option(...,   '--instance-type', help='EC2 instance type.'),
               ami           : str       = typer.Option(...,   '--ami',           help='AMI ID or alias.'),
               key_pair      : str       = typer.Option('',    '--key-pair',      help='Key pair name.'),
               subnet        : str       = typer.Option('',    '--subnet',        help='Subnet ID.'),
               security_group: str       = typer.Option('',    '--sg',            help='Security group ID(s), comma-separated.'),
               user_data_file: str       = typer.Option('',    '--user-data',     help='Path to cloud-init script.'),
               extra_tags    : List[str] = typer.Option([],    '--tags',          help='Extra tags K=V (repeatable).'),
               wait          : bool      = typer.Option(True,  '--wait/--no-wait',help='Wait for running state.'),
               yes           : bool      = typer.Option(False, '--yes',           help='Skip confirmation.'),
               dry_run       : bool      = typer.Option(False, '--dry-run',       help='Print action without executing.'),
               as_json       : bool      = typer.Option(False, '--json',          help='Output as JSON.')):
    """Launch a new EC2 instance (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if not confirm_or_abort(f'Create instance {name!r} ({instance_type}, {ami})?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    user_data_content = ''
    if user_data_file:
        try:
            with open(user_data_file) as fh:
                user_data_content = fh.read()
        except OSError as exc:
            console.print(f'[red]Cannot read user-data file:[/red] {exc}')
            raise typer.Exit(1)
    from sgraph_ai_service_playwright__cli.aws._shared.Aws__Tagger              import Aws__Tagger
    from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Surface import Enum__AWS__Surface
    sg_tags = Aws__Tagger().as_boto3_tags(Enum__AWS__Surface.EC2, 'create')
    for kv in extra_tags:
        if '=' in kv:
            k, v = kv.split('=', 1)
            sg_tags.append({'Key': k, 'Value': v})
    ami_id_safe   = Safe_Str__EC2__AMI_Id(ami)           if ami           else Safe_Str__EC2__AMI_Id('')
    itype_safe    = Safe_Str__EC2__Instance__Type(instance_type) if instance_type else Safe_Str__EC2__Instance__Type('')
    request = Schema__EC2__Create__Request(
        name             = name,
        instance_type    = itype_safe,
        ami_id           = ami_id_safe,
        key_pair         = key_pair,
        subnet_id        = subnet,
        security_groups  = security_group,
        user_data        = user_data_content,
        wait_for_running = wait,
    )
    client  = ctx.obj['ec2_client']
    iid     = client.create_instance(request, extra_tags=sg_tags)
    if not iid:
        console.print('[red]Failed to create instance.[/red]')
        raise typer.Exit(1)
    if wait:
        waiter = EC2__Instance__Wait(ec2_client=client)
        ok     = waiter.wait(iid, Enum__EC2__Instance__State.RUNNING)
        if not ok:
            console.print(f'[yellow]Timeout waiting for {iid} to reach running state.[/yellow]')
    if as_json:
        typer.echo(json.dumps({'instance_id': iid, 'name': name}, indent=2))
        return
    console.print(f'[green]Created[/green] {iid} ({name})')


# ── start ─────────────────────────────────────────────────────────────────────

@app.command('start')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ec2_start(ctx     : typer.Context,
              target  : str  = typer.Argument(...,    help='Instance ID or Name tag.'),
              yes     : bool = typer.Option(False, '--yes',     help='Skip confirmation.'),
              dry_run : bool = typer.Option(False, '--dry-run', help='Print action without executing.')):
    """Start a stopped EC2 instance (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if not confirm_or_abort(f'Start instance {target!r}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    iid = _resolve(ctx, target)
    ctx.obj['ec2_client'].start_instance(iid)
    console.print(f'[green]Started[/green] {iid}')


# ── stop ──────────────────────────────────────────────────────────────────────

@app.command('stop')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ec2_stop(ctx     : typer.Context,
             target  : str  = typer.Argument(...,    help='Instance ID or Name tag.'),
             yes     : bool = typer.Option(False, '--yes',     help='Skip confirmation.'),
             dry_run : bool = typer.Option(False, '--dry-run', help='Print action without executing.')):
    """Stop a running EC2 instance (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if not confirm_or_abort(f'Stop instance {target!r}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    iid = _resolve(ctx, target)
    ctx.obj['ec2_client'].stop_instance(iid)
    console.print(f'[green]Stopped[/green] {iid}')


# ── terminate ─────────────────────────────────────────────────────────────────

@app.command('terminate')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ec2_terminate(ctx     : typer.Context,
                  target  : str  = typer.Argument(...,    help='Instance ID or Name tag.'),
                  yes     : bool = typer.Option(False, '--yes',     help='Skip confirmation.'),
                  dry_run : bool = typer.Option(False, '--dry-run', help='Print action without executing.')):
    """Terminate an EC2 instance — irreversible (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    if not confirm_or_abort(f'Terminate {target!r}? This is IRREVERSIBLE.', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    iid = _resolve(ctx, target)
    ctx.obj['ec2_client'].terminate_instance(iid)
    console.print(f'[green]Terminating[/green] {iid}')


# ── wait ──────────────────────────────────────────────────────────────────────

@app.command('wait')
@spec_cli_errors
def ec2_wait(ctx     : typer.Context,
             target  : str = typer.Argument(..., help='Instance ID or Name tag.'),
             state   : str = typer.Option(...,   '--state', '-s',
                                                 help='Target state: running, stopped, terminated.'),
             timeout : int = typer.Option(300,   '--timeout', '-t',
                                                 help='Maximum seconds to wait (default: 300).')):
    """Block until an instance reaches the specified state."""
    iid = _resolve(ctx, target)
    try:
        target_state = Enum__EC2__Instance__State(state)
    except ValueError:
        console.print(f'[red]Unknown state:[/red] {state!r}. Use: running, stopped, terminated.')
        raise typer.Exit(1)
    client = ctx.obj['ec2_client']
    console.print(f'Waiting for {iid} → [bold]{state}[/bold] (up to {timeout}s) …')
    waiter = EC2__Instance__Wait(ec2_client=client)
    ok     = waiter.wait(iid, target_state, timeout=timeout)
    if ok:
        console.print(f'[green]State reached:[/green] {state}')
    else:
        console.print(f'[red]Timed out[/red] after {timeout}s — instance not yet in state {state!r}')
        raise typer.Exit(1)
