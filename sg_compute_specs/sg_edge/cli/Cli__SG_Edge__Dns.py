# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge__Dns
# Typer app for `sg edge dns` — DNS-as-registry diagnostics (all read-only).
#
#   proxies              list proxies.<parent> A values (fleet IPs)
#   state                show _state.<parent> TXT (zero_streak;updated)
#   slugs                list active _sg.<slug>.<parent> routing records
#   routing <slug>       parse and print one _sg.<slug> TXT record
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console

app = typer.Typer(name='dns', help='DNS-as-registry diagnostics (read-only).', no_args_is_help=True)

_dns_factory = None                                                              # tests assign a callable → SG_Edge__DNS__Helper


def _parent_from(parent: str) -> str:
    return parent or os.environ.get('SG_EDGE__PARENT_DOMAIN', os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', ''))


def _dns():
    if _dns_factory is not None:
        return _dns_factory()
    from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
    return SG_Edge__DNS__Helper()


@app.command(name='proxies', help='List proxies.<parent> A values (fleet IPs).')
def proxies(
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    if not par:
        c.print('\n  [red]✗  --parent / $SG_EDGE__PARENT_DOMAIN is required[/]\n')
        raise typer.Exit(1)
    try:
        ips = _dns().list_proxy_ips(par)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        c.print(json.dumps({'parent': par, 'ips': ips}, indent=2))
        return
    c.print()
    c.print(f'  proxies.{par}  ({len(ips)} IP{"s" if len(ips) != 1 else ""})')
    for ip in ips:
        c.print(f'    {ip}')
    if not ips:
        c.print('    (none)')
    c.print()


@app.command(name='state', help='Show _state.<parent> TXT (zero_streak / updated).')
def state(
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    if not par:
        c.print('\n  [red]✗  --parent / $SG_EDGE__PARENT_DOMAIN is required[/]\n')
        raise typer.Exit(1)
    try:
        rec = _dns().read_state(par)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        c.print(json.dumps({'parent': par, 'zero_streak': int(rec.zero_streak), 'updated': int(rec.updated)}, indent=2))
        return
    c.print()
    c.print(f'  _state.{par}')
    c.print(f'    zero_streak : {int(rec.zero_streak)}')
    c.print(f'    updated     : {int(rec.updated)}')
    c.print()


@app.command(name='slugs', help='List active _sg.<slug>.<parent> routing records.')
def slugs(
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    if not par:
        c.print('\n  [red]✗  --parent / $SG_EDGE__PARENT_DOMAIN is required[/]\n')
        raise typer.Exit(1)
    try:
        active = _dns().list_active_slugs(par)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        c.print(json.dumps({'parent': par, 'slugs': active}, indent=2))
        return
    c.print()
    c.print(f'  Active slugs for {par}  ({len(active)})')
    for slug in active:
        c.print(f'    {slug}')
    if not active:
        c.print('    (none)')
    c.print()


@app.command(name='routing', help='Parse and print one _sg.<slug>.<parent> TXT routing record.')
def routing(
    slug       : str  = typer.Argument(..., help='Slug name'),
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    if not par:
        c.print('\n  [red]✗  --parent / $SG_EDGE__PARENT_DOMAIN is required[/]\n')
        raise typer.Exit(1)
    try:
        rec = _dns().read_routing(par, slug)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if rec is None:
        c.print(f'\n  [yellow]⚠[/]  No routing record for slug [bold]{slug}[/] in {par}\n')
        raise typer.Exit(1)
    if output_json:
        c.print(json.dumps(rec.json(), indent=2))
        return
    c.print()
    c.print(f'  _sg.{slug}.{par}')
    c.print(f'    ip       : {rec.ip}')
    c.print(f'    port     : {int(rec.port)}')
    c.print(f'    type     : {rec.type}')
    c.print(f'    launched : {int(rec.launched)}')
    c.print()
