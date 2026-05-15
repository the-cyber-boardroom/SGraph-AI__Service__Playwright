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

import typer
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

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
zones_app    = typer.Typer(name='zones',    help='Hosted zone commands.',    no_args_is_help=True)
records_app  = typer.Typer(name='records',  help='Record set commands.',     no_args_is_help=True)
instance_app = typer.Typer(name='instance', help='EC2-instance DNS helpers.', no_args_is_help=True)

dns_app.add_typer(zones_app,    name='zones'   )
dns_app.add_typer(records_app,  name='records' )
dns_app.add_typer(instance_app, name='instance')


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


# ── zones list ────────────────────────────────────────────────────────────────

@zones_app.command('list')
def zones_list(json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List all hosted zones in the account."""
    client = _client()
    zones  = client.list_hosted_zones()
    if json_output:
        typer.echo(json.dumps([dict(zone_id     = str(z.zone_id)       ,
                                    name        = str(z.name)          ,
                                    private_zone= z.private_zone       ,
                                    record_count= z.record_count       ,
                                    comment     = z.comment            ,
                                    caller_reference = z.caller_reference)
                                for z in zones], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  Hosted zones in account  ·  {len(zones)} zones')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('Zone Id',  style='cyan',    min_width=22, no_wrap=True)
    t.add_column('Name',     style='bold',    min_width=20)
    t.add_column('Type',     style='',        min_width=7)
    t.add_column('Records',  style='',        min_width=7)
    t.add_column('Comment',  style='dim',     min_width=10)
    for z in zones:
        zone_type = 'private' if z.private_zone else 'public'
        t.add_row(str(z.zone_id), str(z.name) + '.', zone_type,
                  str(z.record_count), str(z.comment))
    c.print(t)
    c.print()


# ── zones show ────────────────────────────────────────────────────────────────

@zones_app.command('show')
def zones_show(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sgraph.ai.'),
               json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """Show details of one hosted zone."""
    client    = _client()
    zone_obj  = client.get_hosted_zone(zone) if zone else client.resolve_default_zone()
    if json_output:
        typer.echo(json.dumps(dict(zone_id     = str(zone_obj.zone_id)        ,
                                   name        = str(zone_obj.name)           ,
                                   private_zone= zone_obj.private_zone        ,
                                   record_count= zone_obj.record_count        ,
                                   comment     = zone_obj.comment             ,
                                   caller_reference = zone_obj.caller_reference), indent=2))
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


# ── records list ──────────────────────────────────────────────────────────────

@records_app.command('list')
def records_list(zone       : str  = typer.Argument(None, help='Zone name or id. Defaults to sgraph.ai.'),
                 json_output: bool = typer.Option(False, '--json', help='Output JSON instead of a table.')):
    """List all records in a hosted zone."""
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


# ── records get ───────────────────────────────────────────────────────────────

@records_app.command('get')
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

@records_app.command('add')
def records_add(name       : str  = typer.Argument(...,  help='Record name (FQDN).'),
                value      : str  = typer.Option(...,   '--value', '-v', help='Record value (e.g. IP address).'),
                rtype      : str  = typer.Option('A',   '--type',  '-t', help='Record type.'),
                ttl        : int  = typer.Option(60,    '--ttl',         help='TTL in seconds.'),
                zone       : str  = typer.Option(None,  '--zone',  '-z', help='Zone name or id.'),
                yes        : bool = typer.Option(False, '--yes',         help='Skip confirmation prompt.'),
                no_verify  : bool = typer.Option(False, '--no-verify',   help='Skip post-mutation DNS verify.'),
                json_output: bool = typer.Option(False, '--json',        help='Emit change result as JSON.')):
    """Create a new DNS record. Env var SG_AWS__DNS__ALLOW_MUTATIONS=1 required."""
    _assert_mutations_allowed()
    try:
        record_type = Enum__Route53__Record_Type(rtype.upper())
    except ValueError:
        typer.echo(f'Unknown record type: {rtype}', err=True)
        raise typer.Exit(1)
    client  = _client()
    zone_id = _resolve_zone_id_for_record(client, zone, name)
    try:
        result = client.create_record(zone_id, name, record_type, [value], ttl=ttl)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        typer.echo("Use `records update` to change an existing record.", err=True)
        raise typer.Exit(1)
    if json_output:
        typer.echo(json.dumps(dict(change_id   =result.change_id  ,
                                   status      =result.status     ,
                                   submitted_at=result.submitted_at)))
        return
    c = Console(highlight=False)
    c.print(f'\n  Created {name} {rtype} → {value}  (TTL {ttl}s)')
    c.print(f'  Change: {result.change_id}  Status: {result.status}\n')
    if not no_verify:
        smart = _make_smart_verify(client)
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision    import Enum__Smart_Verify__Decision
        from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Decision import Schema__Smart_Verify__Decision
        decision = Schema__Smart_Verify__Decision(decision=Enum__Smart_Verify__Decision.NEW_NAME,
                                                  prior_ttl=0, prior_values=[])
        verify_result = smart.verify_after_mutation(decision, zone_id, name, rtype, expected=value)
        _print_auth_check(c, verify_result.authoritative)
        if verify_result.public_resolvers:
            c.print(f'  Public resolvers: {verify_result.public_resolvers.agreed_count}/'
                    f'{verify_result.public_resolvers.total_count} agree.')
        if verify_result.skip_message:
            c.print(f'\n  {verify_result.skip_message}\n')


# ── records update ────────────────────────────────────────────────────────────

@records_app.command('update')
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
def instance_create_record(
        instance   : str  = typer.Argument(None,   help='Instance id or Name tag. Omit to use most recent SG-AI instance.'),
        name       : str  = typer.Option(None,  '--name',       help='Explicit FQDN for the record.'),
        zone       : str  = typer.Option(None,  '--zone', '-z', help='Zone name or id.'),
        ttl        : int  = typer.Option(60,    '--ttl',        help='TTL in seconds.'),
        rtype      : str  = typer.Option('A',   '--type', '-t', help='Record type (default A).'),
        yes        : bool = typer.Option(False, '--yes',        help='Skip confirmation prompt.'),
        no_verify  : bool = typer.Option(False, '--no-verify',  help='Skip post-mutation DNS verify.'),
        force      : bool = typer.Option(False, '--force',      help='Upsert even if record points at different IP.'),
        json_output: bool = typer.Option(False, '--json',       help='Emit change result as JSON.')):
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
    if json_output:
        typer.echo(json.dumps(dict(change_id   =result.change_id  ,
                                   status      =result.status     ,
                                   submitted_at=result.submitted_at)))
        return
    c = Console(highlight=False)
    c.print(f'\n  Created {fqdn} {rtype} → {public_ip}  (TTL {ttl}s)')
    c.print(f'  Change: {result.change_id}  Status: {result.status}\n')
    if not no_verify:
        verify_result = smart.verify_after_mutation(decision, zone_id, fqdn, rtype, expected=public_ip)
        _print_auth_check(c, verify_result.authoritative)
        if verify_result.public_resolvers:
            c.print(f'  Public resolvers: {verify_result.public_resolvers.agreed_count}/'
                    f'{verify_result.public_resolvers.total_count} agree.')
        if verify_result.skip_message:
            c.print(f'\n  {verify_result.skip_message}\n')
    c.print(_CERT_WARNING.format(fqdn=fqdn))
