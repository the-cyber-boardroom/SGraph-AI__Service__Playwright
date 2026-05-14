# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright Renderers
# Tier-2A Rich-based renderers for the sp playwright typer commands. Pure
# functions — they accept a Type_Safe schema and write to a Console. No
# service calls, no AWS calls. Mirrors the sp prom / sp vnc Renderers.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Health      import Schema__Playwright__Health
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Response import Schema__Playwright__Stack__Create__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__List import Schema__Playwright__Stack__List


def _state_colour(state: Enum__Playwright__Stack__State) -> str:
    return {Enum__Playwright__Stack__State.RUNNING : 'green' ,
            Enum__Playwright__Stack__State.PENDING : 'yellow',
            Enum__Playwright__Stack__State.EXITED  : 'red'   ,
            Enum__Playwright__Stack__State.REMOVED : 'red'   ,
            Enum__Playwright__Stack__State.UNKNOWN : 'white' }.get(state, 'white')


def render_list(listing: Schema__Playwright__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Playwright stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name', style='bold')
    t.add_column('state')
    t.add_column('host-port', style='green')
    t.add_column('image'    , style='dim')
    t.add_column('status'   , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                  ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]' ,
                  str(info.host_port) or '—'                            ,
                  str(info.image)     or '—'                            ,
                  str(info.status)    or '—'                            )
    c.print(t)


def render_info(info: Schema__Playwright__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]🎭  Playwright stack[/]  ·  {info.stack_name}  '
                  f'[{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=12, no_wrap=True)
    t.add_column(style='default')
    t.add_row('pod-name'  , str(info.pod_name)   or '—')
    t.add_row('image'     , str(info.image)      or '—')
    t.add_row('host-port' , str(info.host_port)  or '—')
    t.add_row('status'    , str(info.status)     or '—')
    t.add_row('created-at', str(info.created_at) or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Playwright__Stack__Create__Response, c: Console) -> None:
    c.print()
    if resp.started:
        c.print(Panel(f'[bold green]🚀  Created sp playwright stack[/]  ·  {resp.stack_name}',
                      border_style='green', expand=False))
    else:
        c.print(Panel(f'[bold red]⚠️   sp playwright stack did not start[/]  ·  {resp.stack_name}',
                      border_style='red', expand=False))
    c.print()
    c.print(f'  pod-name     : {resp.pod_name}')
    c.print(f'  container-id : [dim]{resp.container_id}[/]')
    c.print(f'  image        : {resp.image}')
    c.print(f'  host-port    : {resp.host_port}')
    if str(resp.error):
        c.print(f'  error        : [red]{resp.error}[/]')
    c.print()


def render_health(h: Schema__Playwright__Health, c: Console) -> None:
    colour = _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    rows = (('running', 'yes' if h.running else 'no'),
            ('error'  , str(h.error) or '—'         ))
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=12, no_wrap=True)
    t.add_column(style='default')
    for label, value in rows:
        t.add_row(label, value)
    c.print(t)
    c.print()
