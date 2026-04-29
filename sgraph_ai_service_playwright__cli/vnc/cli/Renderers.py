# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — VNC Renderers
# Tier-2A Rich renderers for the sp vnc typer commands. Pure functions —
# accept a Type_Safe schema and write to a Console. No service / AWS / HTTP
# calls. Mirrors the OS / Prom Renderers shape.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary import List__Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Response import Schema__Vnc__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List         import Schema__Vnc__Stack__List


def _state_colour(state: Enum__Vnc__Stack__State) -> str:
    return {Enum__Vnc__Stack__State.READY      : 'green' ,
            Enum__Vnc__Stack__State.RUNNING    : 'green' ,
            Enum__Vnc__Stack__State.PENDING    : 'yellow',
            Enum__Vnc__Stack__State.TERMINATING: 'red'   ,
            Enum__Vnc__Stack__State.TERMINATED : 'red'   ,
            Enum__Vnc__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__Vnc__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No VNC stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('public-ip'   , style='green')
    t.add_column('region'      , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                            ,
                  str(info.instance_id)                                           ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]'           ,
                  str(info.public_ip) or '—'                                      ,
                  str(info.region)                                                )
    c.print(t)


def render_info(info: Schema__Vnc__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   VNC stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    interceptor = (str(info.interceptor_name) or info.interceptor_kind.value)
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'       , str(info.region)         or '—')
    t.add_row('ami'          , str(info.ami_id)         or '—')
    t.add_row('public-ip'    , str(info.public_ip)      or '—')
    t.add_row('viewer'       , str(info.viewer_url)     or '—')
    t.add_row('mitmweb'      , str(info.mitmweb_url)    or '—')
    t.add_row('allowed-ip'   , str(info.allowed_ip)     or '—')
    t.add_row('interceptor'  , interceptor              or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Vnc__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp vnc stack[/]  ·  {resp.stack_name}', border_style='green', expand=False))
    c.print()
    interceptor = (str(resp.interceptor_name) or resp.interceptor_kind.value)
    c.print(f'  instance-id    : [dim]{resp.instance_id}[/]')
    c.print(f'  region         : {resp.region}')
    c.print(f'  ami            : {resp.ami_id}')
    c.print(f'  viewer-url     : {resp.viewer_url}  [dim](self-signed TLS — accept the warning)[/]')
    c.print(f'  mitmweb-url    : {resp.mitmweb_url}')
    c.print(f'  operator-user  : {resp.operator_username}')
    c.print(f'  operator-pwd   : [bold green]{resp.operator_password}[/]   [yellow](returned once — stash it now)[/]')
    c.print(f'  interceptor    : {interceptor}')
    c.print()


def render_health(h: Schema__Vnc__Health, c: Console) -> None:
    colour = _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    rows = (('nginx-ok'    , 'yes' if h.nginx_ok   else 'no'  ),
            ('mitmweb-ok'  , 'yes' if h.mitmweb_ok else 'no'  ),
            ('flow-count'  , '—' if h.flow_count < 0 else str(h.flow_count)),
            ('error'       , str(h.error) or '—'              ))
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    for label, value in rows:
        t.add_row(label, value)
    c.print(t)
    c.print()


def render_flows(flows: List__Schema__Vnc__Mitm__Flow__Summary, c: Console) -> None:
    if not flows:
        c.print('  [dim]No mitmweb flows yet.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('method' , style='bold')
    t.add_column('status' )
    t.add_column('url'    , style='cyan')
    t.add_column('flow-id', style='dim')
    for f in flows:
        status = '—' if f.status_code == 0 else str(f.status_code)
        t.add_row(str(f.method), status, str(f.url), str(f.flow_id))
    c.print(t)


def render_interceptors(names: list, c: Console) -> None:
    if not names:
        c.print('  [dim]No baked example interceptors.[/]')
        return
    c.print('  Baked example interceptors:')
    for name in names:
        c.print(f'    · {name}')
