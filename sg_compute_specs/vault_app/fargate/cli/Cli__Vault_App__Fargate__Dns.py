# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate/cli — Cli__Vault_App__Fargate__Dns
# Typer sub-app for `sg vault-app fargate dns *` — DNS record lifecycle helpers
# that complement the start/stop commands.
#
# Sub-commands:
#   list   — show A records in the zone that look like vault-app slugs.
#            A record qualifies if its leftmost label matches the slug pattern
#            ^[a-z]+-[a-z]+(-\d+)?$ (covers Stack__Name__Generator output and
#            the legacy numeric-suffix form).  Each row is marked RUNNING or
#            orphan based on whether any running task has the slug as its
#            VaultApp__Slug tag.
#   prune  — delete orphan A records.  Mutation-gated.
#
# Zone resolution:
#   1. --zone flag wins outright.
#   2. Otherwise read the cluster tag VaultApp__DnsZone from the auto-resolved
#      cluster (cluster_resolver + tags_reader).
#   3. Raise typer.Exit(1) with a friendly error if neither is available.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import re

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sg_compute_specs.vault_app.fargate.service.Mutation__Gate__Scope                 import Mutation__Gate__Scope
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Cluster__Resolver import Vault_App__Fargate__Cluster__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader      import Vault_App__Fargate__Tags__Reader


_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'

_SLUG_RE = re.compile(r'^[a-z]+-[a-z]+(-\d+)?$')                                    # Stack__Name__Generator output, plus legacy numeric-suffix form

console = Console()

app = typer.Typer(name='dns', help='Vault-App DNS record lifecycle.',
                  no_args_is_help=True)


# ── client helpers ────────────────────────────────────────────────────────────

def _get_fargate_client(ctx: typer.Context):
    obj = ctx.obj or {}
    client = obj.get('fargate_client')
    if client is None:
        from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client
        client = Fargate__AWS__Client()
    return client


def _get_route53_client(ctx: typer.Context):
    obj = ctx.obj or {}
    client = obj.get('route53_client')
    if client is not None:
        return client
    try:
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client
        return Route53__AWS__Client()
    except Exception:                                                                # noqa: BLE001 — surface a friendlier error in the command
        return None


def _gate_check():                                                                   # mirrors the pattern in Cli__Vault_App__Fargate__Start
    if os.environ.get(_GATE_ENV) != '1':
        console.print(f'[red]{_GATE_ENV}[/red] must be set to 1 to allow this mutation.')
        raise typer.Exit(1)


# ── zone + slug resolution ────────────────────────────────────────────────────

def _resolve_zone(ctx: typer.Context, zone_flag: str) -> str:                       # --zone wins; else cluster tag VaultApp__DnsZone
    if zone_flag:
        return zone_flag
    fargate_client = _get_fargate_client(ctx)
    try:
        cluster_name = Vault_App__Fargate__Cluster__Resolver(
            fargate_client=fargate_client).resolve('')
    except ValueError:
        cluster_name = ''
    if not cluster_name:
        console.print('  [red]✗[/]  Cannot resolve zone: pass --zone or tag a cluster with VaultApp__DnsZone.')
        raise typer.Exit(1)
    cfg = Vault_App__Fargate__Tags__Reader(fargate_client=fargate_client).read(cluster_name)
    zone = str(cfg.dns_zone or '').strip()
    if not zone:
        console.print(f'  [red]✗[/]  Cluster {cluster_name!r} has no VaultApp__DnsZone tag; pass --zone explicitly.')
        raise typer.Exit(1)
    return zone


def _live_slugs(fargate_client) -> set:                                              # union of VaultApp__Slug tags across every running task in every cluster
    slugs = set()
    try:
        clusters = fargate_client.list_clusters()
    except Exception:                                                                # noqa: BLE001 — return empty set on failure so everything looks orphan
        clusters = []
    cluster_names = [str(c.cluster_name) for c in clusters] or ['']                  # '' triggers account-wide list_tasks fallback
    for cn in cluster_names:
        try:
            tasks = fargate_client.list_tasks(cluster=cn)
        except Exception:                                                            # noqa: BLE001
            continue
        for task in tasks:
            tags = task.tags or {}
            if isinstance(tags, list):
                tags = {t['key']: t['value'] for t in tags if 'key' in t}
            slug = tags.get('VaultApp__Slug', '')
            if slug:
                slugs.add(str(slug))
    return slugs


def _slug_from_record(record_name: str, zone: str) -> str:                           # leftmost label of an A record, normalised; empty if not under zone
    name   = str(record_name).rstrip('.')
    suffix = '.' + zone.rstrip('.')
    if not name.endswith(suffix):
        return ''
    return name[: -len(suffix)]


