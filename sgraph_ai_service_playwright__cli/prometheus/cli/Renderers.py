# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus Renderers
# Tier-2A Rich-based renderers for the sp prom typer commands. Pure functions
# — they accept a Type_Safe schema and write to a Console. No service calls,
# no AWS calls. Single responsibility: schema → human-readable Rich output.
# Mirrors the sp os Renderers.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Response import Schema__Prom__Stack__Create__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__List import Schema__Prom__Stack__List


def _state_colour(state: Enum__Prom__Stack__State) -> str:
    return {Enum__Prom__Stack__State.READY      : 'green' ,
            Enum__Prom__Stack__State.RUNNING    : 'green' ,
            Enum__Prom__Stack__State.PENDING    : 'yellow',
            Enum__Prom__Stack__State.TERMINATING: 'red'   ,
            Enum__Prom__Stack__State.TERMINATED : 'red'   ,
            Enum__Prom__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__Prom__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Prometheus stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('public-ip'   , style='green')
    t.add_column('region'      , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                   ,
                  str(info.instance_id)                  ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]',
                  str(info.public_ip) or '—'             ,
                  str(info.region)                       )
    c.print(t)


def render_info(info: Schema__Prom__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   Prometheus stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'       , str(info.region)         or '—')
    t.add_row('ami'          , str(info.ami_id)         or '—')
    t.add_row('public-ip'    , str(info.public_ip)      or '—')
    t.add_row('prometheus'   , str(info.prometheus_url) or '—')
    t.add_row('allowed-ip'   , str(info.allowed_ip)     or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Prom__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp prom stack[/]  ·  {resp.stack_name}', border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id    : [dim]{resp.instance_id}[/]')
    c.print(f'  region         : {resp.region}')
    c.print(f'  ami            : {resp.ami_id}')
    c.print(f'  prometheus-url : {resp.prometheus_url}')
    c.print(f'  targets-baked  : {resp.targets_count}')
    c.print()


def render_health(h: Schema__Prom__Health, c: Console) -> None:
    colour = _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    rows = (('prometheus-ok', 'yes' if h.prometheus_ok else 'no'           ),
            ('targets-total', '—' if h.targets_total < 0 else str(h.targets_total)),
            ('targets-up'   , '—' if h.targets_up    < 0 else str(h.targets_up   )),
            ('error'        , str(h.error) or '—'                          ))
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    for label, value in rows:
        t.add_row(label, value)
    c.print(t)
    c.print()
