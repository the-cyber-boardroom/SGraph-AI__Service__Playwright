# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko Renderers
# Tier-2A Rich renderers for sp neko typer commands. Pure functions — accept a
# Type_Safe schema, write to a Console. No service / AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.neko.enums.Enum__Neko__Stack__State               import Enum__Neko__Stack__State
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Health__Response        import Schema__Neko__Health__Response
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Create__Response import Schema__Neko__Stack__Create__Response
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Info             import Schema__Neko__Stack__Info
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__List             import Schema__Neko__Stack__List


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def _state_colour(state: Enum__Neko__Stack__State) -> str:
    return {Enum__Neko__Stack__State.READY      : 'green' ,
            Enum__Neko__Stack__State.RUNNING    : 'green' ,
            Enum__Neko__Stack__State.PENDING    : 'yellow',
            Enum__Neko__Stack__State.TERMINATING: 'red'   ,
            Enum__Neko__Stack__State.TERMINATED : 'red'   ,
            Enum__Neko__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__Neko__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Neko stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name' , style='bold')
    t.add_column('instance-id', style='dim')
    t.add_column('state')
    t.add_column('public-ip'  , style='green')
    t.add_column('region'     , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                            ,
                  str(info.instance_id)                                           ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]'           ,
                  str(info.public_ip) or '—'                                      ,
                  str(info.region)                                                )
    c.print(t)


def render_info(info: Schema__Neko__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   Neko stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'    , str(info.region)      or '—')
    t.add_row('ami'       , str(info.ami_id)      or '—')
    t.add_row('public-ip' , str(info.public_ip)   or '—')
    t.add_row('viewer'    , str(info.viewer_url)  or '—')
    t.add_row('allowed-ip', str(info.allowed_ip)  or '—')
    t.add_row('launched'  , str(info.launch_time) or '—')
    c.print(t)
    c.print()


def render_health(h: Schema__Neko__Health__Response, c: Console) -> None:
    colour = 'green' if h.healthy else _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{"healthy" if h.healthy else h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('state'  , h.state.value)
    t.add_row('waited' , _secs(h.elapsed_ms))
    t.add_row('message', str(h.message) or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Neko__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp neko stack[/]  ·  {resp.stack_name}', border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id    : [dim]{resp.instance_id}[/]')
    c.print(f'  region         : {resp.region}')
    c.print(f'  ami            : {resp.ami_id}')
    c.print(f'  viewer-url     : https://<public-ip>/  [dim](available once booted; accept self-signed TLS warning)[/]')
    c.print(f'  admin-password : [bold green]{resp.admin_password}[/]   [yellow](returned once — stash it now)[/]')
    c.print(f'  member-password: [bold]{resp.member_password}[/]')
    c.print()
    c.print('  [dim]Tip: run [bold]sp neko info {resp.stack_name}[/] to get the public IP once the instance is running.[/]')
    c.print()
