# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__EC2__Ami
# Typer CLI surface for `sg aws ec2 ami *` commands.
#
# Command tree:
#   sg aws ec2 ami list    [--owner self|amazon|all] [--name SUBSTR] [--json]
#   sg aws ec2 ami show    <ami-id-or-name>                          [--json]
#   sg aws ec2 ami orphans [--older 30d]                             [--json]
#   sg aws ec2 ami delete  <ami-id> [--with-snapshots] [--yes]       [--json]
#
# `delete` requires SG_AWS__EC2__ALLOW_MUTATIONS=1 (same gate as ec2 terminate).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import re
from datetime import datetime, timedelta, timezone

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate           import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client     import EC2__AWS__Client


_MUTATION_ENV = 'SG_AWS__EC2__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='ami', help='EC2 AMI inspection and orphan-detection.',
                  no_args_is_help=True)


# ── helpers ───────────────────────────────────────────────────────────────────

_TTL_RE = re.compile(r'^(\d+)\s*([smhd])$')                                      # 30d, 12h, 5m, 30s


def _parse_older(value: str) -> timedelta:                                       # Raises typer.BadParameter on bad input
    if not value:
        return timedelta(0)
    m = _TTL_RE.match(value.strip())
    if not m:
        raise typer.BadParameter(f"--older must be like '30d', '12h', '5m'; got {value!r}")
    n, unit = int(m.group(1)), m.group(2)
    if unit == 's': return timedelta(seconds=n)
    if unit == 'm': return timedelta(minutes=n)
    if unit == 'h': return timedelta(hours=n)
    return timedelta(days=n)


def _parse_created_at(s: str):                                                   # str → aware datetime or None
    if not s:
        return None
    try:
        # AWS CreationDate is like '2026-04-01T00:00:00.000Z'; isoformat handles
        # the offset form 2026-04-01T00:00:00+00:00 directly. Normalise trailing 'Z'.
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ec2_client', EC2__AWS__Client())


def _ami_to_dict(ami) -> dict:                                                   # JSON-safe view of Schema__EC2__AMI
    return dict(
        ami_id                = str(ami.ami_id),
        name                  = str(ami.name),
        description           = str(ami.description),
        owner_id              = str(ami.owner_id),
        created_at            = str(ami.created_at),
        public                = bool(ami.public),
        architecture          = str(ami.architecture),
        root_device_type      = str(ami.root_device_type),
        snapshot_ids          = [str(s) for s in ami.snapshot_ids],
        attached_instance_ids = [str(i) for i in ami.attached_instance_ids],
    )


def _render_ami_table(amis: list, title: str) -> None:
    if not amis:
        console.print('No AMIs found.')
        return
    t = Table(title=title)
    t.add_column('AMI ID',     style='cyan')
    t.add_column('Name',       style='green')
    t.add_column('Created',    style='dim')
    t.add_column('Snapshots',  style='dim', justify='right')
    for ami in amis:
        t.add_row(str(ami.ami_id),
                  str(ami.name) or '—',
                  str(ami.created_at) or '—',
                  str(len(ami.snapshot_ids)))
    console.print(t)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command('list')
@spec_cli_errors
def ami_list(ctx     : typer.Context,
             owner   : str  = typer.Option('self', '--owner',
                                            help='Owner filter: self, amazon, all.'),
             name    : str  = typer.Option('',     '--name',
                                            help='Server-side name substring filter.'),
             as_json : bool = typer.Option(False,  '--json', help='Output as JSON.')):
    """List AMIs visible in the current account / region."""
    client = ctx.obj['ec2_client']
    amis   = client.list_amis(owner=owner, name_substring=name)
    if as_json:
        typer.echo(json.dumps([_ami_to_dict(a) for a in amis], indent=2))
        return
    _render_ami_table(list(amis), title=f'AMIs (owner={owner})')


# ── show ──────────────────────────────────────────────────────────────────────