# ════════════════════════════════════════════════════════════════════════════════
# list
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def dns_list(ctx    : typer.Context,
             zone   : str  = typer.Option('',    '--zone',  help='Hosted zone name (auto-resolved from cluster tag if omitted).'),
             as_json: bool = typer.Option(False, '--json',  help='Machine-readable output.')):
    """List vault-app slug A records in the zone (RUNNING vs orphan)."""
    zone_name      = _resolve_zone(ctx, zone)
    fargate_client = _get_fargate_client(ctx)
    route53_client = _get_route53_client(ctx)
    if route53_client is None:
        console.print('  [red]✗[/]  No Route 53 client available.')
        raise typer.Exit(1)

    records   = route53_client.list_records(zone_name)
    live      = _live_slugs(fargate_client)
    rows      = []                                                                   # list of {slug, ip, ttl, status} dicts
    for record in records:
        if str(record.record_type) != 'A':
            continue
        slug = _slug_from_record(str(record.name), zone_name)
        if not slug or not _SLUG_RE.match(slug):
            continue
        ip     = ','.join(str(v) for v in record.values)
        status = 'RUNNING' if slug in live else 'orphan'
        rows.append({'slug': slug, 'ip': ip, 'ttl': int(record.ttl), 'status': status})

    if as_json:
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        console.print(f'[dim]No vault-app slug records found in zone {zone_name}[/dim]')
        return

    tbl = Table(title=f'Vault-app DNS records — {zone_name}', box=None,
                show_header=True, padding=(0, 2))
    tbl.add_column('Slug',   style='cyan')
    tbl.add_column('IP',     style='dim')
    tbl.add_column('TTL',    justify='right', style='dim')
    tbl.add_column('Status', style='green')
    for row in rows:
        style = 'green' if row['status'] == 'RUNNING' else 'red'
        tbl.add_row(row['slug'], row['ip'], str(row['ttl']),
                    f'[{style}]{row["status"]}[/{style}]')
    console.print()
    console.print(tbl)


# ════════════════════════════════════════════════════════════════════════════════
# prune
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def dns_prune(ctx    : typer.Context,
              zone   : str  = typer.Option('',    '--zone',     help='Hosted zone name (auto-resolved from cluster tag if omitted).'),
              yes    : bool = typer.Option(False, '--yes',      help='Skip confirmation prompt.'),
              dry_run: bool = typer.Option(False, '--dry-run',  help='List what would be deleted; make no changes.'),
              as_json: bool = typer.Option(False, '--json',     help='Machine-readable output.')):
    """Delete orphan vault-app A records (no matching running task)."""
    if not dry_run:
        _gate_check()

    zone_name      = _resolve_zone(ctx, zone)
    fargate_client = _get_fargate_client(ctx)
    route53_client = _get_route53_client(ctx)
    if route53_client is None:
        console.print('  [red]✗[/]  No Route 53 client available.')
        raise typer.Exit(1)

    records  = route53_client.list_records(zone_name)
    live     = _live_slugs(fargate_client)
    orphans  = []                                                                    # list of (slug, fqdn) tuples
    for record in records:
        if str(record.record_type) != 'A':
            continue
        slug = _slug_from_record(str(record.name), zone_name)
        if not slug or not _SLUG_RE.match(slug):
            continue
        if slug in live:
            continue
        orphans.append((slug, str(record.name).rstrip('.')))

    if not orphans:
        if as_json:
            typer.echo(json.dumps({'orphans': [], 'deleted': [], 'dry_run': dry_run}, indent=2))
            return
        console.print('[dim]No orphan records found.[/dim]')
        return

    if not yes and not as_json and not dry_run:
        listing = '\n  '.join(f'- {fqdn}' for _, fqdn in orphans)
        typer.confirm(
            f'Delete {len(orphans)} orphan DNS record(s)?\n  {listing}',
            default=False, abort=True,
        )

    from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
    deleted = []
    if not dry_run:
        with Mutation__Gate__Scope():
            for slug, fqdn in orphans:
                try:
                    route53_client.delete_record(
                        zone_id_or_name = zone_name,
                        name            = fqdn,
                        record_type     = Enum__Route53__Record_Type.A,
                    )
                    deleted.append({'slug': slug, 'fqdn': fqdn})
                except ValueError:                                                   # record already gone — treat as success
                    deleted.append({'slug': slug, 'fqdn': fqdn})

    if as_json:
        typer.echo(json.dumps({
            'orphans': [{'slug': s, 'fqdn': f} for s, f in orphans],
            'deleted': deleted,
            'dry_run': dry_run,
        }, indent=2))
        return

    if dry_run:
        console.print(f'[yellow]Would delete[/yellow] {len(orphans)} orphan record(s):')
        for _, fqdn in orphans:
            console.print(f'  - {fqdn}')
    else:
        console.print(f'[green]Deleted[/green] {len(deleted)} orphan record(s):')
        for row in deleted:
            console.print(f'  - {row["fqdn"]}')


# ── register sub-commands ─────────────────────────────────────────────────────

app.command('list' )(dns_list )
app.command('prune')(dns_prune)
