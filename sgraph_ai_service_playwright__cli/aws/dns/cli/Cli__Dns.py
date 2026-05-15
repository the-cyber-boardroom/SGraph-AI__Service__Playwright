# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Dns
# Typer CLI surface for Route 53 DNS management. Sub-groups: zones, records,
# instance. All commands delegate to service classes — no boto3 here.
#
# Command tree:
#   sg aws dns zones list                         — list all hosted zones
#   sg aws dns zones show [<zone>]                — details of one zone
#   sg aws dns records list [<zone>]              — list records in a zone
#   sg aws dns records get <name>                 — show one record
#   sg aws dns records add <name> --value <ip>    — create a record (P1)
#   sg aws dns records update <name> --value <ip> — upsert a record (P1)
#   sg aws dns records delete <name>              — delete a record (P1)
#   sg aws dns records check <name>               — verify a record (P1)
#   sg aws dns instance create-record [<inst>]    — create A from EC2 IP (P1)
#
# Flags: --json on every command; --zone / --type on records commands.
# Mutations require SG_AWS__DNS__ALLOW_MUTATIONS=1 env var.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys

import typer
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

from sg_compute.cli.base.Spec__CLI__Errors                                       import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Resolver                 import Enum__Dns__Resolver
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type          import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                       import Dig__Runner
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Authoritative__Checker   import Route53__Authoritative__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client              import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Check__Orchestrator      import Route53__Check__Orchestrator
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Instance__Linker         import Route53__Instance__Linker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Local__Checker           import Route53__Local__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Public_Resolver__Checker import Route53__Public_Resolver__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Smart_Verify             import Route53__Smart_Verify
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Zone__Resolver           import Route53__Zone__Resolver

# ── Warning banners for cache-polluting check modes (P1.5) ────────────────────

_WARNING__PUBLIC_RESOLVERS = """WARNING: --public-resolvers will cache the answer at each of the 8 public
resolvers below for up to this record's TTL. If you change this record
again, those resolvers will return the OLD value until that TTL elapses,
and there is NO way to flush a third-party recursive cache. Only run
--public-resolvers once you are confident the value is final. Use the
default --authoritative mode for iterative verification."""

_WARNING__LOCAL = """WARNING: --local will shell out to `dig` on this host. That query goes
through whatever upstream resolver this machine is configured to use
(often a corporate proxy or VPN resolver), and that resolver WILL cache
the answer for up to the record's TTL. If you change this record again,
this host (and anyone else behind the same upstream) will see the OLD
value until that TTL elapses. There is no portable way to flush a
third-party upstream cache; flush your local OS cache with platform-native
tooling if needed. Use the default --authoritative mode for iterative
verification."""

_WARNING__ALL = """WARNING: --all enables BOTH cache-polluting modes (--public-resolvers
and --local) in addition to the safe --authoritative check. The 8 public
resolvers AND your host's upstream resolver will each cache the answer
for up to the record's TTL. If you change this record again afterwards,
those caches will return the OLD value until that TTL elapses, and
there is NO way to flush a third-party recursive cache. Only run --all
once you are confident the value is final. Prefer the default
--authoritative mode for iterative verification."""

# ── Typer sub-apps ────────────────────────────────────────────────────────────

dns_app      = typer.Typer(name='dns',      help='Route 53 DNS management.', no_args_is_help=True)
zones_app    = typer.Typer(name='zones',    help='Hosted-zone account-wide listing.', no_args_is_help=True)
zone_app     = typer.Typer(name='zone',     help='Operations on one hosted zone (defaults to sg-compute.sgraph.ai).', no_args_is_help=True)
records_app  = typer.Typer(name='records',  help='Per-record mutations + propagation check.', no_args_is_help=True)
instance_app = typer.Typer(name='instance', help='EC2-instance DNS helpers.', no_args_is_help=True)