@app.command('show')
@spec_cli_errors
def ami_show(ctx          : typer.Context,
             ami_id_or_name: str  = typer.Argument(..., help='AMI ID (ami-*) or AMI name.'),
             as_json      : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show full detail for one AMI plus any instances currently using it."""
    client = ctx.obj['ec2_client']
    ami    = client.describe_ami(ami_id_or_name)
    if ami is None:
        console.print(f'[red]AMI not found:[/red] {ami_id_or_name}')
        raise typer.Exit(1)
    # ── populate attached_instance_ids ────────────────────────────────────────
    instances = client.list_instances(state='all')
    attached  = []
    for inst in instances:
        if str(inst.ami_id) == str(ami.ami_id):
            attached.append(str(inst.instance_id))
    ami.attached_instance_ids = attached
    if as_json:
        typer.echo(json.dumps(_ami_to_dict(ami), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('ami id',          str(ami.ami_id)),
        ('name',            str(ami.name)             or '—'),
        ('description',     str(ami.description)      or '—'),
        ('owner',           str(ami.owner_id)         or '—'),
        ('created',         str(ami.created_at)       or '—'),
        ('public',          'yes' if ami.public else 'no'),
        ('architecture',    str(ami.architecture)     or '—'),
        ('root device',     str(ami.root_device_type) or '—'),
        ('snapshot ids',    ', '.join(str(s) for s in ami.snapshot_ids) or '(none)'),
        ('attached to',     ', '.join(attached) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── orphans ───────────────────────────────────────────────────────────────────

@app.command('orphans')
@spec_cli_errors
def ami_orphans(ctx     : typer.Context,
                older   : str  = typer.Option('', '--older',
                                               help='Only orphans created before TTL (e.g. 30d).'),
                as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List self-owned AMIs not referenced by any instance (running, stopped, or recent)."""
    client    = ctx.obj['ec2_client']
    amis      = client.list_amis(owner='self')
    instances = client.list_instances(state='all')
    in_use    = {str(i.ami_id) for i in instances if str(i.ami_id)}
    orphans   = [a for a in amis if str(a.ami_id) not in in_use]
    # ── --older filter (AMIs with empty/unparseable created_at are NEVER orphans) ──
    if older:
        delta  = _parse_older(older)
        cutoff = datetime.now(timezone.utc) - delta
        kept   = []
        for ami in orphans:
            created_dt = _parse_created_at(str(ami.created_at))
            if created_dt is None:                                              # safety: skip undated AMIs
                continue
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            if created_dt <= cutoff:
                kept.append(ami)
        orphans = kept
    else:
        # Even without --older, skip AMIs with no parseable created_at (safety).
        orphans = [a for a in orphans if _parse_created_at(str(a.created_at)) is not None]
    # attached_instance_ids = [] for orphans (they have none by definition).
    for ami in orphans:
        ami.attached_instance_ids = []
    if as_json:
        typer.echo(json.dumps([_ami_to_dict(a) for a in orphans], indent=2))
        return
    _render_ami_table(orphans, title='Orphan AMIs (self-owned, no attached instances)')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ami_delete(ctx            : typer.Context,
               ami_id         : str  = typer.Argument(..., help='AMI ID (ami-*) or AMI name.'),
               with_snapshots : bool = typer.Option(False, '--with-snapshots',
                                                    help='Also delete backing snapshots.'),
               yes            : bool = typer.Option(False, '--yes',
                                                    help='Skip confirmation prompt.'),
               as_json        : bool = typer.Option(False, '--json',
                                                    help='Output as JSON.')):
    """Deregister an AMI (requires SG_AWS__EC2__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ec2_client']
    # ── pre-flight: resolve so we know the snapshot list BEFORE deregister ──
    ami = client.describe_ami(ami_id)
    if ami is None:
        if as_json:
            typer.echo(json.dumps({'ami_id'      : ami_id,
                                   'deregistered': False,
                                   'error'       : 'not_found',
                                   'snapshots'   : []}, indent=2))
        else:
            console.print(f'[red]AMI not found:[/red] {ami_id}')
        raise typer.Exit(1)
    resolved_id     = str(ami.ami_id)
    snapshot_ids    = [str(s) for s in ami.snapshot_ids]
    # ── summary table ───────────────────────────────────────────────────────
    if not as_json:
        t = Table(box=None, show_header=False, padding=(0, 2))
        t.add_column(style='bold', min_width=22)
        t.add_column()
        t.add_row('ami id',         resolved_id)
        t.add_row('name',           str(ami.name)     or '—')
        t.add_row('owner',          str(ami.owner_id) or '—')
        t.add_row('snapshot count', str(len(snapshot_ids)))
        console.print()
        console.print(t)
        console.print()
    # ── confirm ─────────────────────────────────────────────────────────────
    if with_snapshots:
        prompt = 'Deregister AMI? (snapshots will be deleted)'
    else:
        prompt = 'Deregister AMI? (snapshots will remain — delete separately.)'
    if not yes and not typer.confirm(prompt, default=False):
        if as_json:
            typer.echo(json.dumps({'ami_id'      : resolved_id,
                                   'deregistered': False,
                                   'aborted'     : True,
                                   'snapshots'   : []}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    # ── deregister ──────────────────────────────────────────────────────────
    deregistered = client.deregister_image(resolved_id)
    # ── snapshots ───────────────────────────────────────────────────────────
    snap_results = []
    if with_snapshots and deregistered:
        for snap_id in snapshot_ids:
            try:
                ok = client.delete_snapshot(snap_id)
                snap_results.append({'id': snap_id, 'deleted': bool(ok),
                                     'error': None})
            except Exception as exc:                                            # noqa: BLE001 — surface AWS / boto3 reason verbatim
                snap_results.append({'id': snap_id, 'deleted': False,
                                     'error': str(exc)})
    # ── output ──────────────────────────────────────────────────────────────
    if as_json:
        typer.echo(json.dumps({'ami_id'      : resolved_id,
                               'deregistered': bool(deregistered),
                               'snapshots'   : snap_results}, indent=2))
        return
    if deregistered:
        console.print(f'[green]Deregistered[/green] {resolved_id}')
    else:
        console.print(f'[yellow]Not deregistered[/yellow] {resolved_id} (already gone?)')
    if with_snapshots:
        for res in snap_results:
            if res['deleted']:
                console.print(f'  [green]Deleted snapshot[/green] {res["id"]}')
            else:
                err = res['error'] or 'not deleted'
                console.print(f'  [red]Snapshot {res["id"]} failed:[/red] {err}')
