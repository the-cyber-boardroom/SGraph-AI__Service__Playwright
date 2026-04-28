# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux Renderers
# Tier-2A Rich-based renderers for the sp linux typer commands. Pure functions
# — accept a Type_Safe schema and write to a Console. No service calls, no AWS
# calls. Single responsibility: schema → human-readable Rich output.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Response import Schema__Linux__Create__Response
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Health__Response import Schema__Linux__Health__Response
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info            import Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__List            import Schema__Linux__List


def _state_colour(state: Enum__Linux__Stack__State) -> str:
    return {Enum__Linux__Stack__State.RUNNING    : 'green' ,
            Enum__Linux__Stack__State.PENDING    : 'yellow',
            Enum__Linux__Stack__State.STOPPING   : 'yellow',
            Enum__Linux__Stack__State.STOPPED    : 'red'   ,
            Enum__Linux__Stack__State.TERMINATING: 'red'   ,
            Enum__Linux__Stack__State.TERMINATED : 'red'   ,
            Enum__Linux__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def _secs(ms: int) -> str:                                                          # 2598ms → "2.6s", 300ms → "0.3s"
    return f'{ms / 1000:.1f}s'


def render_list(listing: Schema__Linux__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Linux stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('public-ip'   , style='green')
    t.add_column('region'      , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                          ,
                  str(info.instance_id)                                         ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]'        ,
                  str(info.public_ip) or '—'                                    ,
                  str(info.region)                                               )
    c.print(t)


def render_info(info: Schema__Linux__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   Linux stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'      , str(info.region)            or '—')
    t.add_row('ami'         , str(info.ami_id)            or '—')
    t.add_row('instance'    , str(info.instance_type)     or '—')
    t.add_row('public-ip'   , str(info.public_ip)         or '—')
    t.add_row('allowed-ip'  , str(info.allowed_ip)        or '—')
    t.add_row('sg-id'       , str(info.security_group_id) or '—')
    t.add_row('uptime'      , f'{info.uptime_seconds}s'   if info.uptime_seconds else '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Linux__Create__Response, c: Console) -> None:
    info = resp.stack_info
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp linux stack[/]  ·  {info.stack_name}', border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id  : [dim]{info.instance_id}[/]')
    c.print(f'  region       : {info.region}')
    c.print(f'  ami          : {info.ami_id}')
    c.print(f'  instance     : {info.instance_type}')
    c.print(f'  allowed-ip   : {info.allowed_ip}')
    c.print(f'  submitted in : {_secs(resp.elapsed_ms)}')                           # Time for EC2 API call to accept the launch request
    c.print()
    c.print(f'  [dim]Connect:    sp linux connect {info.stack_name} --region {info.region}[/]')
    c.print(f'  [dim]Wait ready: sp linux wait {info.stack_name} --region {info.region}[/]')
    c.print()


def render_health(h: Schema__Linux__Health__Response, c: Console) -> None:
    colour = 'green' if h.healthy else _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{"healthy" if h.healthy else h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('state'        , h.state.value)
    t.add_row('ssm-reachable', 'yes' if h.ssm_reachable else 'no')
    t.add_row('waited'       , _secs(h.elapsed_ms))
    t.add_row('message'      , str(h.message) or '—')
    c.print(t)
    c.print()