dns_app.add_typer(zones_app,    name='zones'   )                                     # `zones` (plural) — listing all hosted zones in the account
dns_app.add_typer(zone_app,     name='zone'    )                                     # `zone` (singular) — list/show/check records inside one zone
dns_app.add_typer(zone_app,     name='z',        hidden=True)                        # `z` short alias maps to the more common per-zone ops
dns_app.add_typer(records_app,  name='records' )
dns_app.add_typer(records_app,  name='r',        hidden=True)
dns_app.add_typer(instance_app, name='instance')
dns_app.add_typer(instance_app, name='i',        hidden=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client() -> Route53__AWS__Client:
    return Route53__AWS__Client()


def _resolve_zone_id(client: Route53__AWS__Client, zone: str) -> str:               # Resolve an explicit zone arg or fall back to sgraph.ai
    if zone:
        return client.resolve_zone_id(zone)
    return str(client.resolve_default_zone().zone_id)


def _resolve_zone_id_for_record(client: Route53__AWS__Client, zone: str, name: str) -> str:  # FQDN-aware zone resolution for record commands. With explicit --zone: use it. Without: walk labels via Route53__Zone__Resolver to find the deepest owning hosted zone (handles sub-delegations like sg-compute.sgraph.ai). Falls back to the default zone (sgraph.ai) only when the resolver finds no match.
    if zone:
        return client.resolve_zone_id(zone)
    if '.' in name.rstrip('.'):                                                      # Multi-label FQDN — try deepest-zone resolution
        try:
            owning = Route53__Zone__Resolver(r53_client=client).resolve_zone_for_fqdn(name)
            return str(owning.zone_id)
        except ValueError:                                                            # No zone in the account owns this fqdn — fall back to default
            pass
    return str(client.resolve_default_zone().zone_id)


def _zone_label(zone_schema) -> str:                                                 # Human-readable label for a zone in table headers
    return f'{zone_schema.name}.  ·  {zone_schema.zone_id}'


def _assert_mutations_allowed():                                                     # Guard: require SG_AWS__DNS__ALLOW_MUTATIONS=1 for all record mutations
    if os.environ.get('SG_AWS__DNS__ALLOW_MUTATIONS') != '1':
        typer.echo('Error: SG_AWS__DNS__ALLOW_MUTATIONS=1 must be set to run DNS mutations.', err=True)
        typer.echo('Set the env var only in controlled sessions — never in CI pipelines unless intentional.', err=True)
        raise typer.Exit(1)


def _wait_for_change(c: Console, client: Route53__AWS__Client, change_id: str,
                      timeout: int, quiet: bool = False, poll_interval: int = 2):    # Poll Route 53 GetChange until INSYNC or timeout; updates a single inline status line
    if not quiet:
        c.print(f'  ⏳ Waiting for Route 53 INSYNC (timeout {timeout}s)…')
    def _on_poll(result, elapsed):
        if quiet:
            return
        sys.stdout.write(f'\r    {result.status} ({elapsed}s)        ')               # \r overwrites the previous status; trailing spaces clear any leftover characters
        sys.stdout.flush()
    final = client.wait_for_change(change_id, timeout=timeout,
                                    poll_interval=poll_interval, on_poll=_on_poll)
    if not quiet:
        sys.stdout.write('\n')                                                        # Finish the inline progress line before any subsequent print
        sys.stdout.flush()
        if final.status == 'INSYNC':
            c.print('  ✓ Route 53 INSYNC — change is live on all zone NS.\n')
    return final


def _fmt_seconds(secs: float) -> str:                                                # Compact human-friendly formatter for the timings table
    if secs < 1.0:
        return f'{secs * 1000:.0f}ms'
    if secs < 60:
        return f'{secs:.2f}s'
    minutes = int(secs // 60)
    rest    = secs - minutes * 60
    return f'{minutes}m {rest:.0f}s'


def _print_timings(c: Console, phases: list, total_seconds: float):                  # Renders a small "Timings" block at the end of records add
    if not phases:
        return
    c.print()
    c.print('  [dim]Timings[/]')
    for label, secs in phases:
        c.print(f'    [dim]{label:38s}[/] {_fmt_seconds(secs)}', highlight=False)
    c.print(f'    [bold]{"Total":38s} {_fmt_seconds(total_seconds)}[/]', highlight=False)
    c.print()


def _timings_to_dict(phases: list, total_seconds: float) -> dict:                    # Same data, JSON-friendly (seconds, 3-decimal precision)
    out = {label: round(secs, 3) for label, secs in phases}
    out['total'] = round(total_seconds, 3)
    return out


def _make_orchestrator(r53_client: Route53__AWS__Client) -> Route53__Check__Orchestrator:
    dig    = Dig__Runner()
    auth   = Route53__Authoritative__Checker  (dig_runner=dig, r53_client=r53_client)
    pub    = Route53__Public_Resolver__Checker(dig_runner=dig)
    local  = Route53__Local__Checker          (dig_runner=dig)
    return Route53__Check__Orchestrator(authoritative_checker   = auth ,
                                        public_resolver_checker = pub  ,
                                        local_checker           = local)


def _make_smart_verify(r53_client: Route53__AWS__Client) -> Route53__Smart_Verify:
    orch = _make_orchestrator(r53_client)
    return Route53__Smart_Verify(r53_client=r53_client, orchestrator=orch)


def _print_auth_check(c: Console, result):                                           # Print the authoritative-check table in the spec format
    c.print()
    c.print(f'  Authoritative check — {result.name} ({result.rtype})')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Nameserver',  style='cyan', min_width=30, no_wrap=True)
    t.add_column('Value',       style='',     min_width=15)
    t.add_column('Match',       style='',     min_width=5)
    for dig_res in result.results:
        val_str   = '  '.join(dig_res.values) if dig_res.values else '(no answer)'
        expected  = result.expected
        if expected:
            match_str = '✓' if expected in dig_res.values else '✗'
        else:
            match_str = '✓' if dig_res.values else '✗'
        t.add_row(dig_res.nameserver, val_str, match_str)
    c.print(t)
    c.print()
    status = '✓' if result.passed else '✗'
    c.print(f'  {result.agreed_count}/{result.total_count} authoritative nameservers agree. {status}')
    c.print()


def _resolver_name_for_ip(ip: str) -> str:                                           # Map a resolver IP back to its Enum member name; '' if unknown
    for member in Enum__Dns__Resolver:
        if member.value == ip:
            return member.name
    return ip


def _print_public_resolvers_check(c: Console, result, min_resolvers: int):          # Print the public-resolvers fan-out table in spec format
    c.print()
    c.print(f'  Public-resolver check — {result.name} ({result.rtype})')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Resolver',  style='cyan', min_width=14, no_wrap=True)
    t.add_column('IP',        style='dim' , min_width=16, no_wrap=True)
    t.add_column('Value',     style=''    , min_width=15)
    t.add_column('Match',     style=''    , min_width=5)
    for dig_res in result.results:
        val_str   = '  '.join(dig_res.values) if dig_res.values else '(no answer)'
        if result.expected:
            match_str = '✓' if result.expected in dig_res.values else '✗'
        else:
            match_str = '✓' if dig_res.values else '✗'
        t.add_row(_resolver_name_for_ip(dig_res.nameserver), dig_res.nameserver,
                  val_str, match_str)
    c.print(t)
    c.print()
    if result.passed:
        c.print(f'  {result.agreed_count}/{result.total_count} resolvers agree. ✓')
    else:
        c.print(f'  Quorum: {min_resolvers}/{result.total_count} needed, '
                f'{result.agreed_count} agreed. ✗')
    c.print()


def _print_local_check(c: Console, result):                                          # Print the single-row local-resolver check table
    c.print()
    c.print(f'  Local-resolver check — {result.name} ({result.rtype})')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Resolver',  style='cyan', min_width=20, no_wrap=True)
    t.add_column('Value',     style=''    , min_width=15)
    t.add_column('Match',     style=''    , min_width=5)
    for dig_res in result.results:
        val_str   = '  '.join(dig_res.values) if dig_res.values else '(no answer)'
        if result.expected:
            match_str = '✓' if result.expected in dig_res.values else '✗'
        else:
            match_str = '✓' if dig_res.values else '✗'
        t.add_row('(host default)', val_str, match_str)
    c.print(t)
    c.print()
    if result.passed:
        c.print('  Local resolver agrees. ✓')
    else:
        c.print('  Local resolver mismatch. ✗')
    c.print()


def _result_to_dict(result) -> dict:                                                 # Serialise Schema__Dns__Check__Result to a JSON-safe dict
    return dict(mode         = str(result.mode)  ,
                name         = result.name       ,
                rtype        = result.rtype      ,
                expected     = result.expected   ,
                passed       = result.passed     ,
                agreed_count = result.agreed_count,
                total_count  = result.total_count )


_CERT_WARNING = """\
⚠ HTTPS cert
This DNS name is now usable, but HTTPS clients will see a certificate
warning until a cert is issued for `{fqdn}`. Today, the
vault-app / playwright stacks ship Let's Encrypt IP-anchored certs
(valid for the EC2 public IP, not the DNS name).

Options to fix:
  (a) `sg playwright vault re-cert --hostname {fqdn}`
      — uses our own cert sidecar workflow. Fast. No AWS account
      pollution. ⚠ PROPOSED — see brief §addendum-cert. NOT IN P1.
  (b) `sg aws acm request --domain {fqdn}` — issues an
      ACM cert. Useful only if you are terminating TLS on CloudFront /
      ELB. ⚠ Adds an entry to ACM that does NOT auto-delete when the
      stack is destroyed. PROPOSED — NOT IN P1.

For now, accept the cert warning or use the IP-based vault_url
surfaced by `sp pw v info`."""


# ── zones list (cross-zone — all hosted zones in the account) ────────────────

@zones_app.command('list')
@spec_cli_errors
def zones_list(json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List all hosted zones in the account."""
    client = _client()
    zones  = client.list_hosted_zones()
    if json_output:
        typer.echo(json.dumps([dict(name             = str(z.name)        ,
                                    zone_id          = str(z.zone_id)     ,
                                    private_zone     = z.private_zone     ,
                                    record_count     = z.record_count     ,
                                    comment          = z.comment          ,
                                    caller_reference = z.caller_reference )
                                for z in zones], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  Hosted zones in account  ·  {len(zones)} zones')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Name',     style='bold',    min_width=22, no_wrap=True)             # Name first — most distinguishing column
    t.add_column('Zone Id',  style='cyan',    min_width=22, no_wrap=True)
    t.add_column('Type',     style='',        min_width=7)
    t.add_column('Records',  style='',        min_width=7)
    t.add_column('Comment',  style='dim',     min_width=10)
    for z in zones:
        zone_type = 'private' if z.private_zone else 'public'
        t.add_row(str(z.name) + '.', str(z.zone_id), zone_type,
                  str(z.record_count), str(z.comment))
    c.print(t)
    c.print()


# ── zone show (per-zone — metadata) ───────────────────────────────────────────

@zone_app.command('show')
@spec_cli_errors
def zone_show(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sg-compute.sgraph.ai.'),
              json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """Show metadata for one hosted zone."""
    client    = _client()
    zone_obj  = client.get_hosted_zone(zone) if zone else client.resolve_default_zone()
    if json_output:
        typer.echo(json.dumps(dict(name             = str(zone_obj.name)        ,
                                   zone_id          = str(zone_obj.zone_id)     ,
                                   private_zone     = zone_obj.private_zone     ,
                                   record_count     = zone_obj.record_count     ,
                                   comment          = zone_obj.comment          ,
                                   caller_reference = zone_obj.caller_reference ), indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(Panel(f'[bold]{zone_obj.name}.[/]  [dim]{zone_obj.zone_id}[/]', expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18, no_wrap=True)
    t.add_column()
    zone_type = 'private' if zone_obj.private_zone else 'public'
    t.add_row('type',             zone_type)
    t.add_row('record-count',     str(zone_obj.record_count))
    t.add_row('comment',          zone_obj.comment or '(none)')
    t.add_row('caller-reference', zone_obj.caller_reference)
    c.print(t)
    c.print()


# ── zone list (per-zone — records in the zone) ────────────────────────────────

def _records_list_impl(zone: str, json_output: bool):                                # Shared body for `zone list` AND the legacy `records list` alias
    client  = _client()
    zone_id = _resolve_zone_id(client, zone)
    records = client.list_records(zone_id)
    if json_output:
        typer.echo(json.dumps([dict(name          = str(r.name)          ,
                                    type          = str(r.record_type)   ,
                                    ttl           = r.ttl                ,
                                    values        = r.values             ,
                                    alias_target  = r.alias_target       ,
                                    set_identifier= r.set_identifier     )
                                for r in records], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  Records in zone  ·  {zone_id}  ·  {len(records)} records')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Name',        style='bold', min_width=30)
    t.add_column('Type',        style='cyan', min_width=5)
    t.add_column('TTL',         style='',     min_width=6)
    t.add_column('Value(s)',    style='',     min_width=20)
    t.add_column('Alias/Set-ID',style='dim',  min_width=10)
    for r in records:
        values_str    = '  '.join(r.values) if r.values else ''
        alias_set_str = r.alias_target or r.set_identifier or ''
        ttl_str       = str(r.ttl) if r.ttl else '—'
        t.add_row(str(r.name), str(r.record_type), ttl_str, values_str, alias_set_str)
    c.print(t)
    c.print()


@zone_app.command('list')
@spec_cli_errors
def zone_list(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sg-compute.sgraph.ai.'),
              json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List all records in a hosted zone."""
    _records_list_impl(zone, json_output)


@records_app.command('list', hidden=True)                                            # Backward-compat alias — `records list` was the original location of this command
@spec_cli_errors
def records_list_legacy(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sg-compute.sgraph.ai.'),
                        json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """[deprecated alias] Use `sg aws dns zone list` instead."""
    _records_list_impl(zone, json_output)


# ── zone check (per-zone — health-check all records) ─────────────────────────

@zone_app.command('check')
@spec_cli_errors
def zone_check(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sg-compute.sgraph.ai.'),
               json_output: bool = typer.Option(False, '--json', help='Emit JSON instead of a table.')):
    """Health-check all A records in the zone. Flags orphaned / stale entries — candidates for delete."""
    import time
    t_start = time.perf_counter()

    client  = _client()
    zone_id = _resolve_zone_id(client, zone)
    records = client.list_records(zone_id)

    # Build a Name-tag → instance map once. We match the record's leftmost label against
    # the EC2 Name tag (the stack name), which is the convention used by every sg_compute
    # spec and the legacy stack helpers. Records that don't follow that convention land
    # in UNMATCHED — the operator decides whether they're intentional or leftover.
    linker = Route53__Instance__Linker()
    ec2    = linker.ec2_client()
    resp   = ec2.describe_instances(Filters=[{'Name': 'instance-state-name',
                                              'Values': ['running']}])
    instances_by_name = {}                                                            # name_tag → (instance_id, public_ip)
    for r in resp.get('Reservations', []):
        for inst in r.get('Instances', []):
            tag_name = ''
            for tag in inst.get('Tags', []):
                if tag.get('Key') == 'Name':
                    tag_name = tag.get('Value', '')
                    break
            if tag_name:
                instances_by_name[tag_name] = (inst.get('InstanceId', ''),
                                                inst.get('PublicIpAddress', ''))

    zone_name = ''
    try:
        zone_obj  = client.get_hosted_zone(zone) if zone else client.resolve_default_zone()
        zone_name = str(zone_obj.name).rstrip('.')
    except Exception:
        zone_name = '?'

    results = []                                                                      # list of dicts; one per record
    for r in records:
        rtype = str(r.record_type)
        name  = str(r.name).rstrip('.')
        leaf  = name[:-len(zone_name) - 1] if (zone_name and name.endswith(zone_name) and name != zone_name) else ''
        record_value = ', '.join(r.values) if r.values else ''
        status   = 'IGNORED'                                                          # default for SOA/NS/CNAME/zone-apex
        inst_id  = ''
        inst_ip  = ''
        note     = ''
        if rtype in ('SOA', 'NS'):
            status = 'IGNORED'
            note   = 'zone-system record'
        elif rtype != 'A':
            status = 'IGNORED'
            note   = f'{rtype} — not checked'
        elif not leaf:
            status = 'IGNORED'
            note   = 'apex record'
        elif '.' in leaf:                                                             # Multi-label leaf — could be intentional (api.staging.<zone>) but won't match a single-label Name tag
            status = 'UNMATCHED'
            note   = 'multi-label leaf — manual review'
        elif leaf in instances_by_name:
            inst_id, inst_ip = instances_by_name[leaf]
            record_ip = r.values[0] if r.values else ''
            if record_ip == inst_ip:
                status = 'OK'
            else:
                status = 'STALE'
                note   = f'instance public-ip is {inst_ip}'
        else:
            status = 'ORPHANED'
            note   = 'no running instance with this Name tag'
        results.append(dict(name        = name        ,
                            record_type = rtype       ,
                            record_value= record_value,
                            instance_id = inst_id     ,
                            instance_ip = inst_ip     ,
                            status      = status      ,
                            note        = note        ))

    purge_candidates = [r for r in results if r['status'] in ('ORPHANED', 'STALE')]
    elapsed_s        = time.perf_counter() - t_start

    if json_output:
        typer.echo(json.dumps(dict(zone             = zone_name                  ,
                                   zone_id          = zone_id                    ,
                                   record_count     = len(results)               ,
                                   purge_candidates = len(purge_candidates)      ,
                                   elapsed_seconds  = round(elapsed_s, 3)        ,
                                   results          = results                    ), indent=2))
        return

    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1

    c = Console(highlight=False)
    c.print()
    summary = '  '.join(f'{n} {s}' for s, n in counts.items())
    c.print(f'  Zone health — {zone_name}  ·  {len(results)} records  ·  {summary}')
    c.print()

    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Name',         style='bold', min_width=30, no_wrap=True)
    t.add_column('Type',         style='cyan', min_width=5)
    t.add_column('Record value', style='',     min_width=18)
    t.add_column('Instance IP',  style='dim',  min_width=15)
    t.add_column('Status',       style='',     min_width=10)
    t.add_column('Note',         style='dim',  min_width=10)
    status_style = {'OK': '[green]OK[/]', 'STALE': '[yellow]STALE[/]',
                    'ORPHANED': '[red]ORPHANED[/]', 'UNMATCHED': '[blue]UNMATCHED[/]',
                    'IGNORED': '[dim]IGNORED[/]'}
    for r in results:
        t.add_row(r['name'], r['record_type'], r['record_value'],
                  r['instance_ip'] or '—', status_style.get(r['status'], r['status']),
                  r['note'])
    c.print(t)
    c.print()
    if purge_candidates:
        c.print(f'  [yellow]Purge candidates:[/] {len(purge_candidates)} records ([red]ORPHANED[/] or [yellow]STALE[/]).')
        c.print(f'  Delete one with: [bold]sg aws dns records delete <name> --type A[/]')
        c.print()
    else:
        c.print(f'  [green]No purge candidates — every checked A record matches a running instance.[/]\n')


# ── records get ───────────────────────────────────────────────────────────────

@records_app.command('get')
@spec_cli_errors
def records_get(name       : str  = typer.Argument(..., help='Record name (e.g. www.sgraph.ai).'),
                zone       : str  = typer.Option(None,  '--zone', '-z', help='Zone name or id. Defaults to sgraph.ai.'),
                rtype      : str  = typer.Option('A',   '--type', '-t', help='Record type (A, CNAME, MX, …).'),
                json_output: bool = typer.Option(False, '--json',       help='Output JSON instead of a table.')):
    """Show one record from a hosted zone."""
    client  = _client()
    zone_id = _resolve_zone_id_for_record(client, zone, name)
    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)
    record = client.get_record(zone_id, name, record_type)
    if record is None:
        typer.echo(f'No {rtype} record found for {name!r} in zone {zone_id}', err=True)
        raise typer.Exit(1)
    if json_output:
        typer.echo(json.dumps(dict(name          = str(record.name)        ,
                                   type          = str(record.record_type) ,
                                   ttl           = record.ttl              ,
                                   values        = record.values           ,
                                   alias_target  = record.alias_target     ,
                                   set_identifier= record.set_identifier   ), indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Name',        style='bold', min_width=30)
    t.add_column('Type',        style='cyan', min_width=5)
    t.add_column('TTL',         style='',     min_width=6)
    t.add_column('Value(s)',    style='',     min_width=20)
    t.add_column('Alias/Set-ID',style='dim',  min_width=10)
    values_str    = '  '.join(record.values) if record.values else ''
    alias_set_str = record.alias_target or record.set_identifier or ''
    ttl_str       = str(record.ttl) if record.ttl else '—'
    t.add_row(str(record.name), str(record.record_type), ttl_str, values_str, alias_set_str)
    c.print(t)
    c.print()


# ── records add ───────────────────────────────────────────────────────────────

def _looks_like_fqdn(arg: str) -> bool:                                              # An FQDN has at least one dot inside it (label.zone)
    return '.' in arg.rstrip('.')


def _looks_like_instance_ref(arg: str) -> bool:                                      # i-... = AWS instance-id; otherwise a stack-name / Name tag
    return arg.startswith('i-') or not _looks_like_fqdn(arg)


@records_app.command('add')
@spec_cli_errors
def records_add(arg1         : str  = typer.Argument(None,  help='FQDN (e.g. test-2.sg-compute.sgraph.ai) OR instance ref (i-... / stack-name). Omit to use latest running instance + derived name.'),
                arg2         : str  = typer.Argument(None,  help='FQDN — when arg1 is an instance ref. Omit to derive `<stack-name>.<default-zone>`.'),
                value        : str  = typer.Option(None,  '--value', '-v', help='Explicit record value (skips instance auto-resolution). Required for non-A record types.'),
                rtype        : str  = typer.Option('A',   '--type',  '-t', help='Record type.'),
                ttl          : int  = typer.Option(60,    '--ttl',         help='TTL in seconds.'),
                zone         : str  = typer.Option(None,  '--zone',  '-z', help='Zone name or id. Default: $SG_AWS__DNS__DEFAULT_ZONE or sg-compute.sgraph.ai.'),
                yes          : bool = typer.Option(False, '--yes',         help='Skip confirmation prompt.'),
                no_verify    : bool = typer.Option(False, '--no-verify',   help='Skip post-mutation DNS verify.'),
                wait         : bool = typer.Option(False, '--wait',        help='Poll Route 53 until the change is INSYNC (suitable for chaining cert issuance).'),
                wait_timeout : int  = typer.Option(120,   '--wait-timeout',help='Max seconds to wait for INSYNC.'),
                force        : bool = typer.Option(False, '--force',      help='Upsert when the record already exists (otherwise fail).'),
                json_output  : bool = typer.Option(False, '--json',        help='Emit change result as JSON.')):
    """Create a DNS record.

    Forms:
      sg aws dns records add                                           # latest running instance + derived <stack>.<default-zone>
      sg aws dns records add <fqdn>                                    # latest running instance, given FQDN
      sg aws dns records add <i-id|stack-name>                         # that instance, derived <stack>.<default-zone>
      sg aws dns records add <i-id|stack-name> <fqdn>                  # that instance, given FQDN
      sg aws dns records add <fqdn> --value <ip>                       # explicit value (no instance lookup)

    Env: no env gate — `add` is additive and ephemeral. Confirmation prompt protects against typos
    (use `--yes` to skip). `update` and `delete` still require SG_AWS__DNS__ALLOW_MUTATIONS=1.
    """
    import time
    overall_t0   = time.perf_counter()
    timings      = []                                                                # list of (label, seconds) — printed at the end / included in --json
    def _record(label, t0):
        timings.append((label, time.perf_counter() - t0))

    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)

    # ── Dispatch the positional / --value combinations ──────────────────────
    instance_ref      = None                                                          # If set, resolve via Route53__Instance__Linker for the IP
    fqdn              = None                                                          # The record name to create — derived later if still None
    instance_resolved = False                                                          # Tracks whether the IP came from an instance lookup (controls cert-warning + auto-upsert)

    if arg1 and _looks_like_instance_ref(arg1) and value:                             # Instance ref + --value: --value is the FQDN/leaf-name, NOT a record value (instance provides the IP)
        if arg2:
            typer.echo('When the first positional is an instance ref, do not combine --value with a second positional FQDN. Pick one.', err=True)
            raise typer.Exit(1)
        instance_ref = arg1
        fqdn         = value
        value        = None                                                            # Force instance-IP auto-resolution downstream
    elif value:                                                                       # Explicit-value path — arg1 must be the FQDN, arg2 must be absent
        if not arg1:
            typer.echo('When --value is given, the first positional argument must be the FQDN.', err=True)
            raise typer.Exit(1)
        if arg2:
            typer.echo('When --value is given, only one positional argument is accepted (the FQDN).', err=True)
            raise typer.Exit(1)
        fqdn = arg1
    elif arg2:                                                                        # Two positionals + no --value: arg1 = instance ref, arg2 = FQDN
        instance_ref = arg1
        fqdn         = arg2
    elif arg1:                                                                        # One positional: instance ref OR FQDN
        if _looks_like_instance_ref(arg1):
            instance_ref = arg1                                                        # Derive FQDN from stack name later
        else:
            fqdn = arg1                                                                # FQDN; instance comes from --latest
    # else: both arg1 + arg2 absent → use --latest instance, derived name

    if value is None and record_type != Enum__Route53__Record_Type.A:
        typer.echo(f'Auto-resolution from instance only supports A records. Pass --value for {rtype}.', err=True)
        raise typer.Exit(1)

    client = _client()

    # ── Resolve IP from instance when no explicit --value was given ─────────
    if value is None:
        t0     = time.perf_counter()
        linker = Route53__Instance__Linker()
        try:
            inst = linker.resolve_instance(instance_ref) if instance_ref else linker.resolve_latest()
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        try:
            value = linker.get_public_ip(inst)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        if not fqdn:                                                                  # No explicit FQDN — derive from instance Name tag + default zone
            name_tag = linker.get_name_tag(inst)
            default  = client.resolve_default_zone()
            fqdn     = f'{name_tag}.{str(default.name)}'
        instance_resolved = True
        _record('Instance lookup', t0)

    t0      = time.perf_counter()
    zone_id = _resolve_zone_id_for_record(client, zone, fqdn)
    _record('Zone resolution', t0)

    # ── Idempotency / upsert (only for instance-resolved A records) ────────
    if instance_resolved:
        t0       = time.perf_counter()
        existing = client.get_record(zone_id, fqdn, record_type)
        _record('Existing-record check', t0)
    else:
        existing = None
    if existing:
        existing_vals = list(existing.values)
        if value in existing_vals:
            c = Console(highlight=False)
            if not json_output:
                c.print(f'\n  Already correct — {fqdn} already points at {value}.\n')
                c.print(_CERT_WARNING.format(fqdn=fqdn))
                _print_timings(c, timings, time.perf_counter() - overall_t0)
            else:
                typer.echo(json.dumps(dict(change_id='', status='ALREADY_CORRECT',
                                            fqdn=fqdn, value=value, idempotent=True,
                                            timings=_timings_to_dict(timings, time.perf_counter() - overall_t0))))
            raise typer.Exit(0)
        if not force:
            typer.echo(f'Record {fqdn} already exists pointing at {existing_vals}. '
                       f'Use --force to upsert, or `records update` for explicit change.', err=True)
            raise typer.Exit(4)

    if not yes:                                                                       # Always-on confirm (replaces the env gate); --yes skips it
        confirmed = typer.confirm(f'Create {fqdn} {rtype} → {value} (TTL {ttl}s)?', default=False)
        if not confirmed:
            typer.echo('Aborted.')
            raise typer.Exit(0)

    t0 = time.perf_counter()
    try:
        if existing and force:
            result = client.upsert_record(zone_id, fqdn, record_type, [value], ttl=ttl)
        else:
            result = client.create_record(zone_id, fqdn, record_type, [value], ttl=ttl)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        typer.echo('Use `records update` to change an existing record, or pass --force.', err=True)
        raise typer.Exit(1)
    _record('Submit Route 53 change', t0)

    c = Console(highlight=False)
    if not json_output:
        c.print(f'\n  Created {fqdn} {rtype} → {value}  (TTL {ttl}s)')
        c.print(f'  Change: {result.change_id}  Status: {result.status}\n')

    if wait:
        t0    = time.perf_counter()
        final = _wait_for_change(c, client, result.change_id, wait_timeout, quiet=json_output)
        _record('Wait for INSYNC', t0)
        if final.status != 'INSYNC':
            if not json_output:
                c.print(f'  [yellow]✗ Timed out waiting for INSYNC after {wait_timeout}s (last status: {final.status}).[/]\n')
                _print_timings(c, timings, time.perf_counter() - overall_t0)
            if json_output:
                typer.echo(json.dumps(dict(change_id=result.change_id, status=final.status,
                                           submitted_at=result.submitted_at, timed_out=True,
                                           fqdn=fqdn, value=value,
                                           timings=_timings_to_dict(timings, time.perf_counter() - overall_t0))))
            raise typer.Exit(5)
        result = final

    # --wait forces at least an authoritative check even if --no-verify is set.
    run_verify = wait or (not no_verify)
    verify_result = None
    if run_verify:
        t0    = time.perf_counter()
        smart = _make_smart_verify(client)
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision    import Enum__Smart_Verify__Decision
        from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Decision import Schema__Smart_Verify__Decision
        decision = Schema__Smart_Verify__Decision(decision=Enum__Smart_Verify__Decision.NEW_NAME,
                                                  prior_ttl=0, prior_values=[])
        verify_result = smart.verify_after_mutation(decision, zone_id, fqdn, rtype, expected=value)
        _record('Authoritative + public-resolver checks' if (verify_result.public_resolvers and not no_verify) else 'Authoritative check', t0)

    if json_output:
        payload = dict(change_id   =result.change_id  ,
                       status      =result.status     ,
                       submitted_at=result.submitted_at,
                       fqdn        =fqdn               ,
                       value       =value              ,
                       timings     =_timings_to_dict(timings, time.perf_counter() - overall_t0))
        typer.echo(json.dumps(payload))
        return

    if verify_result is not None:
        _print_auth_check(c, verify_result.authoritative)
        if verify_result.public_resolvers and not no_verify:
            c.print(f'  Public resolvers: {verify_result.public_resolvers.agreed_count}/'
                    f'{verify_result.public_resolvers.total_count} agree.')
        if verify_result.skip_message and not no_verify:
            c.print(f'\n  {verify_result.skip_message}\n')

    if instance_resolved:                                                              # Cert hint only when the record points at an EC2 instance
        c.print(_CERT_WARNING.format(fqdn=fqdn))

    _print_timings(c, timings, time.perf_counter() - overall_t0)


# ── records update ────────────────────────────────────────────────────────────

@records_app.command('update')
@spec_cli_errors
def records_update(name       : str  = typer.Argument(...,  help='Record name (FQDN).'),
                   value      : str  = typer.Option(...,   '--value', '-v', help='New record value.'),
                   rtype      : str  = typer.Option('A',   '--type',  '-t', help='Record type.'),
                   ttl        : int  = typer.Option(60,    '--ttl',         help='New TTL in seconds.'),
                   zone       : str  = typer.Option(None,  '--zone',  '-z', help='Zone name or id.'),
                   yes        : bool = typer.Option(False, '--yes',         help='Skip confirmation prompt.'),
                   no_verify  : bool = typer.Option(False, '--no-verify',   help='Skip post-mutation DNS verify.'),
                   json_output: bool = typer.Option(False, '--json',        help='Emit change result as JSON.')):
    """Upsert a DNS record (create or replace). Env var SG_AWS__DNS__ALLOW_MUTATIONS=1 required."""
    _assert_mutations_allowed()
    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)
    client   = _client()
    zone_id  = _resolve_zone_id_for_record(client, zone, name)
    smart    = _make_smart_verify(client)
    decision = smart.decide_before_add(zone_id, name, record_type)
    existing = client.get_record(zone_id, name, record_type)
    if existing:
        old_vals = '  '.join(existing.values) if existing.values else '(none)'
        c = Console(highlight=False)
        c.print(f'\n  old: {old_vals} (TTL {existing.ttl}s) → new: {value} (TTL {ttl}s)\n')
    if not yes:
        confirmed = typer.confirm('Apply this update?', default=False)
        if not confirmed:
            typer.echo('Aborted.')
            raise typer.Exit(0)
    result = client.upsert_record(zone_id, name, record_type, [value], ttl=ttl)
    if json_output:
        typer.echo(json.dumps(dict(change_id   =result.change_id  ,
                                   status      =result.status     ,
                                   submitted_at=result.submitted_at)))
        return
    c = Console(highlight=False)
    c.print(f'\n  Updated {name} {rtype} → {value}  (TTL {ttl}s)')
    c.print(f'  Change: {result.change_id}  Status: {result.status}\n')
    if not no_verify:
        verify_result = smart.verify_after_mutation(decision, zone_id, name, rtype, expected=value)
        _print_auth_check(c, verify_result.authoritative)
        if verify_result.skip_message:
            c.print(f'\n  {verify_result.skip_message}\n')


# ── records delete ────────────────────────────────────────────────────────────

@records_app.command('delete')
@spec_cli_errors
def records_delete(name       : str  = typer.Argument(...,  help='Record name (FQDN).'),
                   rtype      : str  = typer.Option('A',   '--type',  '-t', help='Record type.'),
                   zone       : str  = typer.Option(None,  '--zone',  '-z', help='Zone name or id.'),
                   yes        : bool = typer.Option(False, '--yes',         help='Skip confirmation prompt.'),
                   json_output: bool = typer.Option(False, '--json',        help='Emit change result as JSON.')):
    """Delete a DNS record. Env var SG_AWS__DNS__ALLOW_MUTATIONS=1 required."""
    _assert_mutations_allowed()
    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)
    client  = _client()
    zone_id = _resolve_zone_id_for_record(client, zone, name)
    record  = client.get_record(zone_id, name, record_type)
    if record is None:
        typer.echo(f'No {rtype} record found for {name!r} in zone {zone_id}', err=True)
        raise typer.Exit(1)
    vals_str = '  '.join(record.values) if record.values else '(none)'
    typer.echo(f'\n  Deleting: {name}  {rtype}  TTL={record.ttl}  {vals_str}\n')
    if not yes:
        confirmed = typer.confirm('Delete this record?', default=False)
        if not confirmed:
            typer.echo('Aborted.')
            raise typer.Exit(0)
    from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision    import Enum__Smart_Verify__Decision
    from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Decision import Schema__Smart_Verify__Decision
    prior_decision = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.DELETE,
                                                    prior_ttl   = int(record.ttl)                    ,
                                                    prior_values= list(record.values)                )
    result = client.delete_record(zone_id, name, record_type)
    if json_output:
        typer.echo(json.dumps(dict(change_id   =result.change_id  ,
                                   status      =result.status     ,
                                   submitted_at=result.submitted_at)))
        return
    c = Console(highlight=False)
    c.print(f'\n  Deleted {name} {rtype}')
    c.print(f'  Change: {result.change_id}  Status: {result.status}\n')
    smart         = _make_smart_verify(client)
    verify_result = smart.verify_after_mutation(prior_decision, zone_id, name, rtype)
    if verify_result.skip_message:
        c.print(f'\n  {verify_result.skip_message}\n')


# ── records check ─────────────────────────────────────────────────────────────

@records_app.command('check')
@spec_cli_errors
def records_check(name             : str  = typer.Argument(..., help='Record name (FQDN).'),
                  rtype            : str  = typer.Option('A',   '--type',            '-t', help='Record type.'),
                  zone             : str  = typer.Option(None,  '--zone',            '-z', help='Zone name or id.'),
                  expect           : str  = typer.Option('',    '--expect',                help='Expected value; empty = just check it resolves.'),
                  public_resolvers : bool = typer.Option(False, '--public-resolvers',      help='Also query the 8 public resolvers (CACHE-POLLUTING).'),
                  local            : bool = typer.Option(False, '--local',                 help='Also query the host default resolver (CACHE-POLLUTING).'),
                  all_checks       : bool = typer.Option(False, '--all',                   help='Run authoritative + public-resolvers + local (CACHE-POLLUTING).'),
                  yes              : bool = typer.Option(False, '--yes',                   help='Skip warning prompts on cache-polluting modes.'),
                  min_resolvers    : int  = typer.Option(5,     '--min-resolvers',         help='Quorum threshold for --public-resolvers (default 5/8).'),
                  json_output      : bool = typer.Option(False, '--json',                  help='Emit JSON instead of tables.')):
    """Check DNS record consistency. Authoritative-only by default; opt-in cache-polluting modes via --public-resolvers / --local / --all."""
    # Normalise: --public-resolvers + --local together is equivalent to --all
    if public_resolvers and local and not all_checks:
        all_checks = True
    if all_checks:
        run_public = True
        run_local  = True
        banner     = _WARNING__ALL
    else:
        run_public = public_resolvers
        run_local  = local
        banner     = _WARNING__PUBLIC_RESOLVERS if run_public else _WARNING__LOCAL if run_local else ''

    if banner and not json_output:                                                   # Warn + prompt unless --yes; silent in --json mode (still requires --yes)
        c_warn = Console(highlight=False, stderr=True)
        c_warn.print()
        c_warn.print(banner)
        c_warn.print()
        if not yes:
            typer.confirm('Continue?', abort=True)
    elif banner and json_output and not yes:
        typer.echo('Refusing to run cache-polluting mode in --json without --yes.', err=True)
        raise typer.Exit(1)

    client     = _client()
    zone_id    = _resolve_zone_id_for_record(client, zone, name)
    orch       = _make_orchestrator(client)

    auth_result   = orch.check_authoritative(zone_id, name, rtype, expected=expect)
    public_result = None
    local_result  = None
    if run_public:
        orch.public_resolver_checker.use_full_set(quorum=min_resolvers)              # Switch to the 8-resolver full set with the requested quorum
        public_result = orch.check_public_resolvers(name, rtype, expected=expect)
    if run_local:
        local_result  = orch.check_local(name, rtype, expected=expect)

    # Exit-code priority: auth fail (1) > public fail (2) > local fail (3) > 0
    if not auth_result.passed:
        exit_code = 1
    elif public_result is not None and not public_result.passed:
        exit_code = 2
    elif local_result is not None and not local_result.passed:
        exit_code = 3
    else:
        exit_code = 0

    if json_output:
        payload = dict(authoritative    = _result_to_dict(auth_result)             ,
                       public_resolvers = _result_to_dict(public_result) if public_result else None,
                       local            = _result_to_dict(local_result)  if local_result  else None,
                       exit_code        = exit_code                                )
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(exit_code)

    c = Console(highlight=False)
    _print_auth_check(c, auth_result)
    if public_result is not None:
        _print_public_resolvers_check(c, public_result, min_resolvers)
    if local_result is not None:
        _print_local_check(c, local_result)
    raise typer.Exit(exit_code)


# ── instance create-record ────────────────────────────────────────────────────

@instance_app.command('create-record')
@spec_cli_errors
def instance_create_record(
        instance     : str  = typer.Argument(None,   help='Instance id or Name tag. Omit to use most recent SG-AI instance.'),
        name         : str  = typer.Option(None,  '--name',       help='Explicit FQDN for the record.'),
        zone         : str  = typer.Option(None,  '--zone', '-z', help='Zone name or id.'),
        ttl          : int  = typer.Option(60,    '--ttl',        help='TTL in seconds.'),
        rtype        : str  = typer.Option('A',   '--type', '-t', help='Record type (default A).'),
        yes          : bool = typer.Option(False, '--yes',        help='Skip confirmation prompt.'),
        no_verify    : bool = typer.Option(False, '--no-verify',  help='Skip post-mutation DNS verify.'),
        force        : bool = typer.Option(False, '--force',      help='Upsert even if record points at different IP.'),
        wait         : bool = typer.Option(False, '--wait',       help='Poll Route 53 until INSYNC before exiting (suitable for chaining cert issuance).'),
        wait_timeout : int  = typer.Option(120,   '--wait-timeout',help='Max seconds to wait for INSYNC.'),
        json_output  : bool = typer.Option(False, '--json',       help='Emit change result as JSON.')):
    """Create an A record pointing at an EC2 instance's public IP."""
    _assert_mutations_allowed()
    linker = Route53__Instance__Linker()
    try:
        inst = linker.resolve_instance(instance) if instance else linker.resolve_latest()
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    try:
        public_ip = linker.get_public_ip(inst)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    name_tag = linker.get_name_tag(inst)
    client   = _client()
    if name:
        fqdn    = name
        zone_id = _resolve_zone_id_for_record(client, zone, name)
    else:
        if zone:
            zone_obj = client.get_hosted_zone(zone)
        else:
            zone_obj = client.resolve_default_zone()
        zone_id = str(zone_obj.zone_id)
        fqdn    = f'{name_tag}.{str(zone_obj.name)}'
    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)
    existing = client.get_record(zone_id, fqdn, record_type)
    if existing:
        existing_vals = list(existing.values)
        if public_ip in existing_vals:
            c = Console(highlight=False)
            c.print(f'\n  Already correct — record already points at this instance.\n')
            c.print(_CERT_WARNING.format(fqdn=fqdn))
            raise typer.Exit(0)
        if not force:
            typer.echo(f'Record {fqdn} already exists pointing at {existing_vals}. '
                       f'Use --force to upsert.', err=True)
            raise typer.Exit(4)
    if not yes:
        confirmed = typer.confirm(f'Create {fqdn} → {public_ip} (TTL {ttl}s)?', default=False)
        if not confirmed:
            typer.echo('Aborted.')
            raise typer.Exit(0)
    smart    = _make_smart_verify(client)
    decision = smart.decide_before_add(zone_id, fqdn, record_type)
    if existing and force:
        result = client.upsert_record(zone_id, fqdn, record_type, [public_ip], ttl=ttl)
    else:
        result = client.create_record(zone_id, fqdn, record_type, [public_ip], ttl=ttl)
    c = Console(highlight=False)
    if not json_output:
        c.print(f'\n  Created {fqdn} {rtype} → {public_ip}  (TTL {ttl}s)')
        c.print(f'  Change: {result.change_id}  Status: {result.status}\n')
    if wait:                                                                          # Poll INSYNC before any verify step so smart-verify sees a settled zone
        final = _wait_for_change(c, client, result.change_id, wait_timeout, quiet=json_output)
        if final.status != 'INSYNC':
            if not json_output:
                c.print(f'  [yellow]✗ Timed out waiting for INSYNC after {wait_timeout}s (last status: {final.status}).[/]\n')
            if json_output:
                typer.echo(json.dumps(dict(change_id=result.change_id, status=final.status,
                                           submitted_at=result.submitted_at, fqdn=fqdn,
                                           public_ip=public_ip, timed_out=True)))
            raise typer.Exit(5)
        result = final
    if json_output:
        typer.echo(json.dumps(dict(change_id   =result.change_id  ,
                                   status      =result.status     ,
                                   submitted_at=result.submitted_at,
                                   fqdn        =fqdn               ,
                                   public_ip   =public_ip          )))
        return
    # --wait forces an authoritative check even when --no-verify is set so the user can chain a cert tool with confidence.
    run_verify = wait or (not no_verify)
    if run_verify:
        verify_result = smart.verify_after_mutation(decision, zone_id, fqdn, rtype, expected=public_ip)
        _print_auth_check(c, verify_result.authoritative)
        if verify_result.public_resolvers and not no_verify:
            c.print(f'  Public resolvers: {verify_result.public_resolvers.agreed_count}/'
                    f'{verify_result.public_resolvers.total_count} agree.')
        if verify_result.skip_message and not no_verify:
            c.print(f'\n  {verify_result.skip_message}\n')
    c.print(_CERT_WARNING.format(fqdn=fqdn))
