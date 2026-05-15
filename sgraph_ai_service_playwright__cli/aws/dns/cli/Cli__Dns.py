# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Dns
# Typer CLI surface for Route 53 DNS management. Two sub-groups: zones and
# records. All commands delegate to Route53__AWS__Client — no boto3 here.
#
# Command tree:
#   sg aws dns zones list             — list all hosted zones in the account
#   sg aws dns zones show [<zone>]    — details of one zone (defaults to sgraph.ai)
#   sg aws dns records list [<zone>]  — list records in a zone (defaults to sgraph.ai)
#   sg aws dns records get <name>     — show one record (default type A)
#
# Flags: --json on every command; --zone / --type on records commands.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type  import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client      import Route53__AWS__Client

# ── Typer sub-apps ────────────────────────────────────────────────────────────

dns_app     = typer.Typer(name='dns',     help='Route 53 DNS management.', no_args_is_help=True)
zones_app   = typer.Typer(name='zones',   help='Hosted zone commands.',    no_args_is_help=True)
records_app = typer.Typer(name='records', help='Record set commands.',     no_args_is_help=True)

dns_app.add_typer(zones_app,   name='zones'  )
dns_app.add_typer(records_app, name='records')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client() -> Route53__AWS__Client:
    return Route53__AWS__Client()


def _resolve_zone_id(client: Route53__AWS__Client, zone: str) -> str:               # Resolve an explicit zone arg or fall back to sgraph.ai
    if zone:
        return client.resolve_zone_id(zone)
    return str(client.resolve_default_zone().zone_id)


def _zone_label(zone_schema) -> str:                                                 # Human-readable label for a zone in table headers
    return f'{zone_schema.name}.  ·  {zone_schema.zone_id}'


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
    zone_id = _resolve_zone_id(client, zone)
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
