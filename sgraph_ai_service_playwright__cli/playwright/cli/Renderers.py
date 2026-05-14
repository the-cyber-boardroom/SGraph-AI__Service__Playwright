# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright Renderers
# Tier-2A Rich-based renderers for the sp playwright typer commands. Pure
# functions — they accept a Type_Safe schema and write to a Console. No
# service calls, no AWS calls. Mirrors the sp prom / sp vnc Renderers.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                import Console
from rich.panel                                                                  import Panel
from rich.table                                                                  import Table

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Health import Schema__Playwright__Health
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Response import Schema__Playwright__Stack__Create__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__List import Schema__Playwright__Stack__List


def _state_colour(state: Enum__Playwright__Stack__State) -> str:
    return {Enum__Playwright__Stack__State.RUNNING    : 'green' ,
            Enum__Playwright__Stack__State.READY      : 'green' ,
            Enum__Playwright__Stack__State.PENDING    : 'yellow',
            Enum__Playwright__Stack__State.TERMINATING: 'red'   ,
            Enum__Playwright__Stack__State.TERMINATED : 'red'   ,
            Enum__Playwright__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__Playwright__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Playwright stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'   , style='bold')
    t.add_column('state'        )
    t.add_column('instance-id'  , style='dim')
    t.add_column('public-ip'    , style='green')
    t.add_column('mitmproxy'    , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                   ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]'  ,
                  str(info.instance_id) or '—'                           ,
                  str(info.public_ip)   or '—'                           ,
                  'yes' if info.with_mitmproxy else 'no'                 )
    c.print(t)


def render_info(info: Schema__Playwright__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]🎭  Playwright stack[/]  ·  {info.stack_name}  '
                  f'[{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('instance-id'   , str(info.instance_id)    or '—')
    t.add_row('region'        , str(info.region)         or '—')
    t.add_row('instance-type' , str(info.instance_type)  or '—')
    t.add_row('public-ip'     , str(info.public_ip)      or '—')
    t.add_row('playwright-url', str(info.playwright_url) or '—')
    t.add_row('mitmproxy'     , 'yes' if info.with_mitmproxy else 'no')
    t.add_row('allowed-ip'    , str(info.allowed_ip)     or '—')
    t.add_row('launch-time'   , str(info.launch_time)    or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Playwright__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp playwright stack[/]  ·  {resp.stack_name}',
                  border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id    : [dim]{resp.instance_id}[/]')
    c.print(f'  region         : {resp.region}')
    c.print(f'  instance-type  : {resp.instance_type}')
    c.print(f'  ami-id         : [dim]{resp.ami_id}[/]')
    c.print(f'  security-group : [dim]{resp.security_group_id}[/]')
    c.print(f'  mitmproxy      : {"yes" if resp.with_mitmproxy else "no"}')
    c.print()
    c.print(f'  [bold yellow]api-key (save this — not stored)[/]  : {resp.api_key}')
    c.print()
    c.print('  [dim]Instance is starting. Allow ~2-3 minutes for Docker and compose to initialise.[/]')
    c.print()


def render_health(h: Schema__Playwright__Health, c: Console) -> None:
    colour = _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    rows = (('playwright-ok', 'yes' if h.playwright_ok else 'no'),
            ('error'        , str(h.error) or '—'               ))
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    for label, value in rows:
        t.add_row(label, value)
    c.print(t)
    c.print()
